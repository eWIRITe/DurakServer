from Enums import Status, Role, status
from Player import Player
from MainDeck import MainDeck
from Deck import Deck
from Battlefield import Battlefield

import datetime


class Room:
    def __init__(self, rid, json, comission=0.1):
        self.m_started = False
        self.m_rid = rid
        self.m_isPrivate = json["isPrivate"]
        self.m_key = json["key"]
        self.m_gType = json["type"]
        self.m_nCards = json["cards"]
        self.m_bet = json["bet"]
        self.m_maxPlayers = json["maxPlayers"]
        self.m_roomOwner = json["roomOwner"]

        self.m_comission = comission

        self.m_status = Status.START

        self.m_actions = []

        self.m_players = []

        self.m_throwers = []

        self.m_trump = None

        self.m_finished = []

        self.m_grab = None

        self.m_opensTurn = None

        self.m_turn = None

        self.m_attacker = None

        self.m_defender = None

        self.m_prevTurn = None

        self.m_loser = None

        self.m_bank = 0

        self.m_mainDeck = None

        self.m_discardPile = None

        self.m_battlefield = None

        # to compare time
        self.m_startTurnTimeStamp = None

        # start room flag
        self.m_isStarted = False

        # first beating flag
        self.m_isFirstBeat = True

        # callbacks
        self.m_distributionCallback = None
        self.m_grabCallback = None
        self.m_giveRoles_callback = None
        self.m_clGrabCallback = None
        self.m_foldCallback = None
        self.m_playerFoldCallback = None
        self.m_passCallback = None
        self.m_startCallback = None
        self.m_finishCallback = None
        self.m_throwCallback = None
        self.m_beatCallback = None
        self.m_startAlone = None
        self.m_writeOffChips = None
        self.m_playerWon = None
        self.m_trumpIsDone = None
        self.m_deckIsEmpty = None

    #####################
    ### set functions ###
    #####################

    def set_ready(self):
        for player in self.m_players:
            player.ready()

        self.m_isStarted = True

    #####################
    ### get functions ###
    #####################

    def get_mainTurnPlayer(self):
        for player in self.m_players:
            if player.get_RoleValue() == 0:
                return player
        return None

    def get_num_playing_players(self):
        count = 0

        for player in self.m_players:
            if player.is_playing():
                count += 1

        return count

    def get_trump(self):
        return self.m_trump

    def get_rid(self):
        return self.m_rid

    def get_key(self):
        return self.m_key

    def get_bet(self):
        return self.m_bet

    def get_gtype(self):
        return self.m_gType

    def get_maxplayers(self):
        return self.m_maxPlayers

    def is_private(self):
        return self.m_isPrivate

    def is_started(self):
        return self.m_isStarted

    def is_free(self):
        if not self.m_isStarted:
            if self.m_maxPlayers > len(self.m_players):
                return True

        return False

    def has_player_card(self, uid, card):
        player = self.get_player(uid)
        if not player:
            return

        return player.has_card(card)

    def get_num_empty_seats(self):
        return self.m_maxPlayers - len(self.m_players)

    def get_num_taken_seats(self):
        return self.m_maxPlayers - self.get_num_empty_seats()

    def is_full(self):
        return self.get_num_empty_seats() == 0

    def is_empty(self):
        return self.get_num_taken_seats() == 0

    def has_player_cards(self, uid, cards):
        for card in cards:
            if not self.has_player_card(uid, card):
                return False

    def get_player(self, uid):
        for p in self.m_players:
            if int(p.get_uid()) == int(uid):
                return p

        return None

    def get_idOfAllPlayers(self):
        players = []
        for ID in self.m_players:
            players.append(ID.get_uid())
        return players

    def get_sidOfAllPlayers(self):
        players = []
        for sid in self.m_players:
            players.append(sid.get_sid())
        return players

    def get_list_thrower(self):
        if not self.is_started():
            return

        throwers = []

        if len(self.m_mainDeck) == 0:
            for player in self.m_players:
                if player.get_RoleValue() == 1:
                    throwers.append(player)

        else:
            for player in self.m_players:
                if player.get_RoleValue() == 1 or player.get_RoleValue() == 2:
                    throwers.append(player)

        return throwers

    ##########################
    ### key points of room ###
    ##########################

    def init_party(self):
        # gen main deck
        self.m_mainDeck = MainDeck(self.m_nCards)

        # remember trump card
        self.m_trump = self.m_mainDeck.get_trump()

        # reset discard pile
        self.m_discardPile = Deck()

        # reset battlefield
        self.m_battlefield = Battlefield()

    def reset_party(self):
        # init connections with players
        for i in range(len(self.m_players)):
            self.m_players[i].set_last(self.m_players[i - 1])
            self.m_players[i - 1].set_next(self.m_players[i])

        # put a timestamp
        self.m_startTurnTimeStamp = datetime.datetime.now()

        # clear the list of finished
        self.m_finished = []

        # reset list of throwers
        self.m_throwers = []

        # reset loser
        self.m_loser = None

        # reset started
        self.m_started = True

        # reset first beat
        self.m_isFirstBeat = True

        # reset max battlefield cards
        self.m_maxBattlefield = 5

        # reset actions list
        self.m_actions = []

        self.m_turn = None
        self.m_prevTurn = None
        self.m_attacker = None
        self.m_defender = None

    async def start(self):

        # check for enough players
        if len(self.m_players) <= 1:
            await self.m_startAlone(self.m_players[0].get_sid())
            self.m_isStarted = True

            return None

        for player in self.m_players:
            self.m_writeOffChips(player.get_uid(), (self.m_bet / len(self.m_players)) * -1)

        # set DATA
        self.set_ready()
        self.reset_party()
        self.init_party()

        await self.distribute_all()

        # set players roles
        self.choose_first_turn()

        first_turn = self.get_player(self.m_turn)

        first_turn.role = Role.main
        first_turn.status = status.beating

        first_turn.get_next().role = Role.firstThrower
        first_turn.get_next().status = status.throwing

        for player in self.m_players:
            player.roomID = self.m_rid
            if player.get_RoleEnum() != Role.main and player.get_RoleEnum() != Role.firstThrower:
                player.role = Role.thrower
                player.status = status.throwing

        await self.m_giveRoles_callback(self.m_players)

        self.m_throwers = self.get_list_thrower()

        await self.m_startCallback(self.m_rid, self.m_trump, self.m_bet, self.get_idOfAllPlayers())

    async def finish(self):

        for player in self.m_players:
            self.m_writeOffChips(player.get_uid(), self.m_bet / len(self.m_players))

        self.m_status = Status.FINISH

        # win multipliers
        win = [0.05 * i for i in range(1, len(self.m_finished))]

        # first finished - more win
        win = [1.0 - self.m_comission - sum(win[1:])] + win

        # if it's not a draw
        if len(win) > 1:
            win[-1] = 0

        # reset ready
        for player in self.m_players:
            player.reset_ready()

        self.m_started = False

        # {uid: chips, ...}
        winners = {}

        for i, v in enumerate(self.m_finished):
            winners[v] = win[i] * self.get_bet()

        await self.m_finishCallback(self.m_rid, winners)

        return win

    def fold_battlefield(self):
        self.m_discardPile.transfer_from(self.m_battlefield)

    def turn_is_expired(self):
        return datetime.datetime.now() >= self.m_startTurnTimeStamp + datetime.timedelta(seconds=31)

    async def end_turn(self):
        print("The end of turn")

        main_player = self.get_mainTurnPlayer()

        main_player.get_next().role = Role.main
        main_player.get_next().status = status.beating

        main_player.get_next().get_next().role = Role.firstThrower
        main_player.get_next().get_next().status = status.throwing

        for player in self.m_players:
            if player.get_RoleEnum() != Role.main and player.get_RoleEnum() != Role.firstThrower:
                player.role = Role.thrower
                player.status = status.throwing

        print("give roles")
        await self.m_giveRoles_callback(self.m_players)

        print("distrib all")
        await self.distribute_all()

        # are there any players who finished the game
        for player in self.m_players:
            if not player.is_playing():
                continue

            if player.get_num_cards() == 0:
                # player finished the game
                player.reset_ready()

        num_playing_players = self.get_num_playing_players()

        # the game is over?
        # the only one player
        if num_playing_players == 1:
            await self.finish()
            return

        # has no playing players
        elif num_playing_players == 0:
            # game ended in a draw
            await self.finish()
            return

        self.m_throwers = self.get_list_thrower()

    def join(self, uid, sid):

        if self.is_full() or self.get_player(uid):
            return False

        self.m_players.append(Player(uid, sid))

        return True

    async def leave(self, uid):
        player = self.get_player(uid)

        if not player:
            return

        if player.is_playing():
            # if room is empty or room has no uid
            if self.is_empty() or not player:
                # fold all player's cards
                player.fold_cards(self.m_discardPile)

            player.reset_ready()

        # remove player from room
        self.m_players.remove(player)

    #########################
    ### Playing functions ###
    #########################

    async def throw(self, sid, card, UId):
        print("\nBattlefield cards: \n" + str(self.m_battlefield))

        player = self.get_player(UId)

        if self.m_battlefield.get_num_not_beaten_cards() >= self.get_player(self.m_turn).get_num_cards():
            print("Num of battlefield cards is more than main player have")
            return

        if len(self.m_battlefield) == 0:
            print("battlefield is empty")
            if player.get_RoleEnum() == Role.firstThrower:
                self.m_battlefield.attack(card)
                await self.m_throwCallback(self.get_sidOfAllPlayers(), card, UId, sid)

        else:
            print("battlefield is not empty")
            if player.get_RoleEnum() == Role.thrower or player.get_RoleEnum() == Role.firstThrower:
                if self.can_throw_card(card):
                    self.m_battlefield.attack(card)
                    await self.m_throwCallback(self.get_sidOfAllPlayers(), card, UId, sid)

        player.m_cards.remove(card)
        if len(player.m_cards) == 0:

            prise = self.m_bet / 2
            self.m_bet - prise

            await self.m_writeOffChips(player.get_uid(), prise)
            self.m_playerWon(self, player)
            player.status = status.won

            not_finished = 0
            for pl in self.m_players:
                if pl.status != status.won: not_finished += 1
            if not_finished <= 1:
                await self.finish()

    def can_throw_card(self, card):
        nominals = []
        for pair in self.m_battlefield:
            for card in pair:
                nominals.append(card.get_nominal())

        if card.get_nominal() in nominals: return True

        return False

    async def battle(self, sid, uid, atackCard, atackingCard):
        player = self.get_player(uid)

        # check data
        if not player:
            return False
        if not player.is_playing():
            return False
        if not player.has_card(atackingCard):
            return False

        if player.get_RoleEnum == Role.main:
            self.m_battlefield.beat(atackCard, atackingCard, self.m_trump)

        if len(
            self.m_battlefield) != 0 and atackCard.get_nominal().value == atackingCard.get_nominal().value: await self.transfer()

        await self.m_beatCallback(sid, self.m_rid, uid, atackCard, atackingCard)

        player.m_cards.remove(atackingCard)

    async def transfer(self):
        main_player = self.get_mainTurnPlayer()

        main_player.get_next().role = Role.main
        main_player.get_next().status = status.beating

        main_player.get_next().get_next().role = Role.firstThrower
        main_player.get_next().get_next().status = status.throwing

        for player in self.m_players:
            if player.get_RoleEnum() != Role.main and player.get_RoleEnum() != Role.firstThrower:
                player.role = Role.thrower
                player.status = status.throwing

        await self.m_giveRoles_callback(self.m_players)

        self.m_throwers = self.get_list_thrower()

        return True

    ###################################

    async def cl_grab(self, uid):
        if self.get_player(uid).get_RoleEnum() == Role.main:
            print("The client: " + str(uid) + " is ready to grab")
            self.get_mainTurnPlayer().status = status.grabbing

            await self.m_clGrabCallback(self.m_rid)

    async def grab(self):
        player = self.get_mainTurnPlayer()

        # check data
        if not player:
            print("no player")
            return False
        if not player.is_playing():
            print("player is not playing")
            return False
        if len(self.m_battlefield) == 0:
            print("Battlefield is null")
            return False

        # collect cards
        cards = []
        for pair in self.m_battlefield:
            for card in pair:
                cards.append(card)

        print(cards)

        self.fold_battlefield()

        print("Card: \n " + str(cards) + "\n")

        player.take_cards(cards)

        print("Player cards: \n" + str(player.get_cards()) + "\n")

        await self.m_grabCallback(self.m_rid)

        await self.end_turn()

    async def cl_fold(self, uid):
        player = self.get_player(uid)

        # checking
        if not player:
            print("dont found player")
            return
        if not player.is_playing():
            print("player is not playing")
            return
        if player.get_RoleEnum == Role.main:
            print("Player: " + uid + ", role is: " + player.get_RoleEnum)
            return

        print("there is no cards in the battlefield: " + str(len(self.m_battlefield)))
        print("\nBattlefield:\n" + str(self.m_battlefield))

        if player.status != status.folding: player.status = status.folding

        await self.m_playerFoldCallback(self.m_rid, uid)

        for thrower in self.get_list_thrower():
            if thrower.status != status.folding:
                return

        await self.fold()

    async def fold(self):

        if self.m_gType == 1 and len(self.m_players) > 3:
            await self.transfer()
            return

        self.fold_battlefield()

        await self.m_foldCallback(self.m_rid)

        await self.end_turn()

    async def cl_pass(self, uid):
        if self.get_mainTurnPlayer().status != status.grabbing:
            return

        if self.get_player(uid).status == status.throwing:
            self.get_player(uid).status = status.passing
            await self.m_passCallback(self.m_rid, uid)

        for thrower in self.get_list_thrower():
            if thrower.status != status.passing:
                return

        print("grabbing")
        await self.grab()

    #################################

    async def distribute(self, uid):
        player = self.get_player(uid)

        if not player:
            print("User: " + uid + ", is not exist")
            return

        if not player.is_playing() or player.get_num_cards() >= 6:
            print("User: " + uid + " - \n")
            print(player.get_num_cards())
            print("Player cards: \n" + str(player.get_cards()))

            return []

        # bypass pop from empty list exception
        count_cards = min(6 - player.get_num_cards(), len(self.m_mainDeck))

        cards = []
        for i in range(count_cards):
            if (len(self.m_mainDeck) == 1):
                cards.append(self.m_mainDeck.pop())
                await self.m_trumpIsDone(self)
            elif (len(self.m_mainDeck) == 0):
                await self.m_deckIsEmpty(self)
                return
            else:
                cards.append(self.m_mainDeck.pop())

        player.take_cards(cards.copy())
        await self.m_distributionCallback(cards, player.get_sid(), uid, self.m_rid)

        return cards

    async def distribute_all(self):
        for p in self.m_players:
            if not p.is_playing():
                continue

            await self.distribute(p.get_uid())

    def choose_first_turn(self):

        # if there is a loser
        if self.m_loser and self.get_player(self.m_loser):
            self.m_turn = self.get_player(self.m_loser)

            return self.m_turn

        # get user with min trump
        minTrump = None

        for player in self.m_players:

            if not player.is_playing():
                continue

            minPlayersTrump = player.get_min_trump(self.m_trump)

            if not minPlayersTrump:
                continue

            if not minTrump:
                minTrump = {"uid": player.get_uid(), "card": minPlayersTrump}

            else:
                if minPlayersTrump.get_nominal().value < minTrump["card"].get_nominal().value:
                    minTrump = {"uid": player.get_uid(), "card": minPlayersTrump}

        # return ID of first player 
        if (minTrump == None):
            self.m_turn = self.m_players[0].get_uid()
        else:
            self.m_turn = minTrump["uid"]

        return self.m_turn

    async def whatsup(self):
        if not self.turn_is_expired():
            return

        """
        if self.m_turn == self.m_attacker:
            await self.fold()
            await self.m_foldCallback(self.m_rid, self.m_turn)
        elif self.m_turn == self.m_defender:
            await self.grab()
            await self.m_grabCallback(self.m_rid, self.m_turn)
        else:
            await self.pass_()
            await self.m_passCallback(self.m_rid, self.m_turn)
        """
