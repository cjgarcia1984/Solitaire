from modules.stack import Stack
from modules.card import Card
import random


class Deck(Stack):
    def __init__(self, random_seed=None):
        Stack.__init__(self, [], stack_type="Deck")
        self.max = 13
        self.suits = ["Spades", "Hearts", "Diamonds", "Clubs"]
        for s in self.suits:
            for n in range(self.max):
                self.cards.append(Card(s, n + 1))
        if random_seed is not None:
            random.seed(random_seed)
        random.shuffle(self.cards)