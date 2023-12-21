from modules.stack import Stack
from modules.card import Card
import random

class Deck(Stack):
    def __init__(self):
        Stack.__init__(self, [], type="Deck")
        self.max = 13
        self.suits = ["Spades", "Hearts", "Diamonds", "Clubs"]
        for s in self.suits:
            for n in range(self.max):
                self.cards.append(Card(s, n + 1))
        random.seed(1)
        random.shuffle(self.cards)