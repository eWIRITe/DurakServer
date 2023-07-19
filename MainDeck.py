from Enums import Nominal, Suit
from Deck import Deck
from secrets import SystemRandom
from Card import Card


class MainDeck(Deck):
    s_secretsRandom = SystemRandom()

    def __init__(self, nCards):
        super().__init__()

        table_min_nominal = {
            24: Nominal.NINE,
            36: Nominal.SIX,
            52: Nominal.TWO
        }

        min_nominal = table_min_nominal[nCards]

        for nominal in Nominal:
            if nominal.value < min_nominal.value:
                continue

            if nominal == Nominal.COUNT:
                break

            for suit in Suit:
                self.append(Card(suit, nominal))

        MainDeck.s_secretsRandom.shuffle(self)

    def get_trump(self):
        return self[0]
