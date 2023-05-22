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
            if len(pair) == 1:
                count += 1

        return count

    def can_beat(self, attackedCard, attackingCard, trump):
        # if attackingCard can beat attackedCard
        return attackedCard.get_suit().value == attackingCard.get_suit().value and \
                attackedCard.get_nominal().value < attackingCard.get_nominal().value or \
                attackedCard.get_suit().value != trump.get_suit().value and \
                attackingCard.get_suit().value == trump.get_suit().value

    def beat(self, attackedCard, attackingCard):
        slot = self.index([attackedCard])
        self[slot] = [attackedCard, attackingCard]

        return True

    def attack(self, card):
        self.append([card])
