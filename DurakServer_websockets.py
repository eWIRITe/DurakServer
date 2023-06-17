import asyncio
import base64
import datetime
import hashlib
import json
import os
import secrets
import sqlite3

from websockets import serve

from Card import Card
from Enums import Suit, Nominal
from Room import Room


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


class DataBase:

    @staticmethod
    def get_db():
        global link_db
        # if we are still not db connected
        if not hasattr(link_db, "link_db"):
            link_db = sqlite3.connect(DATABASE)

        return link_db

    @staticmethod
    def close_db(error):
        global link_db
        # close db connection if it does connected
        if hasattr(link_db, "link_db"):
            link_db.close()

    @staticmethod
    def execSQL(sql, args):
        db = DataBase.get_db()
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


class TransleteCardData:
    @staticmethod
    def transform_nominal(_nominal):
        global nominal

        if _nominal == "2 ":
            nominal = Nominal.TWO
        elif _nominal == "3 ":
            nominal = Nominal.THREE
        elif _nominal == "4 ":
            nominal = Nominal.FOUR
        elif _nominal == "5 ":
            nominal = Nominal.FIVE
        elif _nominal == "6 ":
            nominal = Nominal.SIX
        elif _nominal == "7 ":
            nominal = Nominal.SEVEN
        elif _nominal == "8 ":
            nominal = Nominal.EIGHT
        elif _nominal == "9 ":
            nominal = Nominal.NINE
        elif _nominal == "10":
            nominal = Nominal.TEN
        elif _nominal == "В ":
            nominal = Nominal.JACK
        elif _nominal == "Д ":
            nominal = Nominal.QUEEN
        elif _nominal == "К ":
            nominal = Nominal.KING
        elif _nominal == "Т ":
            nominal = Nominal.ACE

        return nominal

    @staticmethod
    def transform_suit(_suit):
        global suit

        if _suit == "♥":
            suit = Suit.HEART
        elif _suit == "♦":
            suit = Suit.TILE
        elif _suit == "♠":
            suit = Suit.PIKES
        elif _suit == "♣":
            suit = Suit.CLOVERS

        return suit


class AdminMetods:
    @staticmethod
    async def admin_getChips(UserID, newChips):
        # if you need to give admin rights from database, and check it
        """
        if UserID:
            admin_rang = float(DataBase.execSQL('SELECT isAdmin FROM Users WHERE ID=?;', (UserID,)))

            if admin_rang == 1:
                old_chips = DataBase.execSQL('SELECT Chips FROM Users WHERE ID = ?;', (UserID,))

                DataBase.execSQL('UPDATE Users SET Chips=? WHERE ID=?;', (int(old_chips) + int(newChips), UserID))

                print("admin get chips: " + str(UserID) + " - " + str(int(old_chips) + int(newChips)))

                return str(int(old_chips) + int(newChips))

            else:
                print("some one trying to cheat!!!! -- " + str(UserID))

        else:
            return "error: Api token is incorrect"

        """

        # if you dont need to make any check, so new admin could just get admin program edition

        old_chips = DataBase.execSQL('SELECT Chips FROM Users WHERE ID = ?;', (UserID,))

        DataBase.execSQL('UPDATE Users SET Chips=? WHERE ID=?;', (int(old_chips) + int(newChips), UserID))

        print("admin get chips: " + str(UserID) + " - " + str(int(old_chips) + int(newChips)))

        return str(int(old_chips) + int(newChips))


