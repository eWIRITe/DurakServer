import threading
import datetime
import os
import io

import sqlite3
import secrets
import hashlib
import base64
import random

from PIL import Image

from Room import Room
from Card import Card

#                                                               for request.form
from flask import Flask, url_for, redirect, g, request, Response, render_template, send_from_directory
from flask import send_file
from flask_socketio import SocketIO, join_room, leave_room, send, emit, rooms
from flask import jsonify
import json
from flask_cors import CORS


# Can we create a thread that will clean up expired tokens every 6 hours. Every api call will refresh time of token?
class AuthServer:
    def __init__(self):
        self.sessions = {}

    def new_token(self, uid):
        token = secrets.token_hex()
        self.sessions[token] = {"uid":uid}
        self.extend_token(token)
        return token


    def extend_token(self, token):
        if self.sessions.get(token):
            self.sessions.get(token)["dtlife"] = datetime.datetime.now() + datetime.timedelta(hours=6)


    def is_token_expired(self, token):
        dtnow = datetime.datetime.now()
        isExpired = not (self.sessions.get(token) and dtnow < self.sessions.get(token)["dtlife"])
    
        if not isExpired:
            self.extend_token(token)

        return isExpired


    def del_token(self, token):
        if self.sessions.get(token):
            del self.sessions[token]


    def get_uid(self, token):
        if not auth.is_token_expired(token):
            return str(self.sessions.get(token)["uid"])
        else:
            print("incorrect token")

auth = AuthServer()


SECRET_KEY = "2738b417b94cce4f7f70953a41f277a3840219d61e32cfc45246949c9dd2c373"
ALLOWED_AVATAR_EXTENSIONS = { "png" }
UPLOAD_AVATAR_FOLDER = "C:/DurakServer/avatars/"
DATABASE = "C:/DurakServer/durak.db"
COMISSION = 0.1
DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["UPLOAD_FOLDER"] = UPLOAD_AVATAR_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 3 * 2**20 # 3Mb
CORS(app)

socketio = SocketIO(app, logger=DEBUG, engineio_logger=DEBUG)

g_durak_rooms = {}


"""

    DateBase help functions

"""

def get_db():
    # if we are still not db connected
    if not hasattr(g, "link_db"):
        g.link_db = sqlite3.connect(app.config["DATABASE"])

    return g.link_db

@app.teardown_appcontext
def close_db(error):
    # close db connection if it does connected
    if hasattr(g, "link_db"):
        g.link_db.close()

def execSQL(sql, args):
    db = get_db()
    result = None

    try:
        cursor = db.cursor()
        cursor.execute(sql, args)
        result = cursor.fetchall()
        db.commit()

    except Exception as e:
        print("Error db: {0}".format(str(e)))

    if result:
        result = result[0] if len(result) == 1 else result
        result = result[0] if len(result) == 1 else result
    return result


"""

    WS

"""

def cl_distribution(cards, sid):
    emit("cl_distribution", {cards}, to=sid, broadcast=False)

def cl_turn(rid, uid):
    emit("cl_turn", {"uid":uid}, to=rid, broadcast=True)

def cl_grab(rid, uid):
    emit("cl_grab", {"uid":uid}, to=rid, broadcast=True)

def cl_fold(rid, uid):
    emit("cl_fold", {"uid":uid}, to=rid, broadcast=True)

def cl_pass(rid, uid):
    emit("cl_pass", {"uid":uid}, to=rid, broadcast=True)

def cl_start(rid, first, trump, players, bet):
    execSQL('UPDATE Users SET Chips = Chips - ? WHERE ID IN ?;', bet, str(tuple(players)))
    emit("cl_start", {"first":first, "trump":trump}, to=rid, broadcast=True)

def cl_finish(rid, winners):
    for uid in winners.keys():
        execSQL('UPDATE Users SET Chips = Chips + ? WHERE ID == ?;', winners[uid], uid)

    emit("cl_finish", winners, to=rid, broadcast=True)


