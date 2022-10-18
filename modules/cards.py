import random


class Card(object):
    def __init__(self,suit,number):
        self.suit_dict = {"Spades": "black","Hearts":"red","Diamonds":"red","Clubs":"black"}
        self.suit = suit
        self.number = number
        self.color = self.suit_dict[suit]
        
class Stack(object):
    def __init__(self,cards: list):
        self.cards = cards
    
    def get_top_card(self):
        top_card = self.cards[0]
        return top_card
    
    def remove_top_card(self):
        top_card = self.cards.pop(0)
        return top_card

class Deck(Stack):
    def __init__(self):
        Stack.__init__(self,[])
        self.max = 13
        self.suits = ["Spades","Hearts","Diamonds","Clubs"]
        for s in self.suits:
            for n in range(self.max):
                self.cards.append(Card(s,n+1))
                
        random.shuffle(self.cards)

    
class Solitaire(object):
    def __init__(self):
        self.deck = Deck()
        self.num_tstacks = 8
        self.tstacks = []
        self.waste = []
        self.cards_per_turn = 3

        # deal deck out into tableau stacks
        for ts in range(1,self.num_tstacks):
            self.tstacks.append(Stack([]))
            s=ts
            while s>0:
                self.tstacks[ts-1].cards.append(self.deck.cards.pop(0))
                s -= 1
        
    def show_next_card(self):
        next_cards = self.deck.cards[:self.cards_per_turn]
        self.deck.cards = self.deck.cards[self.cards_per_turn:]
        print(next_cards[0].number,next_cards[0].suit)
        self.waste.extend(next_cards)
    
    def move_top_waste_card(self,loc):
        card = self.waste[0]
        dest_card = self.tstacks[loc].cards[0]
        if card.color == dest_card.color:
            print("Wrong color.")
            return
        elif card.color != dest_card.color:
            self.tstacks[loc].cards.insert(0,self.waste.pop(0))
            
        