class GameFunctions:

    @staticmethod
    async def cl_distribution(cards, sid, uid, RoomID):
        for card in cards:
            ### send to owrUser ###
            data = {"suit": str(card.__str__()[-1]),
                    "nominal": str(card.__str__()[0]) + str(card.__str__()[1])}

            message = {
                "eventType": "GetCard",
                "data": json.dumps(data)
            }

            print(message)
            await sid.send(json.dumps(message))

            ### send to atherUsers ###
            room = g_durak_rooms[str(RoomID)]

            data = {"UserID": uid}

            message = {
                "eventType": "cl_gotCard",
                "data": json.dumps(data)
            }
            for _sid in room.get_sidOfAllPlayers():
                print(message)
                if _sid != sid: await _sid.send(json.dumps(message))

    @staticmethod
    async def cl_sendRoles(Players):
        players_roles_list = []

        for player in Players:
            players_roles_list.append({"UserID": player.get_uid(), "role": int(player.get_RoleValue())})

        message = {
            "eventType": "cl_role",
            "data": f"{players_roles_list}"
        }

        for player in Players:
            print(message)
            await player.get_sid().send(json.dumps(message))

    # m_foldCallback
    @staticmethod
    async def cl_Fold(RoomID):
        room = g_durak_rooms[str(RoomID)]

        message = {
            "eventType": "cl_fold",
            "data": "NoNData"
        }

        for sid in room.get_sidOfAllPlayers():
            print(message)
            await sid.send(json.dumps(message))

    # m_playerFoldCallback
    @staticmethod
    async def cl_sendFold(RoomID, uid):
        room = g_durak_rooms[str(RoomID)]

        data = {"UserID": uid}

        message = {
            "eventType": "cl_playerFold",
            "data": json.dumps(data)
        }

        for sid in room.get_sidOfAllPlayers():
            print(message)
            await sid.send(json.dumps(message))

    # m_grabCallback
    @staticmethod
    async def cl_grab(RoomID):
        room = g_durak_rooms[str(RoomID)]

        message = {
            "eventType": "grab",
            "data": "NoNData"
        }

        for sid in room.get_sidOfAllPlayers():
            print(message)
            await sid.send(json.dumps(message))

    # m_clGrabCallback
    @staticmethod
    async def cl_sendGrab(RoomID):
        room = g_durak_rooms[str(RoomID)]

        message = {
            "eventType": "cl_grab",
            "data": "NoNData"
        }

        for sid in room.get_sidOfAllPlayers():
            print(message)
            await sid.send(json.dumps(message))

    # m_passCallback
    @staticmethod
    async def cl_pass(RoomID, uid):
        room = g_durak_rooms[str(RoomID)]

        data = {"UserID": uid}

        message = {
            "eventType": "cl_pass",
            "data": data
        }

        for sid in room.get_sidOfAllPlayers():
            print(message)
            await sid.send(json.dumps(message))

    @staticmethod
    async def cl_start(RoomID, trump, bet, playersID):
        print("cl_start callBack")
        room = g_durak_rooms[str(RoomID)]

        DataBase.execSQL('UPDATE Users SET Chips = Chips - ? WHERE ID IN (?);', (bet, str(playersID)))

        print("trump: " + str(trump))
        trump_card = {"suit": str(trump.__str__()[-1]), "nominal": str(trump.__str__()[0]) + str(trump.__str__()[1])}
        print(trump_card)

        data = {"trump": trump_card}

        message = {
            "eventType": "ready",
            "data": json.dumps(data)
        }

        for sid in room.get_sidOfAllPlayers():
            print(message)
            await sid.send(json.dumps(message))

    @staticmethod
    async def cl_finish(RoomID, winners):
        room = g_durak_rooms[str(RoomID)]

        for uid in winners:
            DataBase.execSQL('UPDATE Users SET Chips = Chips + ? WHERE ID = ?;',
                             (g_durak_rooms[RoomID]["bet"] // len(winners), uid))

        data = {{"winners": winners}}

        message = {
            "eventType": "cl_finish",
            "data": json.dumps(data)
        }
        for sid in room.get_sidOfAllPlayers():
            print(message)
            await sid.send(json.dumps(message))

    @staticmethod
    async def cl_throw(playersSId, card, UId, _sid):
        # card would looks like: "{"suit": "♥", "nominal": "2 "}"

        # generate card
        card = {"suit": str(card.__str__()[-1]),
                "nominal": str(card.__str__()[0]) + str(card.__str__()[1])}

        # destroy player card
        data = {"UId": int(UId), "card": card}
        message = {
            "eventType": "DestroyCard",
            "data": json.dumps(data)
        }

        print(message)

        await _sid.send(json.dumps(message))

        # send throu card to every room player
        message = {
            "eventType": "cl_ThrowedCard",
            "data": json.dumps(data)
        }
        for sid in playersSId:
            print(message)
            await sid.send(json.dumps(message))

        # send destroy card to every room player
        data = {
            "UserID": UId
        }
        message = {
            "eventType": "cl_destroyCard",
            "data": json.dumps(data)
        }
        for sid in playersSId:
            print(message)
            await sid.send(json.dumps(message))

    @staticmethod
    async def cl_beat(_sid, RoomID, uid, attackCard, attackingCard):
        room = g_durak_rooms[str(RoomID)]

        # card would looks like: "{"suit": "♥", "nominal": "2 "}"

        # create cards
        attackCard = {"suit": str(attackCard.__str__()[-1]),
                      "nominal": str(attackCard.__str__()[0]) + str(attackCard.__str__()[1])}
        attackingCard = {"suit": str(attackingCard.__str__()[-1]),
                         "nominal": str(attackingCard.__str__()[0]) + str(attackingCard.__str__()[1])}

        # send destroy card to user
        data = {"UId": int(uid), "card": attackingCard}

        message = {
            "eventType": "DestroyCard",
            "data": json.dumps(data)
        }

        print(message)
        await _sid.send(json.dumps(message))

        # send beat to every user
        data = {"UserID": uid, "attacedCard": attackCard, "attacingCard": attackingCard}
        message = {
            "eventType": "cl_BeatCard",
            "data": json.dumps(data)
        }
        for sid in room.get_sidOfAllPlayers():
            print(message)
            await sid.send(json.dumps(message))

        # send destroy card to every user
        data = {"UserID": uid}
        message = {
            "eventType": "cl_destroyCard",
            "data": json.dumps(data)
        }
        for sid in room.get_sidOfAllPlayers():
            print(message)
            await sid.send(json.dumps(message))

    @staticmethod
    async def cl_sendImage(uid, sid, image):
        data = {
            "UserID": uid,
            "avatarImage": image
        }

        message = {
            "eventType": "cl_getImage",
            "data": json.dumps(data)
        }

        print(message)
        await sid.send(json.dumps(message))


class GetFunctions:
    @staticmethod
    async def getFreeRooms(sid=None):
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

        if sid is not None:
            await sid.send(json.dumps(message))
        else:
            for sid in connections:
                await sid.send(json.dumps(message))

    @staticmethod
    async def get_UId(token, sid):
        UserID = auth.get_uid(token)
        await sid.send(json.dumps({"eventType": "cl_getId", "data": f"{UserID}"}))

    @staticmethod
    async def get_username(token, sid):
        if not auth.is_token_expired(token):
            uname = DataBase.execSQL('SELECT Name FROM Users WHERE ID = ?;', (auth.get_uid(token),))
            await sid.send(uname)
        else:
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))

    @staticmethod
    async def getChips(token, sid):
        uid = auth.get_uid(token)

        if uid:
            chips = DataBase.execSQL('SELECT Chips FROM Users WHERE ID = ?;', (uid,))
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

    @staticmethod
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


