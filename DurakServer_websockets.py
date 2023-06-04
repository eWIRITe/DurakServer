import asyncio
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

import json
from websockets import serve, WebSocketServerProtocol


class AuthServer:
    def __init__(self):
        self.sessions = {}

    def new_token(self, uid):
        token = secrets.token_hex()
        self.sessions[token] = {"uid": uid}
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
connections = set()

SECRET_KEY = "2738b417b94cce4f7f70953a41f277a3840219d61e32cfc45246949c9dd2c373"
ALLOWED_AVATAR_EXTENSIONS = {"png"}
UPLOAD_AVATAR_FOLDER = "C:/DurakServer/avatars/"
DATABASE = "C:/DurakServer/durak.db"
COMISSION = 0.1
DEBUG = True

g_durak_rooms = {}

link_db = None

###############
###Data base###
###############

def get_db():
    global link_db
    # if we are still not db connected
    if not hasattr(link_db, "link_db"):
        link_db = sqlite3.connect(DATABASE)

    return link_db
def close_db(error):
    global link_db
    # close db connection if it does connected
    if hasattr(link_db, "link_db"):
        link_db.close()
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


####################
###Game functions###
####################

async def cl_distribution(cards, sid, uid, RoomID):
    for card in cards:
        ### send to owrUser ###
        data = {"suit": str(Card.from_byte(card).__str__()[-1]), "nominal": str(Card.from_byte(card).__str__()[0]) + str(Card.from_byte(card).__str__()[1])}

        message = {
            "eventType": "playerGetCard",
            "data": json.dumps(data)
        }
        await sid.send(json.dumps(message))

        ### send to atherUsers ###
        room = g_durak_rooms[str(RoomID)]

        data = {"UserID": uid}

        message = {
            "eventType": "atherUserGotCard",
            "data": json.dumps(data)
        }
        for _sid in room.get_sidOfAllPlayers():
            if(_sid != sid): await _sid.send(json.dumps(message))


async def cl_turn(RoomPlayersSids, uid):
    for sid in RoomPlayersSids:
        data = {"uid": uid}

        message = {
            "eventType": "cl_turn",
            "data": json.dumps(data)
        }
        await sid.send(json.dumps(message))

async def cl_grab(RoomID, uid):
    RoomID.send(json.dumps({"cl_grab": {"uid": uid}}))

async def cl_fold(RoomID, uid):
    RoomID.send(json.dumps({"cl_fold": {"uid": uid}}))

async def cl_pass(RoomID, uid):
    RoomID.send(json.dumps({"cl_pass": {"uid": uid}}))

async def cl_start(RoomID, first, trump, bet, players):
    room = g_durak_rooms[str(RoomID)]

    execSQL('UPDATE Users SET Chips = Chips - ? WHERE ID IN (?);', (bet, str(players)))

    data = {"first": first, "trump": trump.get_byte()}

    message = {
        "eventType": "ready",
        "data": json.dumps(data)
    }
    for sid in room.get_sidOfAllPlayers():
        await sid.send(json.dumps(message))

async def cl_finish(RoomID, winners):
    room = g_durak_rooms[str(RoomID)]

    for uid in winners:
        execSQL('UPDATE Users SET Chips = Chips + ? WHERE ID = ?;', (g_durak_rooms[RoomID]["bet"] // len(winners),uid))


    data = {{"winners": winners}}

    message = {
        "eventType": "cl_finish",
        "data": json.dumps(data)
    }
    for sid in room.get_sidOfAllPlayers():
        await sid.send(json.dumps(message))

##############################
###Request handle functions###
##############################

###freeRooms###
async def getFreeRooms(sid = None):
    free_rooms = []
    for room_id, room in g_durak_rooms.items():
        if room.is_free():
            free_rooms.append(room_id)

    data = {
        "FreeRoomsID": free_rooms
    }

    message = {
        "eventType": "FreeRooms",
        "data": json.dumps(data)
    }

    if(sid!=None): await sid.send(json.dumps(message))
    else:
        for sid in connections:
            await sid.send(json.dumps(message))

###Whatsup###
async def whatsup(token, UserID, RoomID, sid):

	if not UserID:
		await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))
		print("A user got mistake: incorrect token(whatsup funktion), his token was: " + token)
		return

	room = g_durak_rooms[RoomID]

	if not room:
		await sid.send(json.dumps({"eventType": "error", "data": "incorrect Room"}))
		print("A user got mistake: incorrect Room(whatsup funktion), his RoomID was: " + RoomID)
		return

	room.whatsup()

###Battle###
async def battle(data, token, UserID, sid, RoomID):
    if not UserID:
        await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))
        print("A user got a mistake: incorrect token (battle function), his token was: " + token)
        return

    room = g_durak_rooms[RoomID]

    if not room:
        await sid.send(json.dumps({"eventType": "error", "data": "incorrect Room"}))
        print("A user got a mistake: incorrect Room (battle function), his RoomID was: " + RoomID)
        return

    attacked = [Card.from_byte(data["attacked"][i]) for i in data["attacked"]]
    attacking = [Card.from_byte(data["attacking"][i]) for i in data["attacking"]]

    if room.battle(UserID, attacked, attacking):
        for sid in room.get_sidOfAllPlayers():
            await sid.send(json.dumps({"eventType": "cl_battle", "data": {"uid": UserID, "attacked": data["attacked"], "attacking": data["attacking"]}}))

