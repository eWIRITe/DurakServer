from enum import Enum

class Suit(Enum):
    HEART = 0
    TILE = 1
    CLOVERS = 2
    PIKES = 3

class Nominal(Enum):
    TWO = 0
    THREE = 1
    FOUR = 2
    FIVE = 3
    SIX = 4
    SEVEN = 5
    EIGHT = 6
    NINE = 7
    TEN = 8
    JACK = 9
    QUEEN = 10
    KING = 11
    ACE = 12
    COUNT = 13

Status = Enum("Status", ["START", "ATTACK", "DEFENSE", "THROWIN", "FINISH"])