class PlayingMetods:
    @staticmethod
    async def UserTrowCard(RoomID, card, UserID, sid):
        room = g_durak_rooms[str(RoomID)]

        _suit = TransleteCardData.transform_suit(card["suit"])
        _nominal = TransleteCardData.transform_nominal(card["nominal"])

        card = Card(_suit, _nominal)

        await room.throw(sid, card, UserID)

    @staticmethod
    async def Whatsup(token, UserID, RoomID, sid):
        if not UserID:
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))
            print("A user got mistake: incorrect token(whatsup funktion), his token was: " + token)
            return

        room = g_durak_rooms[str(RoomID)]

        if not room:
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect Room"}))
            print("A user got mistake: incorrect Room(whatsup funktion), his RoomID was: " + RoomID)
            return

        room.whatsup()

    @staticmethod
    async def Battle(sid, data, UserID, RoomID):
        room = g_durak_rooms[str(RoomID)]

        if not UserID:
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))
            print("A user got a mistake: incorrect token (battle function), his token was")
            return

        if not room:
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect Room"}))
            print("A user got a mistake: incorrect Room (battle function), his RoomID was: " + RoomID)
            return

        attacked = Card(TransleteCardData.transform_suit(data["attacedCard"]["suit"]),
                        TransleteCardData.transform_nominal(data["attacedCard"]["nominal"]))
        attacking = Card(TransleteCardData.transform_suit(data["attacingCard"]["suit"]),
                         TransleteCardData.transform_nominal(data["attacingCard"]["nominal"]))

        await room.battle(sid, UserID, attacked, attacking)

    @staticmethod
    async def Transfer(data, UserID, RoomID, sid, token):
        if not UserID:
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))
            print("A user got a mistake: incorrect token (transfer function), his token was: " + token)
            return

        room = g_durak_rooms[str(RoomID)]

        if not room:
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect Room"}))
            print("A user got a mistake: incorrect Room (transfer function), his RoomID was: " + RoomID)
            return

        if room.transfer(UserID, Card.from_byte(data["card"])):
            for sid in room.get_sidOfAllPlayers():
                await sid.send(json.dumps({"eventType": "cl_transfer", "data": {"uid": UserID, "card": data["card"]}}))

    @staticmethod
    async def Fold(UserID, RoomID):
        room = g_durak_rooms[str(RoomID)]
        if not room:
            if DEBUG: print("\nRoom: " + RoomID + " is not founded.\n")
            return

        await room.cl_fold(UserID)

    @staticmethod
    async def Grab(UserID, RoomID):
        room = g_durak_rooms[str(RoomID)]
        if not room:
            return

        await room.cl_grab(UserID)

    @staticmethod
    async def Pass(UserID, RoomID):
        room = g_durak_rooms[str(RoomID)]
        if not room:
            return

        await room.cl_pass(UserID)


