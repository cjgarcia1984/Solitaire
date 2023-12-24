class Card(object):
    SUIT_SYMBOLS = {"Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠"}

    def __init__(self, suit, number):
        self.suit = suit
        self.number = number
        self.color = "red" if suit in ["Hearts", "Diamonds"] else "black"
        self.visible = False

    def __repr__(self):
        color_code = "\033[91m" if self.color == "red" else ""
        reset_code = "\033[0m" if self.color == "red" else ""
        suit_symbol = Card.SUIT_SYMBOLS.get(self.suit, "")
        return (
            f"{color_code}{self.number}{suit_symbol}{reset_code}"
            if self.visible
            else "[Hidden]"
        )

    def set_visible(self, visibility):
        self.visible = visibility
        return self
