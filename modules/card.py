class Card(object):
    RED = '\033[91m'  # ANSI code for red text
    RESET = '\033[0m' # ANSI code to reset color
    SUIT_SYMBOLS = {
        "Hearts": "\u2665",  # Unicode for heart symbol
        "Diamonds": "\u2666",  # Unicode for diamond symbol
        "Clubs": "\u2663",  # Unicode for club symbol
        "Spades": "\u2660"  # Unicode for spade symbol
    }

    def __init__(self, suit, number):
        self.suit_dict = {
            "Spades": "black",
            "Hearts": "red",
            "Diamonds": "red",
            "Clubs": "black",
        }
        self.suit = suit
        self.number = number
        self.color = self.suit_dict[suit]
        self.visible = False

    def card_id(self):
        color = Card.RED if self.color == "red" else ""
        reset = Card.RESET if self.color == "red" else ""
        suit_symbol = Card.SUIT_SYMBOLS[self.suit]
        card_id = f"{color}{self.number}{suit_symbol}{reset}"
        return card_id