from Deck import Deck

class Player:
    def __init__(self, uid, sid, next=None, prev=None):
        self.m_uid = uid
        self.m_sid = sid
        self.m_ready = False
        self.m_cards = Deck()

        if not next or not prev:
            next = prev = None

        self.m_next, self.m_prev = next, prev

    def set_next(self, nextPlayer):
        if self.m_next == nextPlayer:
            return

        self.m_next = nextPlayer
        self.m_next.set_prev(self)

    def set_prev(self, prevPlayer):
        if self.m_prev == prevPlayer:
            return

        self.m_prev = prevPlayer
        self.m_prev.set_next(self)

    def next(self):
        if self.m_next.is_playing():
            return self.m_next
        else:
            return self.m_next.next()

    def prev(self):
        if self.m_prev.is_playing():
            return self.m_prev
        else:
            return self.m_prev.prev()

    def is_playing(self):
        return self.m_ready

    def is_ready(self):
        return self.m_ready

    def ready(self):
        self.m_ready = True

    def reset_ready(self):
        if not self.m_ready:
            return

        self.m_ready = False

        self.m_next.set_prev(self.m_prev)
        self.m_prev.set_next(self.m_next)
        self.m_prev = None
        self.m_next = None

    def get_uid(self):
        return self.m_uid

    def get_sid(self):
        return self.m_sid


    """
        Returns number of cards
    """
    def get_num_cards(self):
        return len(self.m_cards)

    """
        Returns True if player has card
    """
    def has_card(self, card):
        return card in self.m_cards

    """
        Returns True if player has all cards
    """
    def has_cards(self, cards):
        for card in cards:
            if not self.has_card(card):
                return False
        
        return True

    def fold_cards(self, discardPile):
        self.m_cards.transfer_to(discardPile)

    def take_cards(self, cards):
        self.m_cards.transfer_from(cards)

    def get_min_trump(self, trump):
        minTrump = None

        for card in self.m_cards:
            if card.get_suit() != trump.get_suit():
                continue
            
            if minTrump == None or card.get_nominal().value < minTrump.get_nominal().value:
                minTrump = card

        return minTrump
