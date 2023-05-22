class Deck(list):
    def is_empty(self):
        return len(self)

    def transfer_to(self, deck):
        while self:
            deck.append(self.pop())

    def transfer_from(self, deck):
        while deck:
            self.append(deck.pop())