###Game functions###
####################
@socketio.on("srv_whatsup")
def on_srv_whatsup(json):
    uid = auth.get_uid(json["token"])

    if not uid:
        return

    # if user not entered to any room
    if len(rooms()) == 1:
        return

    rid = rooms()[1]
    room = g_durak_rooms[rid]
    
    if not room:
        return

    room.whatsup()

@socketio.on("srv_battle")
def on_srv_battle(json):
    uid = auth.get_uid(json["token"])

    if not uid:
        return

    # if user not entered to any room
    if len(rooms()) == 1:
        return

    rid = rooms()[1]
    room = g_durak_rooms[rid]
    
    if not room:
        return

    attacked = [Card.from_byte(json["attacked"][i]) for i in json["attacked"]]
    attacking = [Card.from_byte(json["attacking"][i]) for i in json["attacking"]]

    if room.battle(uid, attacked, attacking):
        emit("cl_battle", {"uid":uid, "attacked":json["attacked"], "attacking":json["attacking"]}, to=room.get_rid(), broadcast=True)

@socketio.on("srv_transfer")
def on_srv_transfer(json):
    uid = auth.get_uid(json["token"])

    if not uid:
        return

    # if user not entered to any room
    if len(rooms()) == 1:
        return

    rid = rooms()[1]
    room = g_durak_rooms[rid]

    if not room:
        return

    if room.transfer(uid, Card.from_byte(json["card"])):
        emit("cl_transfer", {"uid":uid, "card":json["card"]}, to=room.get_rid(), broadcast=True)
    
@socketio.on("srv_grab")
def on_srv_grab(json):
    uid = auth.get_uid(json["token"])

    if not uid:
        return
    
    # if user not entered to any room
    if len(rooms()) == 1:
        return

    rid = rooms()[1]
    room = g_durak_rooms[rid]

    if room.grab(uid):
        emit("cl_grab", {"uid":uid}, to=room.get_rid(), broadcast=True)

@socketio.on("srv_pass")
def on_srv_pass(json):
    uid = auth.get_uid(json["token"])

    if not uid:
        return

    # if user not entered to any room
    if len(rooms()) == 1:
        return

    rid = rooms()[1]
    room = g_durak_rooms[rid]

    if not room:
        return

    if room.pass_(uid):
        emit("cl_pass", {"uid":uid}, to=room.get_rid(), broadcast=True)

@socketio.on("srv_fold")
def on_srv_fold(json):
    uid = auth.get_uid(json["token"])

    if not uid:
        return

    # if user not entered to any room
    if len(rooms()) == 1:
        return

    rid = rooms()[1]
    room = g_durak_rooms[rid]

    if not room:
        return

    if room.fold(uid):
        emit("cl_fold", {"uid":uid}, to=room.get_rid(), broadcast=True)

@socketio.on("srv_ready")
def on_srv_ready(json):
    uid = auth.get_uid(json["token"])

    if not uid:
        return

    room = g_durak_rooms.get(str(json["RoomID"]))

    if room and int(uid) == int(room.get_roomOwner()):
        room.set_ready()
        emit("cl_ready", room=str(json["RoomID"]), broadcast=True)


####################################
###Room (enters//exits) functions###
####################################

