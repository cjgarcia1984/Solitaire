from modules.cards import Deck, Solitaire


def main():
    deck = Deck()
    for c in deck.cards:
        print(c.number, c.suit)
        
    s = Solitaire()
    print(s)
        


if __name__ == "__main__":
    main()