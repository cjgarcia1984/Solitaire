from modules.card import Card
from modules.deck import Deck
from modules.stack import Stack

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
        self.foundation = [Stack([],type="Foundation") for _ in range(4)]
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
        self.deal_next_cards()

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
            following_cards = ', '.join([c.card_id() for c in self.next_cards.cards[1:]])
        else:
            following_cards = "None"
        print(f"Next card: {next_card}")
        print(f"Following cards: {following_cards}")
        for n, s in enumerate(self.t_stack):
            visible_cards = ', '.join([c.card_id() for c in s.cards if c.visible])
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


    def move_card(self, source, dest=None, num_cards=1):
        def foundation_logic(sd):
            l = len(self.t_stack) + 4 > sd >= len(self.t_stack)
            return(l)
        def t_stack_logic(sd):
            l = (sd < len(self.t_stack))
            return l
        def next_card_logic(sd):
            l = (sd == len(self.t_stack) + 4)
            return l
        # Determine if the source corresponds to a tableau stack, foundation, or next_cards stack
        if num_cards>1:
            if not (t_stack_logic(source) and t_stack_logic(dest)):
                print("Can only move more than one card from and to tableau stacks.")
                return 0
        if "Tableau Stack" in source.type:
            source_stack = source
            if source_stack.is_empty():
                print("Source stack empty.")
                return 0
            if num_cards==1:
                card = source_stack.get_top_card()
            else:
                num_visible_cards = sum([c.visible for c in source_stack.cards])
                if num_visible_cards < num_cards:
                    print("Not enough visible cards in stack.")
                    return 0
                card = [source_stack.cards[n] for n in range(num_cards)]

            
        elif source.type == "Foundation":
            source_stack = source
            if len(source_stack.cards) == 0:
                print("Foundation pile empty.")
                return 0
            card = source_stack.get_top_card()
        elif source.type == "Next Cards":
            if not self.next_cards.cards:
                print("Next cards pile is empty.")
                return 0
            source_stack = source
            card = source_stack.get_top_card()
            self.show_cards()
            pass
        else:
            print("Invalid source")
            return 0
        # Check if the selected card is visible
        if not isinstance(card, list):
            if not card.visible:
                print("Selected card is not visible.")
                return 0
        # Check if the card can be moved to foundation
        f_index = dest-len(self.t_stack)
        if foundation_logic(dest):
            if source.type == "Foundation":
                print("Cannot move from foundation to foundation.")
                return 0
            if self.foundation[f_index].cards:
                if (
                    self.foundation[f_index].cards[0].suit == card.suit
                    and self.foundation[f_index].cards[0].number == card.number - 1
                ):
                    print(f"Card {card.card_id()} moved to foundation.")
                    self.foundation[f_index].cards.insert(0, source_stack.remove_top_card())
                    if self.status():
                        return 5
                    return 2
                else:
                    print(f"Card {card.card_id()} does not fit in foundation.")
                    return 0
            elif card.number == 1:
                print(f"Card {card.card_id()} moved to new foundation pile.")
                self.foundation[f_index].cards.append(source_stack.remove_top_card())
                return 2
            else:
                print(f"Card {card.card_id()} does not fit in foundation.")
                return 0
        else:
            if t_stack_logic(dest):
                if not isinstance(card,list):
                    card = [card]
                dest_stack = self.t_stack[dest]
                if not dest_stack.cards:
                    if card[0].number != 13:
                        print("Only kings can be moved to empty tableau stacks.")
                        return 0
                    for _ in card:
                        dest_stack.cards.insert(0,source_stack.remove_top_card())
                    print(f"Card {[c.card_id() for c in card]} moved to tableau stack {dest}.")
                    return 1
                
                dest_card = dest_stack.get_top_card()
                if dest_card.color == card[-1].color:
                    print("Wrong color.")
                    return 0
                if dest_card.number == card[-1].number + 1:
                    if num_cards>1:
                        self.show_cards()
                        pass
                    [dest_stack.cards.insert(n,source_stack.remove_top_card()) for n in range(num_cards)]
                    print(f"Card {[c.card_id() for c in card]} moved to tableau stack {dest}.")
                    self.show_cards()
                    if source.type == "Foundation":
                        return 0
                    else:
                        return 1
                else:
                    print("Wrong number.")
                    return 0


    def move_next_card(self, loc):
        cards = self.next_cards
        moved = self.move_card(cards, loc)
        if moved and self.waste.cards:
            self.next_cards.cards.append(self.waste.cards.pop(0))
            
    def move_from_t_stack(self, t_stack, loc, cards=1):
        cards = self.t_stack[t_stack]
        moved = self.move_card(cards, loc)
        if moved:
            if cards:
                cards.cards[0].visible=True
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
        