@socketio.on("srv_createRoom")
def on_srv_createRoom(json):

    def validRoomJSON(json):
        def validMaxPlayers(mxplayers):
            return 2 <= mxplayers <= 6

        def validGameType(gtype):
            return 0 <= gtype <= 2

        def validNumCards(ncards):
            return ncards == 24 or ncards == 36 or ncards == 52

        def validBet(bet):
            return bet == 100 or bet == 500 or \
                bet == 1000 or bet == 5000 or \
                bet == 10000 or bet == 50000 or \
                bet == 100000 or bet == 200000

        return validMaxPlayers(json["maxPlayers"]) and \
            validGameType(json["type"]) and \
            validNumCards(json["cards"]) and \
            validBet(json["bet"]) and \
            json["maxPlayers"] * 6 <= json["cards"]

    uid = auth.get_uid(json["token"])

    ##Check UId
    if not uid:
        http_response = '{"error":"Token not founded"}'
        return Response(response=http_response, mimetype="application/json")
    ##Check User chips 
    if float(execSQL("SELECT Chips FROM Users WHERE ID = ?;", (uid,))) < json["bet"]:
        http_response = '{"error":"Not enouth chips"}'
        return Response(response=http_response, mimetype="application/json")

    # get sid
    sid = request.sid

    ##Get comission
    comission = float(execSQL('SELECT Comission FROM Config;', ""))

    if not validRoomJSON(json):
        http_response = '{"error":"incorrect JSON"}'
        return Response(response=http_response, mimetype="application/json")

    # gen rid
    rid = str(10000 + secrets.randbelow(100000 - 10000))

    # create room
    room = Room(rid, json, comission)

    room.set_distribution_callback(cl_distribution)
    room.set_grab_callback(cl_grab)
    room.set_turn_callback(cl_turn)
    room.set_fold_callback(cl_fold)
    room.set_pass_callback(cl_pass)
    room.set_start_callback(cl_start)
    room.set_finish_callback(cl_finish)
    
    g_durak_rooms[rid] = room

    if not room.join(uid, sid):
        http_response = '{"error":"Room is not free"}'
        return Response(response=http_response, mimetype="application/json")

    join_room(rid)

    json["RoomID"] = rid

    emit("cl_RoomWasCreated", json, broadcast=True)
    emit("cl_enterInTheRoomAsOwner", json, to=rid, broadcast=True)


@socketio.on("srv_joinRoom")
def on_srv_joinRoom(data):
    uid = auth.get_uid(data["Token"])

    ##Check UId
    if not uid:
        print("incorrect token")
        http_response = '{"error":"incorrect token"}'
        return Response(response=http_response, mimetype="application/json")

    # get room
    room = g_durak_rooms[str(data["RoomID"])]
    # if there is no room by rid
    if not room:
        print("incorrect room")
        http_response = '{"error":"incorrect room"}'
        return Response(response=http_response, mimetype="application/json")

    if float(execSQL("SELECT Chips FROM Users WHERE ID = ?;", (uid,))) < room.get_bet():
        print("Not enough chips")
        http_response = '{"error":"Not enough chips"}'
        return Response(response=http_response, mimetype="application/json")

    # if room is private and keys is not eq
    if room.is_private() and room.get_key() != data["key"]:
        print("Room is private")
        http_response = '{"error":"Room is private"}'
        return Response(response=http_response, mimetype="application/json")

    # get sid
    sid = request.sid

    # add player in room
    # if there is no free place or player is already in room
    if not room.join(uid, sid):
        print("Room is not free")
        http_response = '{"error":"Room is not free"}'
        return Response(response=http_response, mimetype="application/json")

    rid = room.get_rid()

    join_room(rid)

    # remove token
    del data["Token"]

    # remove key
    del data["key"]

    data["roomOwner"] = room.get_roomOwner()

    # add uid
    data["uid"] = uid

    # emit event
    emit("cl_joinRoom", data, to=rid, skip_sid=sid)
    emit("cl_enterInTheRoom", data, to=sid)


@socketio.on("srv_exitRoom")
def on_srv_exitRoom(json):
    uid = auth.get_uid(json["token"])

    if not uid:
        return

    # get room
    room = g_durak_rooms.get(str(json["rid"]))
        
    # if there is no room by rid
    if not room:
        print("no room")
        return

    # remove player from room
    # if player is not in the room
    if not room.leave(uid):
        print("player not in this room")
        return

    rid = room.get_rid()

    leave_room(rid)

    # if room is empty
    if room.is_empty():
        emit("cl_RoomWasCreated", json, broadcast=True)
        del g_durak_rooms[rid]
        return

    # remove token
    del json["token"]

    # add uid
    json["uid"] = uid

    emit("cl_exitRoom", json, to=rid, broadcast=True)


###Get all room players###
###Call on enter in room to get all users in room
#################################################
@app.route('/api/get_RoomPlayers', methods=['GET'])
def get_room_players():

    RoomID = request.args.get('RoomID')
    
    if RoomID in g_durak_rooms:
        room = g_durak_rooms[str(RoomID)]
        return room.get_players()

    else:
        # Если комната не найдена, возвращаем ошибку
        response = {'error': 'Room not found'}
        return jsonify(response), 404

