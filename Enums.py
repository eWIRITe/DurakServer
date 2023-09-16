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


class Role(Enum):
    notReady = -1
    main = 0
    firstThrower = 1
    thrower = 2


class status(Enum):
    loosed = -2
    won = -1
    waiting = 0
    throwing = 1
    beating = 2
    folding = 3
    grabbing = 4
    passing = 5


class LastMove(Enum):
    folding = 0
    grabbing = 1


class GameType(Enum):
    usual = 0,
    ThrowIn = 1,
    Transferable = 2