###Transfer###
async def transfer(UserID, RoomID, sid):

    if not UserID:
        await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))
        print("A user got a mistake: incorrect token (transfer function), his token was: " + token)
        return

    room = g_durak_rooms[RoomID]

    if not room:
        await sid.send(json.dumps({"eventType": "error", "data": "incorrect Room"}))
        print("A user got a mistake: incorrect Room (transfer function), his RoomID was: " + RoomID)
        return

    if room.transfer(UserID, Card.from_byte(json["card"])):
        for sid in room.get_sidOfAllPlayers():
            await sid.send(json.dumps({"eventType": "cl_transfer", "data": {"uid": UserID, "card": data["card"]}}))

###Create room###
async def createRoom(token, UserID, data, sid):
    if not UserID:
        await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))
        print("A user got a mistake: incorrect token(createRoom function), his token was: " + token)
        return False

    if float(execSQL("SELECT Chips FROM Users WHERE ID = ?;", (UserID,))) < data["bet"]:
        if DEBUG:
            print("the user: " + token + ", doesn't have enough chips to play")
        await sid.send(json.dumps({"eventType": "error", "data": "Not enough chips"}))
        return False

    ##Get commission
    commission = float(execSQL('SELECT Comission FROM Config;', ""))

    if not validRoomJSON(data):
        await sid.send(json.dumps({"eventType": "error", "data": "incorrect JSON"}))

    # Generate rid
    RoomID = str(10000 + secrets.randbelow(100000 - 10000))

    # Create room
    room = Room(RoomID, data, commission)

    room.set_distribution_callback(cl_distribution)
    room.set_grab_callback(cl_grab)
    room.set_turn_callback(cl_turn)
    room.set_fold_callback(cl_fold)
    room.set_pass_callback(cl_pass)
    room.set_start_callback(cl_start)
    room.set_finish_callback(cl_finish)

    # Add room in the list
    g_durak_rooms[RoomID] = room

    data["RoomID"] = RoomID

    # Join user
    if not room.join(UserID, sid):
        if DEBUG: print("User: " + UserID + ", got an error with entering the room: " + RoomID)
        await sid.send(json.dumps({"eventType": "error", "data": "Room is not free or there is an error"}))
    else:
        if DEBUG: print("User: " + UserID + ", entered the room: " + RoomID)
        await sid.send(json.dumps({"eventType": "cl_enterInTheRoomAsOwner", "data": f"{data}"}))

    await getFreeRooms()

###join room###
async def joinRoom(sid, UserID, RoomID, data):

    ##Check UId
    if not UserID:
        print("incorrect token")
        await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))
        return

    # get room
    room = g_durak_rooms[RoomID]
    # if there is no room by rid
    if not room:
        if(DEBUG): print("incorrect room")
        await sid.send(json.dumps({"eventType": "error", "data": "incorrect room"}))
        return

    if float(execSQL("SELECT Chips FROM Users WHERE ID = ?;", (UserID,))) < room.get_bet():
        if(DEBUG): print("Not enough chips")
        await sid.send(json.dumps({"eventType": "error", "data": "Not enough chips"}))
        return

    # if room is private and keys is not eq
    #if room.is_private():
    #    if(DEBUG): print("Room is private")
    #    sid.send(json.dumps({"eventType": "error", "data": "Room is private"}))
    #    return

    # add player in room
    # if there is no free place or player is already in room
    if not room.join(UserID, sid):
        print("Room is not free")
        await sid.send(json.dumps({"eventType": "error", "data": "Room is not free"}))
        return

    else:
        del data["Token"]
        data["uid"] = UserID
        data["RoomID"] = str(data["RoomID"])
        data["roomOwner"] = room.get_roomOwner()

        if(DEBUG): print("User: " + UserID + ", enter in the room: " + RoomID)
        await sid.send(json.dumps({"eventType": "cl_enterInTheRoom", "data": f"{data}"}))


        for _sid in room.get_sidOfAllPlayers():
            if(_sid != sid): await _sid.send(json.dumps({"eventType": "cl_joinRoom", "data": f"{data}"}))

###exit room###
async def exitRoom(RoomID, UserID):
    return True

###ready###
async def Ready(RoomID):
    return True

###getUId###
async def get_UId(token, sid):
    UserID = auth.get_uid(token)
    if(DEBUG): print("The sid: " + str(sid) + ", asked for id: " + UserID)
    await sid.send(json.dumps({"eventType": "ID", "data": f"{UserID}"}))

###get userName###
async def get_username(token, sid):

    if not auth.is_token_expired(token):
        uname = execSQL('SELECT Name FROM Users WHERE ID = ?;', (auth.get_uid(token),))
        if(DEBUG): print("The token:" + token + ", got name: " + uname)
        await sid.send(uname)
    else:
        print("The request with sid: " + sid + ", got error, becouse of incorrect token: " + token)
        await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))

