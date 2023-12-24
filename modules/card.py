class Card(object):
    SUIT_SYMBOLS = {"Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠"}
    SPECIAL_VALUES = {1: "A", 11: "J", 12: "Q", 13: "K"}

    def __init__(self, suit, number):
        self.suit = suit
        self.number = number
        self.color = "red" if suit in ["Hearts", "Diamonds"] else "black"
        self.visible = False

    def __repr__(self):
        color_code = "\033[91m" if self.color == "red" else ""
        reset_code = "\033[0m" if self.color == "red" else ""
        suit_symbol = Card.SUIT_SYMBOLS.get(self.suit, "")

        # Use special value names for 1, 11, 12, and 13
        number_or_face = Card.SPECIAL_VALUES.get(self.number, self.number)

        return (
            f"{color_code}{number_or_face}{suit_symbol}{reset_code}"
            if self.visible
            else "[Hidden]"
        )

    def set_visible(self, visibility):
        self.visible = visibility
