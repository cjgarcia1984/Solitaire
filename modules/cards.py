import random
from typing import Iterable

class Card(object):
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
        card_id = (self.number, self.suit)
        return card_id


class Stack(object):
    def __init__(self, cards: list):
        if not isinstance(cards,Iterable):
            cards = [cards]
        self.cards = cards

    def get_top_card(self):
        top_card = self.cards[0]
        return top_card

    def remove_top_card(self):
        top_card = self.cards.pop(0)
        return top_card


class Deck(Stack):
    def __init__(self):
        Stack.__init__(self, [])
        self.max = 13
        self.suits = ["Spades", "Hearts", "Diamonds", "Clubs"]
        for s in self.suits:
            for n in range(self.max):
                self.cards.append(Card(s, n + 1))

        random.Random(2).shuffle(self.cards)


class Solitaire(object):
    def __init__(self):
        self.deck = Deck()
        self.num_t_stack = 8
        self.t_stack = []
        self.waste = Stack([])
        self.cards_per_turn = 3
        self.foundation = []
        self.next_cards = []
        self.complete = False

        # deal deck out into tableau stacks
        for ts in range(1, self.num_t_stack):
            self.t_stack.append(Stack([]))
            s = ts - 1
            top_card = self.deck.cards.pop(0)
            top_card.visible = True
            self.t_stack[ts - 1].cards.append(top_card)
            while s > 0:
                self.t_stack[ts - 1].cards.append(self.deck.cards.pop(0))
                s -= 1

        
        for c in self.deck.cards:
            c.visible = True

    def show_cards(self):
        if not self.next_cards:
            print("Deal cards first.")
            return
        print(f"Next card:{self.next_cards[0].card_id()}")
        for n, c in enumerate(self.next_cards[1:], 1):
            print(f"Following card {n}:{c.card_id()}")
        for n, s in enumerate(self.t_stack):
            visible_cards = [c.card_id() for c in s.cards if c.visible]
            print(f"TS {n}: {visible_cards}")
        for n, s in enumerate(self.foundation):
            c = s.get_top_card()
            print(f"F {n}: {c.card_id()}")

    def deal_next_cards(self):
        if not self.deck.cards:
            self.waste.cards.reverse()
            self.deck.cards = self.waste.cards
            self.waste.cards = []
            print("Cards recycled.")
        self.next_cards.reverse()
        for c in self.next_cards:
            self.waste.cards.insert(0, c)
        self.next_cards = self.deck.cards[: self.cards_per_turn]
        self.next_cards.reverse()
        self.deck.cards = self.deck.cards[self.cards_per_turn :]
        self.show_cards()

    def move_card(self, cards, loc, num_cards=1):
        card = cards[:num_cards]
        bottom_card = card[-1]
        top_card = card[0]
        if not isinstance(card,list):
            card = [card]
        if [c for c in card if not c.visible]:
            print("Selected cards are not all visible")
            return False
        if loc == "f":
            if len(card) > 1:
                print("Cannot move more than one card to foundation at a time.")
                return False
            
            if self.foundation:
                for f in self.foundation:
                    if (
                        f.cards[0].suit == top_card.suit
                        and f.cards[0].number == top_card.number - 1
                    ):
                        print(f"Card {top_card.card_id()} moved to foundation.")
                        f.cards.insert(0, [cards.pop(0)])
                        return True
                    
            if top_card.number == 1:
                print(f"Card {top_card.card_id()} moved to new foundation pile.")
                new_f_stack = Stack([cards.pop(0)])
                self.foundation.append(new_f_stack)
                return True
            else:
                print(f"Card {top_card.card_id()}does not fit in foundation.")
                return False

        if loc == "k":
            if bottom_card.number == 13:
                self.t_stack = [s for s in self.t_stack if s.cards]
                if len(self.t_stack) < self.num_t_stack-1:
                    print(f"{[c.card_id() for c in card]} moved to new stack.")
                    self.t_stack.append(Stack(card))
                    for c in card:
                        cards.pop(0)
                    return True
                else:
                    print("No empty spots available.")
                    return False
            else:
                print(f"Card {bottom_card.card_id()}not a king.")
                return

        dest_card = self.t_stack[loc].cards[0]
        if bottom_card.color == dest_card.color:
            print("Wrong color.")
            return False
        if bottom_card.number == dest_card.number - 1:
            print(f"Card(s) {[c.card_id() for c in card]} added to stack {loc}.")
            self.t_stack[loc].cards[0:0] = card
            for c in card:
                cards.pop(0)
            return True
        else:
            print(f"Card {[c.card_id() for c in card]} does not go under {dest_card.card_id()}.")
            return False

    def move_next_card(self, loc):
        cards = self.next_cards
        moved = self.move_card(cards, loc)
        if moved and self.waste.cards:
            self.next_cards.append(self.waste.cards.pop(0))

    def move_from_t_stack(self, t_stack, loc, cards=1):
        cards = self.t_stack[t_stack].cards
        moved = self.move_card(cards, loc)
        if moved:
            if cards:
                cards[0].visible=True
            self.show_cards()
            
    def play(self):
        self.complete = self.status()
        options = ["s","m","d"]
        print("Select option:")
        user_input = ""
        while user_input not in options:
            print("Show (s); Move (m); Deal (d)")
            user_input = input()
            if user_input == "s":
                self.show_cards()
                break
            elif user_input == "m":
                self.ui_move()
                break
            elif user_input == "d":
                self.deal_next_cards()
                break
            else: 
                print("Please enter a valid option.")
                
    def ui_move(self):
        options = ["n","t","r"]
        print("Select option:")
        user_input = ""
        while user_input not in options:
            print("Move from: Next card (n); Tableau stack (t) or Return (r)")
            user_input = input()
            if user_input == "n":
                self.ui_move_next_card()
            elif user_input == "t":
                self.ui_select_t_stack()
            elif user_input == "r":
                self.play()
            else: 
                print("Please enter a valid option.")   

    def ui_move_next_card(self):
        options = ["f","k","r"]
        int_options = [str(i) for i in range(len(self.t_stack))]
        print("Select option:")
        user_input = ""
        while user_input not in options or user_input not in int_options:
            print("Move to: Tableau stack (int); Foundation (f); New pile (k); or Return (r)")
            user_input = input()
            if user_input in int_options:
                self.move_next_card(int(user_input))
                self.play()
                break
            elif user_input == "f":
                self.move_next_card("f")
                self.play()
                break
            elif user_input == "k":
                self.move_next_card("k")
                self.play()
                break
            elif user_input == "r":
                self.ui_move()
                break
            else: 
                print("Please enter a valid option.")  
                
    def ui_select_t_stack(self):
        int_options = [str(i) for i in range(len(self.t_stack))]
        options = ["r"]
        print("Select option:")
        user_input = ""
        while user_input not in options or user_input not in int_options:
            print("Move from tableau stack (int) or Return (r)")
            user_input = input()
            if user_input in int_options:
                self.ui_select_t_stack_dest(int(user_input))
                break
            elif user_input == "r":
                self.ui_move()
                break
            else: 
                print("Please enter a valid option.")  
                
    def ui_select_t_stack_dest(self,n):
        int_options = [str(i) for i in range(len(self.t_stack))]
        options = ["f","k","r"]
        print("Select option:")
        user_input = ""
        while user_input not in options or user_input not in int_options:
            print("Move to: Tableau stack (int); Foundation (f); New pile (k); or Return (r)")
            user_input = input()
            if user_input in int_options:
                self.ui_move_t_stack(n,int(user_input))
                break
            elif user_input == "f":
                self.move_from_t_stack(n,"f")
                self.play()
                break
            elif user_input == "k":
                self.move_from_t_stack(n,"k")
                self.play()
                break
            elif user_input == "r":
                self.ui_select_t_stack()
                break
            else: 
                print("Please enter a valid option.") 
                
    def ui_move_t_stack(self,source,dest):
        options = ["r"]
        int_options = range(1,len([c for c in self.t_stack[source] if c.visible])+1)
        print("Select option:")
        user_input = ""
        while user_input not in options or user_input not in int_options:
            print("Number of cards to move (int) or Return (r)")
            user_input = input()
            if user_input in int_options:
                self.move_from_t_stack(source, dest,cards=int(user_input))
                self.play()
                break
            elif user_input == "r":
                self.ui_select_t_stack_dest()
                break
            else: 
                print("Please enter a valid option.")
    
    def status(self):
        n_foundation = sum([len(s.cards) for s in self.foundation])
        if n_foundation == 52:
            return True
        