class UserEntering:
    @staticmethod
    async def createRoom(token, UserID, data, sid):
        if not UserID:
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))
            print("A user got a mistake: incorrect token(createRoom function), his token was: " + token)
            return False

        if float(DataBase.execSQL("SELECT Chips FROM Users WHERE ID = ?;", (UserID,))) < data["bet"]:
            if DEBUG:
                print("the user: " + token + ", doesn't have enough chips to play")
            await sid.send(json.dumps({"eventType": "error", "data": "Not enough chips"}))
            return False

        ##Get commission
        commission = float(DataBase.execSQL('SELECT Comission FROM Config;', ""))

        if not validRoomJSON(data):
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect JSON"}))

        # Generate rid
        RoomID = str(10000 + secrets.randbelow(100000 - 10000))

        # Create room
        room = Room(RoomID, data, commission)

        room.set_distribution_callback(GameFunctions.cl_distribution)
        room.set_grab_callback(GameFunctions.cl_grab)
        room.set_clGrab_callback(GameFunctions.cl_sendGrab)
        room.set_giveRoles_callback(GameFunctions.cl_sendRoles)
        room.set_throw_callback(GameFunctions.cl_throw)
        room.set_fold_callback(GameFunctions.cl_Fold)
        room.set_playerFold_callback(GameFunctions.cl_sendFold)
        room.set_pass_callback(GameFunctions.cl_pass)
        room.set_start_callback(GameFunctions.cl_start)
        room.set_finish_callback(GameFunctions.cl_finish)
        room.set_beat_callback(GameFunctions.cl_beat)

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

        await GetFunctions.getFreeRooms()

    @staticmethod
    async def joinRoom(sid, UserID, RoomID, data):
        if not UserID:
            if DEBUG: print("incorrect token")
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))
            return

        room = g_durak_rooms[str(RoomID)]

        if not room:
            if DEBUG: print("incorrect room")
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect room"}))
            return
        if float(DataBase.execSQL("SELECT Chips FROM Users WHERE ID = ?;", (UserID,))) < room.get_bet():
            if DEBUG: print("Not enough chips")
            await sid.send(json.dumps({"eventType": "error", "data": "Not enough chips"}))
            return
        if not room.join(UserID, sid):
            if DEBUG: print("Room is not free")
            await sid.send(json.dumps({"eventType": "error", "data": "Room is not free"}))
            return

        del data["Token"]
        data["uid"] = UserID
        data["RoomID"] = str(data["RoomID"])
        data["roomOwner"] = room.m_roomOwner
        data["type"] = room.get_gtype()

        if DEBUG: print("User: " + UserID + ", enter in the room: " + RoomID)
        await sid.send(json.dumps({"eventType": "cl_enterInTheRoom", "data": f"{data}"}))

        for _sid in room.get_sidOfAllPlayers():
            if _sid != sid: await _sid.send(json.dumps({"eventType": "cl_joinRoom", "data": f"{data}"}))

    @staticmethod
    async def exitRoom(sid, RoomID, UserID):
        # get room
        room = g_durak_rooms[str(RoomID)]

        await room.leave(UserID)

        data = {"uid": UserID}
        message = {"eventType": "cl_leaveRoom", "data": json.dumps(data)}

        for sid in room.get_sidOfAllPlayers():
            await sid.send(json.dumps(message))

    ### Enter funtions ###
    @staticmethod
    async def login(sid, data):
        name, password = data["name"], data["password"]

        salt = DataBase.execSQL('SELECT Salt FROM Users WHERE Name == ?;', (name,))

        if salt:
            hash = hashlib.sha3_224()
            hash.update(password.encode("utf-8"))
            hash.update(salt.encode("utf-8"))
            password = hash.hexdigest()

        UserID = DataBase.execSQL('SELECT ID FROM Users WHERE Name == ? and Password == ?;', (name, password))

        if UserID and UserID >= 0:
            if DEBUG: print("User: " + name + ", sucsessedLogin")
            await sid.send(
                json.dumps({"eventType": "sucsessedLogin", "data": "{'token': '%s'}" % (auth.new_token(UserID),)}))
        else:
            await sid.send(json.dumps({"eventType": "error", "data": "incorrect token"}))

    @staticmethod
    async def save_avatar(data):
        user_id = data['UserID']
        avatar_image = data['avatarImage']

        # Decode base64 image data
        image_data = base64.b64decode(avatar_image)

        # Create the folder if it doesn't exist
        if not os.path.exists(UPLOAD_AVATAR_FOLDER):
            os.makedirs(UPLOAD_AVATAR_FOLDER)

        # Save the image to a file with UserID as the filename
        avatar_filename = os.path.join(UPLOAD_AVATAR_FOLDER, str(user_id) + '.png')
        with open(avatar_filename, 'wb') as f:
            f.write(image_data)

        print('Avatar saved:', avatar_filename)

    @staticmethod
    async def get_avatar(sid, user_id):
        # Check if the avatar file exists for the given UserID
        avatar_filename = os.path.join(UPLOAD_AVATAR_FOLDER, str(user_id) + '.png')
        if os.path.exists(avatar_filename):
            with open(avatar_filename, 'rb') as f:
                # Read the image file and encode it as base64
                image_data = f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')

            await GameFunctions.cl_sendImage(user_id, sid, base64_image)

    @staticmethod
    async def register_user(sid, data):
        name, email, password = data["name"], data["email"], data["password"]

        salt = secrets.token_hex(16)
        hash = hashlib.sha3_224()
        hash.update(password.encode("utf-8"))
        hash.update(salt.encode("utf-8"))
        password = hash.hexdigest()

        if not DataBase.execSQL('SELECT * FROM Users WHERE Name=?;', (name,)):
            sql = 'INSERT INTO Users (Name{0}, Password, Salt) VALUES (?{1}, ?, ?);'
            if email:
                sql = sql.format(", Email", ", ?")
                DataBase.execSQL(sql, (name, email, password, salt))
            else:
                sql = sql.format("", "")
                DataBase.execSQL(sql, (name, password, salt))

            await sid.send(json.dumps({"eventType": "sucsessedSignIn", "data": "NoNData"}))
            print("There is new user: " + name + " : " + email + " : " + password)

        else:
            await sid.send(json.dumps({"eventType": "error", "data": "user already exists"}))
            if DEBUG: print("user: " + name + ", tryed register again")
        return