###login###
async def login(sid, data):
    name, password = data["name"], data["password"]

    salt = execSQL('SELECT Salt FROM Users WHERE Name == ?;', (name,))

    if salt:
        hash = hashlib.sha3_224()
        hash.update(password.encode("utf-8"))
        hash.update(salt.encode("utf-8"))
        password = hash.hexdigest()

    UserID = execSQL('SELECT ID FROM Users WHERE Name == ? and Password == ?;', (name, password))

    if UserID and UserID >= 0:
        if(DEBUG): print("User: " + name + ", sucsessedLogin")
        await sid.send(json.dumps({"eventType": "sucsessedLogin", "data": "{'token': '%s'}" % (auth.new_token(UserID), )}))
    else:
        print("The user: password-" + password + ", name-" + name + ": got error with uid-" + str(UserID))
        await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))

###signin###
async def register_user(sid, data):
    name, email, password =  data["name"], data["email"], data["password"]

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

        await sid.send(json.dumps({"eventType": "sucsessedSignIn", "data": ""}))
        print("There is new user: " + name + " : " + email + " : " + password)

    else:
        await sid.send(json.dumps({"eventType": "error", "data": "user already exists"}))
        if(DEBUG): print("user: " + name + ", tryed register again")
    return

##getChips###
async def getChips(token, sid):

    uid = auth.get_uid(token)

    if uid:
        chips = execSQL('SELECT Chips FROM Users WHERE ID = ?;', (uid,))
        data = {
            "chips": chips
        }

        message = {
            "eventType": "Chips",
            "data": json.dumps(data)
        }
    else:
        message = {"eventType": "error", "data": "get chips error"}

    await sid.send(json.dumps(message))

###GetRoomPlayers###
async def getRoomPlayers(sid, RoomID):
    room = g_durak_rooms[str(RoomID)]
    data = {
        "RoomID": RoomID,
        "PlayersID": room.get_idOfAllPlayers()
    }

    message = {
        "eventType": "roomPlayersID",
        "data": json.dumps(data)
    }

    for sid in room.get_sidOfAllPlayers():
        await sid.send(json.dumps(message))




############################
###input requests handler###
############################

async def ws_handle(websocket, path):
    try:
        sid = websocket
        connections.add(sid)
        async for message in websocket:
            __data = json.loads(message)
            data = json.loads(__data["data"])
            print(message)
            print(data)
            if "eventType" in __data:
                action = __data["eventType"]

                # action whatsup
                if action == "srv_whatsup":
                    await whatsup(data["token"], auth.get_uid(data["token"]), data["RoomID"])

                # action battle
                elif action == "srv_battle":
                    await battle(data, data["token"], auth.get_uid(data["token"]), sid, data["RoomID"])

                # transfer
                elif action == "srv_transfer":
                    await transfer(auth.get_uid(data["token"]), data["RoomID"])

                # getRooms
                elif action == "getFreeRooms":
                    await getFreeRooms(sid)

                # createRoom
                elif action == "srv_createRoom":
                    await createRoom(data["token"], auth.get_uid(data["token"]), data, sid)

                # joinRoom
                elif action == "srv_joinRoom":
                    await joinRoom(sid, auth.get_uid(data["Token"]), str(data["RoomID"]), data)

                # exitRoom
                elif action == "srv_exit":
                    print(connections)
                    connections.remove(sid);

                    room = g_durak_rooms[str(data["rid"])]
                    UserID = auth.get_uid(data["token"])

                    await room.leave(UserID)

                    data = {
                        "uid": UserID
                    }

                    message = {
                        "eventType": "cl_leaveRoom",
                        "data": json.dumps(data)
                    }

                    for sid in room.get_sidOfAllPlayers():
                        await sid.send(json.dumps(message))

                # ready
                elif action == "srv_ready":
                    if(DEBUG): print("Find room")
                    room = g_durak_rooms[str(data["RoomID"])]
                    if(DEBUG): print("Found room: " + str(data["RoomID"]))

                    if(room == None):
                        print ("SID: " + sid + "trying connect to an incorrect room")
                        return

                    room.set_ready()

                    if(DEBUG): print("Before start function")
                    await room.start()
                    if(DEBUG): print("After start function")

                # login
                elif action == "Login":
                    await login(sid, data)

                # Signin
                elif action == "Signin":
                    await register_user(sid, data)

                # SignOut
                elif action == "logout":
                    # Handle the signout action
                    pass

                # Get UId
                elif action == "getId":
                    await get_UId(data["token"], sid)

                elif action == "get_UserName":
                    await get_username(data["token"], sid)

                elif action == "getChips":
                    await getChips(data["token"], sid)

                elif action == "get_RoomPlayers":
                    await getRoomPlayers(sid, data["RoomID"])

                else:
                    await sid.send(json.dumps({"eventType": "error", "data": "Unknown action"}))

            else:
                await sid.send(json.dumps({"eventType": "error", "data": "Unknown action"}))

    except Exception as e:
        print(f"WS Error: {e}")


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

if __name__ == "__main__":

    start_server = serve(ws_handle, "127.0.0.1", 5000)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
