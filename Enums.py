from enum import Enum

Suit = Enum("Suit", [("HEART", 0x00), ("TILE", 0x0D), ("CLOVERS", 0x1A), ("PIKES", 0x27)])

Nominal = Enum("Index", [
    ("TWO", 0x00), ("THREE", 0x01), ("FOUR", 0x02),
    ("FIVE", 0x03), ("SIX", 0x04), ("SEVEN", 0x05),
    ("EIGHT", 0x06), ("NINE", 0x07), ("TEN", 0x08),
    ("JACK", 0x09), ("QUEEN", 0x0A), ("KING", 0x0B),
    ("ACE", 0x0C), ("COUNT", 0x0D)
])

Status = Enum("Status", ["START", "ATTACK", "DEFENSE", "THROWIN", "FINISH"])