@app.route("/api/get_freeRooms", methods = ["GET"])
def get_free_rooms( ):
    free_rooms = []
    for room_id, room in g_durak_rooms.items():
        if room.is_free():
            free_rooms.append(room_id)

    return free_rooms


"""
 
    WEB API

"""
###############
###User data###
###############

# /api/login
@app.route("/api/login", methods = ["POST"])
def login():
    name, password = request.form["name"], request.form["password"]
    http_response = ""

    salt = execSQL('SELECT Salt FROM Users WHERE Name == ?;', (name,))
    
    if salt:
        hash = hashlib.sha3_224()
        hash.update(password.encode("utf-8"))
        hash.update(salt.encode("utf-8"))
        password = hash.hexdigest()
    
    uid = execSQL('SELECT ID FROM Users WHERE Name == ? and Password == ?;', (name, password))
    if uid and uid >= 0:
        http_response = '{{"token":"{0}", "uid":"{1}"}}'.format(auth.new_token(uid), uid)
    else:
        http_response = '{"error":"The entered data is incorrect"}'

    return Response(response=http_response, content_type="application/json")

# /api/logout?token=kbTiQHNl2D…Rmu
@app.route("/api/logout", methods = ["POST"])
def logout():
    token = request.args.get("token")
    http_response = ""

    if not auth.is_token_expired(token):
        auth.del_token(token)
        http_response = '{"status":"ok"}'
    else:
        http_response = '{"error":"Api token is incorrect"}'

    return Response(response=http_response, mimetype="application/json")

# /api/register_user
@app.route("/api/register_user", methods = ["POST"])
def register_user():
    name, email, password = request.form["name"], request.form["email"], request.form["password"]
    http_response = ""

    salt = secrets.token_hex(16)
    hash = hashlib.sha3_224()
    hash.update(password.encode("utf-8"))
    hash.update(salt.encode("utf-8"))
    password = hash.hexdigest()

    if not execSQL('SELECT * FROM Users WHERE Name=?;', (name,)):
        sql = 'INSERT INTO Users (Name{0}, Password, Salt) VALUES (?{1}, ?, ?);'
        if email:
            sql = sql.format(", Email", ", ?")
            execSQL(sql, (name, email, password, salt))
        else:
            sql = sql.format("", "")
            execSQL(sql, (name, password, salt))

        http_response = '{"status":"ok"}'
    else:
        http_response = '{"error":"This user already exists"}'

    return Response(response=http_response, mimetype="application/json")

# /api/change_email?token=kbTiQHNl2D…Rmu
@app.route("/api/change_email", methods = ["POST"])
def change_email():
    token = request.args.get("token")
    new_email, old_email = request.form["new_email"], request.form["old_email"]
    http_response = ""

    uid = auth.get_uid(token)
    
    if uid:
        if new_email != old_email:
            currentEmail = execSQL('SELECT Email FROM Users WHERE ID=?;', (uid,))
            
            # if user has no email
            if not currentEmail:
                currentEmail = ""

            print(currentEmail)
            if currentEmail == old_email:
                execSQL('UPDATE Users SET Email=? WHERE ID=?;', (new_email, uid))
                http_response = '{"status":"ok"}'
            else:
                http_response = '{"error":"Old email address not found"}'
        else:
            http_response = '{"error":"Email addresses are equal"}'
    else:
        http_response = '{"error":"Api token is incorrect"}'

    return Response(response=http_response, mimetype="application/json")

# /api/get_rating/?token=6t16fy…xFw&limit=50&offset=0
@app.route("/api/get_rating", methods = ["GET"])
def get_rating():
    token = request.args.get("token")
    offset = request.args.get("offset")
    limit = request.args.get("limit")
    http_response = ""

    if not auth.is_token_expired(token):
        expr = 'Won*1.0/"Total"'
        top = execSQL(f'SELECT ID, Name, "Total", {expr} AS WinRate FROM Users WHERE "Total" > 0 ORDER BY WinRate DESC LIMIT ? OFFSET ?;', (limit, offset))
        print(top)
        if top:
            http_response = "["
            for i in top:
                item = '{{"id":{0},"name":"{1}","total":{2},"win_rate":{3}}},'.format(*i)
                http_response += item
            http_response = http_response[:-1] + "]"
        else:
            http_response = '{"error":"Out of range"}'
    else:
        http_response = '{"error":"Api token is incorrect"}'

    return Response(response=http_response, mimetype="application/json")

