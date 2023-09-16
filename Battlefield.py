class Battlefield(list):
    def has_card(self, card):
        return [card] in self

    def has_cards(self, cards):
        for card in cards:
            if not self.has_card(card):
                return False

        return True

    def get_num_not_beaten_cards(self):
        count = 0
        for pair in self:
            if len(pair) > 1:
                count += 1

        return count

    def beat(self, attacked_card, attacking_card, trump):
        slot = self.index([attacked_card])
        print("attacking card slot: " + str(slot))
        if can_beat(attacked_card, attacking_card, trump):
            self[slot] = [attacked_card, attacking_card]
            print("Slot: " + str(self[slot]))
        else:
            print("cannon beat")

    def attack(self, card):
        self.append([card])


def can_beat(attacked_card, attacking_card, trump):
    if attacked_card.get_suit() == trump.get_suit() and attacking_card.get_suit() != trump.get_suit():
        return False

    if attacking_card.get_suit() == trump.get_suit() and attacked_card.get_suit() != trump.get_suit():
        return True

    if attacked_card.get_suit() == attacking_card.get_suit():
        return attacked_card.get_nominal().value < attacking_card.get_nominal().value
    else:
        return False
