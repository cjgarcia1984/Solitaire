from typing import Iterable


class Stack(object):
    def __init__(self, cards: list,type=None):
        if not isinstance(cards,Iterable):
            cards = [cards]
        self.cards = cards
        self.type = type

    def get_top_card(self):
        if self.cards:
            top_card = self.cards[0]
            return top_card

    def remove_top_card(self):
        top_card = self.cards.pop(0)
        self.show_top_card()
        return top_card

    def is_empty(self):
        if not self.cards:
            return True
    
    def show_top_card(self):
        if not self.cards:
            return
        self.cards[0].visible = True