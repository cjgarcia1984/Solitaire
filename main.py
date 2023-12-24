from modules.solitaire import Deck, Solitaire


def main():
    deck = Deck()
    for c in deck.cards:
        print(c.number, c.suit)

    s = Solitaire(config_path="configs/config.yaml")
    while not s.complete:
        s.play()



if __name__ == "__main__":
    main()
