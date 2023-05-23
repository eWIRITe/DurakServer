from Enums import Status
from Player import Player
from MainDeck import MainDeck
from Deck import Deck
from Battlefield import Battlefield

import datetime

class Room:
    def __init__(self, rid, json, comission=0.1):
        self.m_rid = rid
        self.m_isPrivate = json["isPrivate"]
        self.m_key = json["key"]
        self.m_gType = json["type"]
        self.m_nCards = json["cards"]
        self.m_bet = json["bet"]
        self.m_maxPlayers = json["maxPlayers"]
        self.m_roomOwner = json["roomOwner"]

        # service comission
        self.m_comission = comission

        # status of turns
        self.m_status = Status.START

        # list of players who played cards
        self.m_actions = []

        # seats at the table
        self.m_players = []

        # list of throwers
        self.m_throwers = []

        # trump card at the bottom of the game deck
        self.m_trump = None

        # sorted list of players
        # first element is left the game early, last - loser
        self.m_finished = []

        # grabber's uid in current turn
        self.m_grab = None

        # player who start the circle
        self.m_opensTurn = None

        # player whose turn
        self.m_turn = None

        # player attacker
        self.m_attacker = None

        # player defender
        self.m_defender = None

        # prev player turn
        self.m_prevTurn = None

        # player who last finished in the prev game party
        self.m_loser = None

        # common bank
        self.m_bank = 0

        # main deck
        self.m_mainDeck = None

        # cards played
        self.m_discardPile = None

        # battlefield
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
        self.m_turnCallback = None
        self.m_foldCallback = None
        self.m_passCallback = None
        self.m_startCallback = None
        self.m_finishCallback = None

    def set_distribution_callback(self, callback):
        self.m_distributionCallback = callback

    def set_grab_callback(self, callback):
        self.m_grabCallback = callback

    def set_turn_callback(self, callback):
        self.m_turnCallback = callback

    def set_fold_callback(self, callback):
        self.m_foldCallback = callback

    def set_pass_callback(self, callback):
        self.m_passCallback = callback

    def set_start_callback(self, callback):
        self.m_startCallback = callback

    def set_finish_callback(self, callback):
        self.m_finishCallback = callback

    def set_ready(self):
        self.m_isStarted = True


    def is_free(self):
        print("isFreeCheck")
        if(self.m_isStarted == False):
            print("not started")
            print(str(len(self.m_players)))
            print(str(self.m_maxPlayers))
            if self.m_maxPlayers > len(self.m_players):
                print("not full")
                return True
        return False

    def get_roomOwner(self):
        return self.m_roomOwner

    def get_rid(self):
        return self.m_rid

    def get_key(self):
        return self.m_key

    def get_bet(self):
        return self.m_bet

    def get_ncards(self):
        return self.m_nCards

    def get_gtype(self):
        return self.m_gType

    def get_maxplayers(self):
        return self.m_maxPlayers

    def is_private(self):
        return self.m_isPrivate

    def is_started(self):
        if(self.started):
            return True
        else:
            return False

    def fold_battlefield(self):
        self.m_discardPile.transfer_from(self.m_battlefield)

    def turn_is_expired(self):
        return datetime.datetime.now() >= self.m_startTurnTimeStamp + datetime.timedelta(seconds = 31)

    def get_num_playing_players(self):
        count = 0

        for player in self.m_players:
            if player.is_playing():
                count += 1

        return count

    def end_turn(self):
        # are there any players who finished the game
        for player in self.m_players:
            if not player.is_playing():
                continue

            if player.get_num_cards() == 0:
                # player finished the game
                player.reset_ready()

        numPlayingPlayers = self.get_num_playing_players()

        # the game is over?
        # the only one player
        if numPlayingPlayers == 1:
            # normal game over
            for player in self.m_players:
                if player.is_playing():
                    
                    self.add_finished(player.get_uid())
                    break

            self.finish()
            return

        # has no playing players
        elif numPlayingPlayers == 0:
            # game ended in a draw
            self.finish()
            return


        nextTurn = self.get_player(self.m_opensTurn).next()

        # if there is a card taker
        if self.m_grab:
            # collect cards
            cards = []
            for pair in self.m_battlefield:
                cards += pair

            # take all cards
            self.get_player(self.m_grab).take_cards(cards)
            
            # reset grabber's uid
            self.m_grab = None

            # skip grabber's turn
            nextTurn = nextTurn.next()

        else:
            self.m_firstTurn = False

            self.m_maxBattlefield = 6

        self.distrib(self.m_attacker)

        # distrib the cards
        for uid in self.m_actions:
            self.distrib(uid)

        self.distrib(self.m_defender)

        self.m_actions = []

        self.m_opensTurn = self.m_turn = self.m_attacker = nextTurn.get_uid()
        self.m_defender = nextTurn.next().get_uid()
        self.m_prevTurn = None

        self.m_turnCallback(self.m_rid, self.m_turn)

        self.m_status = Status.ATTACK

        # reset bf
        self.fold_battlefield()

        self.m_throwers = self.get_list_thrower()

    def has_player_card(self, uid, card):
        player = self.get_player(uid)
        if not player:
            return

        return player.has_card(card)

    def has_player_cards(self, uid, cards):
        for card in cards:
            if not self.has_player_card(uid, card):
                return False

    def add_finished(self, uid):
        player = self.get_player(uid)

        if not player:
            print("Warning: There is an attempt to add finished as a non-existent player")
            return

        self.m_finished.append(uid)

    def add_loser(self, uid):
        player = self.get_player(uid)

        if not player:
            print("Warning: There is an attempt to add loser as a non-existent player")
            return

        player.reset_ready()
        self.m_finished.append(uid)

    def can_throw_cards(self, cards):
        nominals = []
        for pair in self.m_battlefield:
            for card in pair:
                nominals.append(card.get_nominal())

        for card in cards:
            if not card.get_nominal() in nominals:
                return False

        return True

    """
        Returns the number of seats which is free
    """
    def get_num_empty_seats(self):
        return self.m_maxPlayers - len(self.m_players)

    """
        Returns the number of seats which is taken
    """
    def get_num_taken_seats(self):
        return self.m_maxPlayers - self.get_num_empty_seats()

    """
        Returns True if room is full
        or False
    """
    def is_full(self):
        return self.get_num_empty_seats() == 0

    """
        Returns True if room is empty
        or False
    """
    def is_empty(self):
        return self.get_num_taken_seats() == 0

    """
        Returns Player with uid if it there
        or None otherwise
    """
    def get_player(self, uid):
        for p in self.m_players:
            if p and p.get_uid() == uid:
                return p

        return None

    def get_players(self):
        players = []
        for ID in self.m_players:
            players.append(ID.get_uid())
        return players

    """
        Returns the id of a free place
    """
    def get_first_free_place(self):
        if self.is_full():
            return

        return self.m_players.index(None)

    """
        Returns list of thrower
        Call this func after set m_turn, m_attacker
    """
    def get_list_thrower(self):
        throwers = []
        player = self.get_player(self.m_attacker)

        while True:
            if player.get_uid() in throwers:
                break
        
            if (self.m_gType != 1) and len(throwers) == 3:
                break

            throwers.append(player.get_uid())
            player = player.next()

        return throwers[2:]






    def battle(self, uid, attacked, attacking):
        player = self.get_player(uid)

        if not player:
            return False

        # if player is not playing
        if not player.is_playing():
            return False
    
        # if player is not active
        if not self.m_turn == uid:
            return False

        # if player has no at least one card from attacking
        if not player.has_cards(attacking):
            return False

        #if player is attacker
        if self.m_status.value == Status.ATTACK.value:
            defender = self.get_player(self.m_defender)

            # if number of cards in attacking list > number of cards in defender's hands
            if len(attacking) > defender.get_num_cards():
                return False

            # if number of attacking cards + number of cards in battlefield > max number of cards at the current turn
            if len(attacking) + len(self.m_battlefield) > self.m_maxBattlefield:
                return False

            # if the nominal of the attacking cards is not identical
            ideal = attacking[0].get_nominal()

            for card in attacking:
                if card.get_nominal().value != ideal.value:
                    return False

            # attack/throw in
            for card in attacking:
                self.m_battlefield.attack(card)

                player.m_cards.remove(card)

            # if player has no cards and main deck is empty
            if len(self.m_mainDeck) == 0 and player.get_num_cards() == 0:
                self.add_finished(uid)

            # next step
            self.m_prevTurn, self.m_turn = self.m_turn, self.m_defender

            self.m_turnCallback(self.m_rid, self.m_turn)

            self.m_status = Status.DEFENSE

        # if player is defender
        elif self.m_status.value == Status.DEFENSE.value:
            if len(attacked) == 0:
                return False

            # if battlefield is empty
            if len(self.m_battlefield) == 0:
                return False

            # if battlefield has no at least one card from attacked
            if not self.m_battlefield.has_cards(attacked) or len(attacked) != self.m_battlefield.get_num_not_beaten_cards():
                return False

            # if cant beat at least one card
            for i in range(len(attacked)):
                if not self.m_battlefield.can_beat(attacked[i], attacking[i], self.m_trump):
                    return False

            # beat
            for i in range(len(attacked)):
                if not self.m_battlefield.beat(attacked[i], attacking[i]):
                    return False

                player.m_cards.remove(attacking[i])

            # next step
            self.m_turn = self.m_prevTurn

            self.m_turnCallback(self.m_rid, self.m_turn)

            self.m_status = Status.THROWIN

            # if battlefield has max number of cards at the current turn or cards is run out of player's cards
            if len(self.m_battlefield) == self.m_maxBattlefield or player.get_num_cards() == 0:
                # if player has no cards and main deck is empty
                if len(self.m_mainDeck) == 0 and player.get_num_cards() == 0:
                    self.add_finished(uid)

                # turn's end
                self.end_turn()

        elif self.m_status.value == Status.THROWIN.value:
            defender = self.get_player(self.m_defender)

            # if number of cards in attacking list > number of cards in defender's hands
            if len(attacking) > defender.get_num_cards():
                return False

            # if number of attacking cards + number of cards in battlefield > max number of cards at the current turn
            if len(attacking) + len(self.m_battlefield) > self.m_maxBattlefield:
                return False

            # if attacking card cant throw in
            if not self.can_throw_cards(attacking):
                return False

            # attack/throw in
            for card in attacking:
                self.m_battlefield.attack(card)

                player.m_cards.remove(card)

            self.m_actions.append(uid)

            # if player has no cards and main deck is empty
            if len(self.m_mainDeck) == 0 and player.get_num_cards() == 0:
                self.add_finished(uid)

            # next step
            if self.m_grab:
                if len(self.m_throwers) == 0:
                    self.end_turn()
                    return True
                else:
                    self.m_prevTurn, self.m_turn = self.m_turn, self.m_throwers.pop(0)
            else:
                self.m_prevTurn, self.m_turn = self.m_turn, self.m_defender

            self.m_turnCallback(self.m_rid, self.m_turn)

            self.m_status = Status.DEFENSE

        else:
            return False

        return True

    def transfer(self, uid, card):
        # check game type
        if self.m_gType != 2:
            return False

        if not self.m_turn == uid:
            return False

        player = self.get_player(uid)

        if not player:
            return False

        # if player is not playing
        if not player.is_playing():
            return False

        if self.m_firstTurn:
            return False

        # if player is not active
        if not self.m_turn == uid:
            return False

        # if player is not defender
        if uid != self.m_defender:
            return False

        # if player has no this card
        if not self.has_player_card(uid, card):
            return False

        # if the next player runs out of cards
        nextPlayer = self.get_player(uid).next()

        if nextPlayer.get_num_cards() < len(self.m_battlefield) + 1:
            return False

        # add card to the battlefield
        player.m_cards.remove(card)
        self.m_battlefield.attack(card)

        # if player has no cards and main deck is empty
        if len(self.m_mainDeck) == 0 and player.get_num_cards() == 0:
            self.add_finished(uid)

        # move circle +1
        self.m_attacker, self.m_defender = self.m_defender, player.next().get_uid()
        self.m_prevTurn, self.m_turn = self.m_turn, self.m_defender
        self.m_opensTurn = self.m_attacker

        self.m_turnCallback(self.m_rid, self.m_turn)

        self.m_throwers = self.get_list_thrower()

        self.m_actions.append(uid)

        return True

    def grab(self, uid):
        if not self.m_turn == uid:
            return

        player = self.get_player(uid)

        if not player:
            return

        # if player is not playing
        if not player.is_playing():
            return

        # if player is not a defender
        if uid != self.m_defender:
            return

        self.m_grab = uid

        if not self.m_throwers:
            self.end_turn()
            return True
        else:
            # then next turn is next player after thrower
            self.m_prevTurn, self.m_turn = self.m_turn, self.m_throwers.pop(0)

            # если количество карт на поле == maxBattlefield
            if len(self.m_battlefield) == self.m_maxBattlefield:
                self.end_turn()
                return True

        self.m_turnCallback(self.m_rid, self.m_turn)

        self.m_status = Status.THROWIN

        return True

    def pass_(self, uid):
        if not self.m_turn == uid:
            return False

        player = self.get_player(uid)

        if not player:
            return False

        # if player is not playing
        if not player.is_playing():
            return False

        # if this turn is first in current circle
        if len(self.m_battlefield) == 0:
            return False

        # if uid is defender
        if uid == self.m_defender:
            return False

        if len(self.m_throwers) == 0:
            self.end_turn()
            return True

        self.m_status = Status.THROWIN
        self.m_prevTurn, self.m_turn = self.m_turn, self.m_throwers.pop(0)
        
        self.m_turnCallback(self.m_rid, self.m_turn)

        return True

    def fold(self, uid):
        player = self.get_player(uid)

        if not player:
            return

        if not self.m_turn == uid:
            return

        if not player.is_playing():
            return

        if len(self.m_battlefield):
            return

        player.fold_cards(self.m_discardPile)

        if self.get_num_playing_players() == 1:
            self.add_finished()

        self.m_opensTurn = self.m_turn = self.m_attacker = player.next().get_uid()
        self.m_defender = player.next().next().get_uid()
        self.m_prevTurn = None

        self.m_turnCallback(self.m_rid, self.m_turn)

        player.reset_ready()

        numPlayingPlayers = self.get_num_playing_players()

        # the game is over?
        # the only one player
        if numPlayingPlayers == 1:
            for player in self.m_players:
                if player.is_playing():
                    self.add_finished(player.get_uid())
                    break

            self.finish()
        # has no playing players
        elif numPlayingPlayers == 0:
            self.finish()

        return True

    """
        Returns list of cards which needs to be takes player
    """
    def distrib(self, uid):
        cards = []
        player = self.get_player(uid)
        
        if not player:
            return

        if not player.is_playing() or player.get_num_cards() == 6:
            return []

        # bypass pop from empty list exception
        countCards = min(6 - player.get_num_cards(), len(self.m_mainDeck))

        cards = [self.m_mainDeck.pop().get_byte() for _ in range(0, countCards)]

        player.take_cards(cards.copy())
        self.m_distributionCallback(cards, player.get_sid())

        return cards

    """
        Returns list of dicts [{sid:, cards:}]
    """
    def all_distrib(self):
        cards = []

        for p in self.m_players:
            if not p.is_playing():
                continue

            cards.append({"sid": p.get_sid(), "cards": self.distrib(p.get_uid())})

        return cards

    """
        Returns True if uid successfuly joined
        or False if room is full or uid already in room
    """
    def join(self, uid, sid):
        # if room is full or uid already in room
        if self.is_full() or self.get_player(uid):
            return False

        self.m_players.append(Player(uid, sid))

        return True

    """
        Returns True if uid successfuly removed
        or False if room is empty or room has no uid
    """
    def leave(self, uid):
        player = self.get_player(uid)

        if not player:
            return

        if player.is_playing():
            # if room is empty or room has no uid
            if self.is_empty() or not player:
                return False

            # fold all player's cards
            player.fold_cards(self.m_discardPile)

            player.reset_ready()

        # remove player from room
        self.m_players.remove(player)

        return True

    def choose_first_turn(self):
        # if there is loser
        if self.m_loser and self.get_player(self.m_loser):
            # select first player to start circle
            self.m_opensTurn = self.get_player(self.m_loser).prev().get_uid()

            # set player turn
            self.m_turn = self.m_opensTurn

            return

        # else if there is no loser
        #else:
        # find min trump card in hands of player
        minTrump = None
        for player in self.m_players:
            if not player.is_playing():
                continue

            # min card in player
            minPlayersTrump = player.get_min_trump(self.m_trump)

            if not minPlayersTrump:
                continue

            if not minTrump or minPlayersTrump.get_nominal().value < minTrump["card"].get_nominal().value:
                minTrump = {"uid": player.get_uid(), "card": minPlayersTrump}

        # select first player to start circle
        self.m_opensTurn = minTrump["uid"]

        # set player turn
        self.m_turn = self.m_opensTurn

        return self.m_opensTurn

    def init_party(self):
        # gen main deck
        self.m_mainDeck = MainDeck(self.m_nCards)

        # remember trump card
        self.m_trump = self.m_mainDeck.get_trump()

        # reset discard pile
        self.m_discardPile = Deck()

        # reset battlefield
        self.m_battlefield = Battlefield()

        return self.m_trump

    def reset_party(self):
        # init connections with players
        for i in range(len(self.m_players)):
            self.m_players[i].set_prev(self.m_players[i - 1])
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

    def start(self):
        trump = self.init_party()

        self.all_distrib()

        firstTurn = self.choose_first_turn()

        self.reset_party()

        self.m_turn = self.m_attacker = firstTurn
        self.m_defender = self.get_player(firstTurn).next().get_uid()

        self.m_turnCallback(self.m_rid, self.m_turn)

        self.m_throwers = self.get_list_thrower()

        self.m_status = Status.ATTACK

        self.m_startCallback(self.m_rid, firstTurn, trump)

    def finish(self):
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

        self.m_finishCallback(self.m_rid, winners)

        return win

    def whatsup(self):
        if not self.turn_is_expired():
            return

        if self.m_turn == self.m_attacker:
            self.fold()
            self.m_foldCallback(self.m_rid, self.m_turn)
        elif self.m_turn == self.m_defender:
            self.grab()
            self.m_grabCallback(self.m_rid, self.m_turn)
        else:
            self.pass_()
            self.m_passCallback(self.m_rid, self.m_turn)
