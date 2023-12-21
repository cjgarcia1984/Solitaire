from modules.solitaire import Deck, Solitaire

def main():
    deck = Deck()
    for c in deck.cards:
        print(c.number, c.suit)
        
    s = Solitaire()
    while not s.complete:
        s.play()

    print(s)
        


if __name__ == "__main__":
    main()