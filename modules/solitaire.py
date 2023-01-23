import random
from typing import Iterable
import gym


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


class Deck(Stack):
    def __init__(self):
        Stack.__init__(self, [], type="Deck")
        self.max = 13
        self.suits = ["Spades", "Hearts", "Diamonds", "Clubs"]
        for s in self.suits:
            for n in range(self.max):
                self.cards.append(Card(s, n + 1))

        random.Random().shuffle(self.cards)


class Solitaire(object):
    def __init__(self):
        self.deck = None
        self.num_t_stack = 8
        self.t_stack = None
        self.waste = None
        self.cards_per_turn = 3
        self.foundation = None
        self.next_cards = None
        self.complete = False
        self.deal_cards()

    def deal_cards(self):
        # deal deck out into tableau stacks
        self.foundation = []
        self.next_cards = Stack([],type="Next Cards")
        self.t_stack = []
        self.waste = Stack([], type="Waste")
        self.deck = Deck()
        for ts in range(1, self.num_t_stack):
            self.t_stack.append(Stack([],type=f"Tableau Stack {ts}"))
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
        num_next_cards = len(self.next_cards.cards)
        if num_next_cards >= 1:
            next_card = self.next_cards.cards[0].card_id()
        else:
            next_card = "None"
        if num_next_cards >= 2:
            following_cards = [c.card_id() for c in self.next_cards.cards[1:]]
        else:
            following_cards = "None"
        print(f"Next card:{next_card}")
        for n, c in enumerate(following_cards, 1):
            print(f"Following card {n}:{following_cards}")
        for n, s in enumerate(self.t_stack):
            visible_cards = [c.card_id() for c in s.cards if c.visible]
            print(f"TS {n}: {visible_cards}")
        for n, s in enumerate(self.foundation):
            if len(s.cards) == 0:
                continue
            c = s.get_top_card()
            print(f"F {n}: {c.card_id()}")

    def deal_next_cards(self):
        if not self.deck.cards:
            self.waste.cards.reverse()
            self.deck.cards = self.waste.cards
            self.waste.cards = []
            print("Cards recycled.")
        self.next_cards.cards.reverse()
        for c in self.next_cards.cards:
            self.waste.cards.insert(0, c)
        self.next_cards.cards = self.deck.cards[: self.cards_per_turn]
        self.next_cards.cards.reverse()
        self.deck.cards = self.deck.cards[self.cards_per_turn :]
        self.show_cards()
        return True
    
    def remove_card(self,stack):
        card = stack.remove_top_card()
        if stack.type == "Foundation":
            if not stack.cards:
                self.foundation.remove(stack)
                pass
        return card


    def move_card(self, action, dest_action=None):
        # Determine if the action corresponds to a tableau stack, foundation, or next_cards stack
        if action < len(self.t_stack):
            source_stack = self.t_stack[action]
            if source_stack.is_empty():
                print("Source stack empty.")
                return False, 0
            card = source_stack.get_top_card()
            
        elif action < len(self.t_stack) + 4:
            index = action - len(self.t_stack)
            if len(self.foundation) - 1 < index:
                print("Foundation pile does not exist.")
                return False, 0
            source_stack = self.foundation[index]
            if len(source_stack.cards) == 0:
                print("Foundation pile empty.")
                return False, 0
            card = source_stack.get_top_card()
        elif action == len(self.t_stack) + 4:
            if not self.next_cards.cards:
                print("Next cards pile is empty.")
                return False, 0
            source_stack = self.next_cards
            card = source_stack.get_top_card()
            self.show_cards()
            pass
        else:
            print("Invalid action")
            return False, 0
        # Check if the selected card is visible
        if not card.visible:
            print("Selected card is not visible.")
            return False, 0
        # Check if the card can be moved to foundation
        f_index = dest_action-len(self.t_stack)
        if (len(self.t_stack)<=dest_action<len(self.t_stack)+4):
            if len(self.t_stack)<=action < len(self.t_stack) + 4:
                print("Cannot move from foundation to foundation.")
                return False, 0
            if f_index < len(self.foundation):
                if (
                    self.foundation[f_index].cards[0].suit == card.suit
                    and self.foundation[f_index].cards[0].number == card.number - 1
                ):
                    print(f"Card {card.card_id()} moved to foundation.")
                    self.foundation[f_index].cards.insert(0, self.remove_card(source_stack))
                    if self.status():
                        return True, 5
                    return True, 1
                else:
                    print(f"Card {card.card_id()} does not fit in foundation.")
                    return False, 0
            elif card.number == 1:
                if f_index >= len(self.foundation):
                    print(f"Card {card.card_id()} moved to new foundation pile.")
                    new_f_stack = Stack([self.remove_card(source_stack)],type="Foundation")
                    self.foundation.insert(0,new_f_stack)
                    return True, 1
            else:
                print(f"Card {card.card_id()} does not fit in foundation.")
                return False, 0
        else:
            if dest_action < len(self.t_stack):
                dest_stack = self.t_stack[dest_action]
                if not dest_stack.cards:
                    if card.number != 13:
                        print("Only kings can be moved to empty tableau stacks.")
                        return False, 0
                    dest_stack.cards.insert(0,self.remove_card(source_stack))
                    print(f"Card {card.card_id()} moved to tableau stack {dest_action}.")
                    return True, 1
                
                dest_card = dest_stack.get_top_card()
                if dest_card.color == card.color:
                    print("Wrong color.")
                    return False, 0
                if dest_card.number == card.number + 1:
                    dest_stack.cards.insert(0,self.remove_card(source_stack))
                    print(f"Card {card.card_id()} moved to tableau stack {dest_action}.")
                    self.show_cards()
                    return True, 1
                else:
                    return False, 0


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
        int_options = range(1,len([c for c in self.t_stack[source].cards if c.visible])+1)
        int_options = [str(c) for c in int_options]
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
                self.play()
                break
            else: 
                print("Please enter a valid option.")
    
    def status(self):
        n_foundation = sum([len(s.cards) for s in self.foundation])
        if n_foundation == 52:
            return True
        