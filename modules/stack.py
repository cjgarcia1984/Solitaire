class Stack(object):
    def __init__(self, cards=None, stack_type=None, suit=None):
        self.cards = cards if cards else []
        self.type = stack_type
        self.suit = suit

    def add_card(self, card):
        self.cards.append(card)

    def add_cards(self, cards):
        self.cards.extend(cards)

    def remove_card(self):
        return self.cards.pop() if self.cards else None

    def get_top_card(self):
        return self.cards[-1] if self.cards else None

    def move_cards_to(self, destination, num_cards=1):
        if len(self.cards) >= num_cards:
            for _ in range(num_cards):
                destination.add_card(self.remove_card())

    def is_empty(self):
        return not self.cards

    def __len__(self):
        return len(self.cards)

    def __repr__(self):
        return ", ".join([str(card) for card in self.cards])
