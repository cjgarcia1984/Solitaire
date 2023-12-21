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
    
        # Display the next card and the following cards
        print("Next Cards:")
        next_cards_str = ', '.join([card.card_id() for card in self.next_cards.cards[:-1]])
        next_cards_str += f", [{self.next_cards.cards[-1].card_id()}]"
        print(f"{next_cards_str if next_cards_str else 'None'}")
        print('-' * 40)
    
        # Display the foundation stacks
        print("Foundation:")
        for n, s in enumerate(self.foundation):
            top_card = s.get_top_card().card_id() if s.cards else "[Empty]"
            print(f"F{n}: {top_card}", end='  ')
        print('\n' + '-' * 40)
    
        # Display the tableau stacks with identifiers at the top
        print("Tableau:")
        max_length = max(len(s.cards) for s in self.t_stack)  # Find the longest stack for formatting

        # Print the identifiers for each tableau stack
        for n, _ in enumerate(self.t_stack):
            print(f"{n}\t", end='')
        print()  # Newline after the identifiers

        # Print the cards in each tableau stack
        for i in range(max_length):
            for s in self.t_stack:
                if len(s.cards) > i:
                    card = s.cards[-(i+1)]  # Invert the order
                    print(f"{card.card_id() if card.visible else '[?]'}\t", end='')
                else:
                    print("\t", end='')
            print()  # Newline after each level of cards
        print('=' * 40)


    def deal_next_cards(self):
        if not self.deck.cards:
            self.waste.cards
            self.deck.cards = self.waste.cards
            self.waste.cards = []
            print("Cards recycled.")
        self.next_cards.cards.reverse()
        for c in reversed(self.next_cards.cards):
            self.waste.cards.append(c)
        self.next_cards.cards = self.deck.cards[: self.cards_per_turn]
        #self.next_cards.cards.reverse()
        self.deck.cards = self.deck.cards[self.cards_per_turn :]
        self.show_cards()
        return True


    def is_valid_source_and_destination(self, source, dest, num_cards):
        """Check if the source and destination are valid for the move."""
        if isinstance(dest, str) and dest == 'f':
            return True  # Destination is the foundation
        if isinstance(dest, int):
            # Destination is a tableau stack
            return dest < len(self.t_stack) and ("Tableau Stack" in source.type or num_cards == 1)
        return False

    def is_card_visible_and_movable(self, card):
        """Check if the card or cards are visible and can be moved."""
        if isinstance(card, list):
            # Check if all cards in the list are visible
            return all(c.visible for c in card)
        else:
            return card.visible

    def is_valid_tableau_destination(self, dest):
        """Check if the destination is a valid tableau stack."""
        return isinstance(dest, int) and dest < len(self.t_stack)

    def is_valid_tableau_move(self, dest_stack, card):
        """Validate color and sequence for tableau move."""
        if dest_stack.is_empty():
            # Only kings (number 13) can be moved to an empty stack
            return card.number == 13 if isinstance(card, Card) else card[0].number == 13

        top_dest_card = dest_stack.get_top_card()

        # Determine the bottom card of the moving sequence
        bottom_card = card if isinstance(card, Card) else card[0]

        # Check the color and number sequence for the bottom card
        is_valid_color = top_dest_card.color != bottom_card.color
        is_valid_sequence = top_dest_card.number == bottom_card.number + 1

        return is_valid_color and is_valid_sequence


    def move_to_tableau(self, source_stack, dest_stack, cards):
        """Move the card(s) to the tableau stack."""
        # Reverse the order of cards for correct insertion
        for card in reversed(cards):
            dest_stack.cards.insert(0, card)
            source_stack.cards.remove(card)

        # Format the list of card representations into a string
        cards_str = ', '.join([card.card_id() for card in cards])
        print(f"Card {cards_str} moved to tableau stack.")
        self.show_cards()
        return 1


    def move_to_foundation(self, source_stack, card):
        """Move the card to the foundation."""
        for foundation_stack in self.foundation:
            if foundation_stack.cards and card.suit == foundation_stack.cards[0].suit:
                if card.number == foundation_stack.cards[0].number + 1:
                    foundation_stack.cards.insert(0, source_stack.remove_top_card())
                    print(f"Card {card.card_id()} moved to foundation.")
                    return 2 if not self.status() else 5
            elif not foundation_stack.cards and card.number == 1:
                foundation_stack.cards.append(source_stack.remove_top_card())
                print(f"Card {card.card_id()} moved to new foundation pile.")
                return 2
        print(f"Card {card.card_id()} does not fit in foundation.")
        return 0

    def move_card(self, source, dest=None, num_cards=1):
        """Simplified move_card logic."""
        if not self.is_valid_source_and_destination(source, dest, num_cards):
            print("Invalid source or destination.")
            return 0
    
        source_stack = source
        if num_cards == 1:
            cards = [source_stack.get_top_card()]  # Single card
        else:
            # Multiple cards: Select from the specified card to the bottom of the stack
            cards = source_stack.cards[-num_cards:]
    
        if not self.is_card_visible_and_movable(cards):
            print("Selected card is not visible.")
            return 0
    
        if isinstance(dest, str) and dest == 'f':
            # Move to foundation (only allow single card move)
            return self.move_to_foundation(source_stack, cards[0]) if num_cards == 1 else 0
        elif self.is_valid_tableau_destination(dest):
            dest_stack = self.t_stack[dest]
            bottom_card = cards[-1]  # The bottom card of the sequence
            if self.is_valid_tableau_move(dest_stack, bottom_card):
                return self.move_to_tableau(source_stack, dest_stack, cards)
    
        print("Invalid move.")
        return 0


    def move_next_card(self, dest):
        if not self.next_cards.cards:
            print("No more cards in the next cards pile.")
            return

        # Select the last card in the next_cards stack as the card to move
        source_card = self.next_cards.cards[-1]

        # Move the specific card
        moved = self.move_card(Stack([source_card], type="Next Cards"), dest)
        if moved:
            # Successfully moved, so remove the card from next_cards
            self.next_cards.cards.pop()

        self.show_cards()

            
    def move_from_t_stack(self, t_stack, loc, num_cards=1):
        cards = self.t_stack[t_stack]
        moved = self.move_card(cards, loc, num_cards=num_cards)
        if moved:
            if not isinstance(cards, list):
                cards = cards.cards
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
                self.move_from_t_stack(source, dest,num_cards=int(user_input))
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
        