############################
###input requests handler###
############################

async def ws_handle(websocket, path):
    print("new User connected: " + str(websocket))

    try:
        # get sid
        sid = websocket
        # remember sid, to remember this connection
        connections.add(sid)

        ### handle the request ###
        async for message in websocket:

            ### get data ###
            _message = json.loads(message)
            data = json.loads(_message["data"])

            if DEBUG:
                print("request, action: " + str(_message["eventType"]))
                print("reqest, data: " + str(data))

            # hande data
            if "eventType" in _message:
                action = _message["eventType"]

                ### game functions ###

                if action == "srv_Throw":
                    await PlayingMetods.UserTrowCard(data["RoomID"], data["card"], data["UserID"], sid)

                elif action == "srv_whatsup":
                    await PlayingMetods.Whatsup(data, data["token"], auth.get_uid(data["token"]), data["RoomID"])

                elif action == "srv_battle":
                    await PlayingMetods.Battle(sid, data, data["UserID"], data["RoomID"])

                elif action == "srv_transfer":
                    await PlayingMetods.Transfer(data, auth.get_uid(data["token"]), data["RoomID"], sid, data["token"])

                elif action == "srv_pass":
                    await PlayingMetods.Pass(auth.get_uid(data["token"]), data["RoomID"])
                elif action == "srv_grab":
                    await PlayingMetods.Grab(auth.get_uid(data["token"]), data["RoomID"])
                elif action == "srv_fold":
                    await PlayingMetods.Fold(auth.get_uid(data["token"]), data["RoomID"])

                ### room functions ###

                elif action == "srv_createRoom":
                    await UserEntering.createRoom(data["token"], auth.get_uid(data["token"]), data, sid)

                elif action == "srv_joinRoom":
                    await UserEntering.joinRoom(sid, auth.get_uid(data["Token"]), str(data["RoomID"]), data)

                elif action == "srv_exit":
                    await UserEntering.exitRoom(sid, data["rid"], auth.get_uid(data["token"]))

                elif action == "srv_ready":
                    room = g_durak_rooms[str(data["RoomID"])]
                    await room.start()


                ### enter functions ###

                elif action == "Login":
                    await UserEntering.login(sid, data)

                elif action == "Signin":
                    await UserEntering.register_user(sid, data)

                elif action == "logout":
                    pass

                elif action == "setAvatar":
                    await UserEntering.save_avatar(data)

                ### Get functions ###

                elif action == "getId":
                    await GetFunctions.get_UId(data["token"], sid)

                elif action == "get_UserName":
                    await GetFunctions.get_username(data["token"], sid)

                elif action == "getChips":
                    await GetFunctions.getChips(data["token"], sid)

                elif action == "get_RoomPlayers":
                    await GetFunctions.getRoomPlayers(sid, data["RoomID"])

                elif action == "getFreeRooms":
                    await GetFunctions.getFreeRooms(sid)

                elif action == "getAvatar":
                    await UserEntering.get_avatar(sid, data["UserID"])

                ### admin metods ###

                elif action == "admin_getChips":
                    await AdminMetods.admin_getChips(auth.get_uid(data["token"]), data["chips"])

                ### on unknown action ###
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
    print("//////////// Server opened \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\")
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
