from Enums import Nominal, Suit
from Deck import Deck
from secrets import SystemRandom
from Card import Card

class MainDeck(Deck):
    s_secretsRandom = SystemRandom()

    def __init__(self, nCards):
        super().__init__()

        tableMinNominal = {
            24 : Nominal.NINE, 
            36 : Nominal.SIX, 
            52 : Nominal.TWO
        }

        minNominal = tableMinNominal[nCards]
        
        for nominal in Nominal:
            if nominal.value < minNominal.value:
                continue

            if nominal == Nominal.COUNT:
                break

            for suit in Suit:
                self.append(Card(suit, nominal))

        MainDeck.s_secretsRandom.shuffle(self)

    def get_trump(self):
        return self[0]
