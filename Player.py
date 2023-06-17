from Deck import Deck
from Card import Card
from Enums import Role, status


class Player:
    def __init__(self, uid, sid, role=Role.notReady, status = status.waiting, nextPlayer=None, lastPlayer=None):
        self.m_uid = uid
        self.m_sid = sid
        self.m_ready = False
        self.m_cards = Deck()
        self.role = role
        self.status = status

        self.nextPlayer, self.lastPlayer = nextPlayer, lastPlayer

    ##########################
    ### next//last players ###
    ##########################

    def set_next(self, nextPlayer):
        self.nextPlayer = nextPlayer

    def set_last(self, lastPlayer):
        self.lastPlayer = lastPlayer

    def get_next(self):
        return self.nextPlayer

    def get_last(self):
        return self.lastPlayer

    #####################
    ### get functions ###
    #####################

    def get_uid(self):
        return self.m_uid

    def get_sid(self):
        return self.m_sid

    def get_RoleValue(self):
        return self.role.value

    def get_RoleEnum(self):
        return self.role

    def get_StatusEnum(self):
        return self.status

    def is_playing(self):
        return self.m_ready

    def is_ready(self):
        return self.m_ready

    def get_num_cards(self):
        return len(self.m_cards)

    def has_card(self, card):
        print(card)
        print(self.m_cards)

        return card in self.m_cards

    def has_cards(self, cards):
        for card in cards:
            if not self.has_card(card):
                return False

        return True

    def get_min_trump(self, trump):
        minTrump = None
        print("Trump: " + str(trump))

        for card in self.m_cards:
            if card.get_suit() == trump.get_suit():
                if minTrump is None:
                    minTrump = card
                else:
                    if card.get_nominal().value < minTrump.get_nominal().value:
                        minTrump = card

        return minTrump

    #####################
    ### set functions ###
    #####################

    def ready(self):
        self.m_ready = True

    def reset_ready(self):
        if not self.m_ready:
            return

        self.m_ready = False

        self.nextPlayer.set_last(self.lastPlayer)
        self.lastPlayer.set_next(self.nextPlayer)
        self.lastPlayer = None
        self.nextPlayer = None

    #########################
    ### playing functions ###
    #########################

    def fold_cards(self, discardPile):
        self.m_cards.transfer_to(discardPile)

    def take_cards(self, cards):
        print("\nUser: " + self.m_uid + ", got cards: \n" + str(cards))
        self.m_cards.transfer_from(cards)
        print("\nNow this user have: \n" + str(self.m_cards))

    def get_cards(self):
        return self.m_cards