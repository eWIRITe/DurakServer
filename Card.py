from Enums import Nominal, Suit

class Card:
    s_humanSuits = ["♥", "♦", "♣", "♠"]
    s_humanNominals = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "В", "Д", "К", "Т"]

    def __init__(self, suit, nominal):
        if type(suit) != Suit:
            raise Exception("suit type", "suit is not Suit enum")

        if type(nominal) != Nominal:
            raise Exception("index type", "index is not Index enum")

        self.m_suit = suit
        self.m_nominal = nominal
        self.m_byte = self.m_suit.value + self.m_nominal.value

    @staticmethod
    def from_byte(byte):
        suit = byte // Nominal.COUNT
        nominal = byte % Nominal.COUNT
        return Card(suit, nominal)

    def get_suit(self):
        return self.m_suit

    def get_nominal(self):
        return self.m_nominal

    def get_byte(self):
        return chr(self.m_byte)

    """
        Return True if it can
        If attacking card can beat self card then attacking card cant beat self card
        Use it if you want to check other card
    """
    def can_card_beat(self, attacking, trump):
        if attacking.get_suit() == trump.get_suit():
            if self.get_suit() == trump.get_suit():
                return attacking.get_nominal() > self.get_nominal()

            return True

        return attacking.get_suit() == self.get_suit() and \
            attacking.get_nominal() > self.get_nominal()

    def __eq__(self, other):
        return other and self.get_suit() == other.get_suit() and \
            self.get_nominal() == other.get_nominal()

    def __str__(self):
        nominalIndex = self.get_nominal().value
        suitIndex = self.get_suit().value // Nominal.COUNT.value
        return "{0} {1}".format(Card.s_humanNominals[nominalIndex], Card.s_humanSuits[suitIndex])

    def __repr__(self):
        #return str(self) + " ({0})".format(hex(id(self)))
        return str(self)