# /api/get_chips/?token=6t16fy…xFw
@app.route("/api/get_chips", methods = ["GET"])
def get_chips():
    token = request.args.get("token")
    http_response = ""

    uid = auth.get_uid(token)

    if uid:
        chips = execSQL('SELECT Chips FROM Users WHERE ID = ?;', (uid,))
        http_response = '{{"chips":{0}}}'.format(chips)
    else:
        http_response = '{"error":"Api token is incorrect"}'
    
    return Response(response=http_response, mimetype="application/json")

# /api/get_chips/?token=6t16fy…xFw
@app.route("/api/get_uid", methods = ["GET"])
def get_UId():
    token = request.args.get("token")
    uid = auth.get_uid(token)

    return str(uid)

#/api/get_username/13?token=6t16fy…xFw
@app.route("/api/get_username/<int:uid>", methods = ["GET"])
def get_username(uid):
    token = request.args.get("token")
    http_response = ""

    if not auth.is_token_expired(token):
        uname = execSQL('SELECT Name FROM Users WHERE ID = ?;', (uid,))
        http_response = '{{"username":"{0}"}}'.format(uname)
    else:
        http_response = '{"error":"Api token is incorrect"}'

    return Response(response=http_response, mimetype="application/json")



####################
##avatar functions##
####################
@app.route('/api/upload_avatar', methods=['POST'])
def upload_avatar():

    token = request.form.get('token')

    if 'avatar' not in request.files:
        return "No avatar file provided", 400

    avatar_file = request.files['avatar']

    if not os.path.exists(UPLOAD_AVATAR_FOLDER):
        os.makedirs(UPLOAD_AVATAR_FOLDER)

    filename = f"{auth.get_uid(token)}.png"

    # Сохранение файла на сервере
    file_path = os.path.join(UPLOAD_AVATAR_FOLDER, filename)
    avatar_file.save(file_path)

    return "Avatar uploaded successfully"

@app.route("/api/getAvatar/<uid>", methods=["GET"])
def get_avatar(uid):
    # Создаем имя файла из переданного UID
    file_name = str(uid) + ".png"

    # Полный путь к файлу
    file_path = UPLOAD_AVATAR_FOLDER + file_name

    try:
        # Открываем изображение или создаем новое, если файл не существует
        image = Image.open(file_path)
    except FileNotFoundError:
        image = Image.open(UPLOAD_AVATAR_FOLDER + "StandartPhoto.png")

    # Возвращаем файл клиенту
    return send_file(file_path, mimetype="image/png")

#####################
###Admin functions###
#####################
@app.route("/api/GetChips_admin", methods = ["POST"])
def _getChips_admin():
    token = request.form["token"]
    _chips = request.form["Chips"]

    uid = auth.get_uid(token)
    
    if uid:

        AdminRang = execSQL('SELECT isAdmin FROM Users WHERE ID=?;', (uid,))
            
        if(AdminRang == 1):
            oldChips = execSQL('SELECT Chips FROM Users WHERE ID=?;', (uid,))

            execSQL('UPDATE Users SET Chips=? WHERE ID=?;', (int(oldChips)+int(_chips), uid))

            print("admin get chips: " + str(uid) + " - " + str(int(oldChips)+int(_chips)))

            return str(int(oldChips)+int(_chips))

        else:
            print("some one trying to cheat!!!! -- " + str(uid))
        
    else:
        return "error: Api token is incorrect"

# help .html page
@app.route("/helper", methods=["GET"])
def helper():
    return render_template("helper.html")

##################
###Start server###
if __name__ == "__main__":
    #app.run(debug=DEBUG, threaded=True)
    socketio.run(app, debug=DEBUG, use_reloader=False)
