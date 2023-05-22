from Room import Room
from Card import Card
from Enums import Nominal, Suit

durak_rooms = {}

def finish(win):
    print("emit finish", win)

def distrib(cards):
    print("emit distrib", cards["cards"])

def transfer(card):
    print("emit transfer", card)

def start(startJSON):
    print("emit start", startJSON)

room = Room("123", start, distrib, transfer, finish, {"isprivate" : False, "key" : "123", "gtype" : 2, "ncards" : 36, "bet" : 100, "mxplayers" : 2})

# процесс тестирования игрового процесса
room.join(1, "g543g542g")
room.join(2, "234t2g534")
#room.join(3, "234t2g534")
#room.join(4, "234t2g534")
#room.join(5, "234t2g534")
#room.join(6, "234t2g534")

# проверка, если игра идет, а игроков осталось 1 - вызов room.finish()
#room.leave(1)

# ожидание подтверждения всех игроков
room.ready(1)
room.ready(2)
#room.ready(3)
#room.ready(4)
#room.ready(5)
#room.ready(6)

synonims = { 
    "атака" : ["атака", "напасть", "атакую", "атакует", "атаковать"], 
    "оборона" : ["оборона", "отбить", "обороняю", "обороняет", "оборонять"], 
    "перевод": ["перевод", "перевести", "перевожу", "переводит", "переводить"], 
    "сброс" : ["сброс", "сбросить", "сбрасываю", "сбрасывает", "сбрасывать"], 
    "показать" : ["показать", "карты", "показать карты"], 
    "чей ход" : ["чей ход", "кто ходит", "кто", "чей", "ход"], 
    "поле" : ["поле", "что на поле", "что бить", "что"], 
    "взять" : ["взять", "забрать", "возьму", "заберу", "беру", "мое", "забрал", "взял"], 
    "пропуск" : ["пропуск", "пропустить", "пас", "пасс", "конец"], 
    "колода" : ["колода", "сколько", "сколько осталось", "осталось", "козырь", "что козырь", "какой козырь"]
}

def input_cards(info):
    cardsStr = input(f"{info} >")

    cardsStr = cardsStr.lower()
    cardsStr = cardsStr.replace(", ", ",")
    cardsStr = cardsStr.split(',')

    cards = []

    for cardStr in cardsStr:
        nominal, suit = tuple(cardStr.split())
        
        cards.append(Card(Suit(Card.s_humanSuits.index(suit) * Nominal.COUNT.value), Nominal(Card.s_humanNominals.index(nominal[0].upper() + nominal[1:]))))

    return cards

while True:
    cmd = input(">")
    cmd = cmd.lower()

    if cmd in synonims["атака"]:
        #uid = input("игрока uid#")
        #uid = uid.lower()
        #uid = uid.split()[0]
        #uid = int(uid)

        attackingCards = input_cards("карты которые подкидываем (через запятую)")

        if room.battle(room.m_turn, [], attackingCards):
            print("Успех")
            print("Ход {0}-го".format(room.m_turn))
            # emit("cl_battle", {"uid":uid, "attacked":attacked, "attacking":attacking})
        else:
            print("Провал")

    elif cmd in synonims["оборона"]:
    #    uid = input("игрок uid#")
    #    uid = uid.lower()
    #    uid = uid.split()[0]
    #    uid = int(uid)

        attackedCards = input_cards("карты от которых отбиваемся (через запятую)")
        attackingCards = input_cards("карты которыми отбиваемся (через запятую)")

        if room.battle(room.m_turn, attackedCards, attackingCards):
            print("Успех")
            print("Ход {0}-го".format(room.m_turn))
            # emit("cl_battle", {"uid":uid, "attacked":attacked, "attacking":attacking})
        else:
            print("Провал")

    elif cmd in synonims["перевод"]:
        #uid = input("игрока uid#")
        #uid = uid.lower()
        #uid = uid.split()[0]
        #uid = int(uid)

        card = input_cards("карты от которых отбиваемся (через запятую)")[0]

        if room.transfer(room.m_turn, card):
            print("Успех")
            print("Ход {0}-го".format(room.m_turn))
            # emit transfer
        else:
            print("Провал")

    elif cmd in synonims["сброс"]:
        #uid = input("игрока uid#")
        #uid = uid.lower()
        #uid = uid.split()[0]
        #uid = int(uid)

        room.fold(room.m_turn)
        print("Ход {0}-го".format(room.m_turn))
        # emit fold

    elif cmd in synonims["показать"]:
        #uid = input("игрока uid#")
        #uid = uid.lower()
        #uid = uid.split()[0]
        #uid = int(uid)

        for player in room.m_players:
            print("игрок {0}:".format(player.get_uid()))
            print("\t{0}".format(player.m_cards))

    elif cmd in synonims["чей ход"]:
        print("uid#{0}".format(room.m_turn))

    elif cmd in synonims["поле"]:
        print(room.m_battlefield)

    elif cmd in synonims["взять"]:
        #uid = input("игрока uid#")
        #uid = uid.lower()
        #uid = uid.split()[0]
        #uid = int(uid)

        if room.grab(room.m_turn):
            print("Успех")
            print("Ход {0}-го".format(room.m_turn))
        else:
            print("Провал")

    elif cmd in synonims["пропуск"]:
        #uid = input("игрока uid#")
        #uid = uid.lower()
        #uid = uid.split()[0]
        #uid = int(uid)

        if room.pass_(room.m_turn):
            print("Успех")
            print("Ход {0}-го".format(room.m_turn))
        else:
            print("Провал")

    elif cmd in synonims["колода"]:
        print("В колоде осталось {0} карт вместе с козырем {1}".format(len(room.m_mainDeck), room.m_trump))
