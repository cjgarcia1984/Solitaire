from modules.card import Card
from modules.deck import Deck
from modules.stack import Stack
import yaml
from copy import deepcopy

class Solitaire(object):
    def __init__(self, config=None, config_path=None):
        """
        Initialize the Solitaire game.

        Args:
            config (dict, optional): Configuration dictionary for the game. Defaults to None.
            config_path (str, optional): Path to a YAML file containing game configuration. Defaults to None.
        """
        # Attempt to load configuration from the file if provided
        if config_path:
            try:
                with open(config_path, 'r') as file:
                    self.config = yaml.safe_load(file)
            except FileNotFoundError:
                print(f"Error: Configuration file '{config_path}' not found.")
                self.config = {}
            except yaml.YAMLError as e:
                print(f"Error reading configuration file: {e}")
                self.config = {}
        else:
            self.config = config if config else {}
        self.history = []
        self.num_t_stack = 7
        self.foundation = [Stack(stack_type="Foundation") for _ in range(4)]
        self.t_stack = [Stack(stack_type="Tableau Stack")
                        for _ in range(self.num_t_stack)]
        self.waste = Stack(stack_type="Waste")
        self.next_cards = Stack(stack_type="Next Cards")
        self.complete = False
        self.deck = Deck(self.config.get("random_seed"))
        self.deal_cards()

    def deal_cards(self):
        """
        Distribute cards into the tableau stacks and deal initial next cards according to the game configuration.
        """
        for index, stack in enumerate(self.t_stack):
            for card_num in range(index + 1):
                card = self.deck.remove_card()
                card.visible = card_num == index  # Make the top card visible
                stack.add_card(card)

        # Set visibility of remaining cards in the deck
        for card in self.deck.cards:
            card.set_visible(True)

        # Initial dealing of next cards, depending on the game configuration
        # Check if there are any cards in the deck before dealing
        if self.deck.cards:
            # Initial dealing of next cards, depending on the game configuration
            for _ in range(self.config.get('cards_per_turn', 3)):
                self.next_cards.add_card(self.deck.remove_card())

    def show_cards(self):
        """
        Display the current state of the game, including the Next Cards, Foundation Stacks, and Tableau Stacks.
        """
        if not self.next_cards.cards and not self.deck.cards:
            "No cards left in deck. Deal again to reset deck."
            return
        print('=' * 60)

        # Display Next Cards
        self.display_next_cards()

        # Display Foundation Stacks
        self.display_foundation_stacks()

        # Display Tableau Stacks
        self.display_tableau_stacks()

        print('=' * 60)

    def display_tableau_stacks(self):
        """
        Print the cards in each tableau stack, showing the visible card at the bottom.
        """
        print("Tableau:")
        max_length = max(len(s.cards) for s in self.t_stack)
    
        # Print the identifiers for each tableau stack starting from 1
        for n in range(1, len(self.t_stack) + 1):
            print(f"{n}\t", end='')
        print()
    
        # Print the cards in each tableau stack, with the visible card at the bottom
        for i in range(max_length):
            for s in self.t_stack:
                if i < len(s.cards):
                    card = s.cards[-(len(s.cards)-i)]
                    print(f"{str(card) if card.visible else '[?]'}\t", end='')
                else:
                    print("\t", end='')
            print()

    def display_next_cards(self):
        """
        Display the cards in the Next Cards stack.
        """
        print("Next Cards:")
        if len(self.next_cards.cards) > 0:
            if len(self.next_cards.cards) == 1:
                next_cards_str = f"[{str(self.next_cards.cards[-1])}]"
            else:
                next_cards_str = ', '.join(
                    [str(card) for card in self.next_cards.cards[:-1]])
                next_cards_str += f", [{str(self.next_cards.cards[-1])}]"
            print(f"{next_cards_str if next_cards_str else 'None'}")
        else:
            print("None")

    def display_foundation_stacks(self):
        """
        Display the cards in each of the foundation stacks.
        """
        print("Foundation:")
        for n, s in enumerate(self.foundation):
            top_card = str(s.get_top_card()) if s.cards else "[]"
            print(f"F{n}: {top_card}", end='  ')
        print('\n' + '-' * 60)

    def deal_next_cards(self):
        """
        Deal the next set of cards from the deck to the Next Cards stack and handle the recycling of the waste pile if necessary.
        Returns True if the operation is successful.
        """
        # Move current next cards to the waste pile
        self.save_state()
        while self.next_cards.cards:
            card = self.next_cards.cards.pop(0)
            self.waste.cards.append(card)

        # Recycling waste pile if the deck is empty
        if not self.deck.cards and self.waste.cards:
            #print("Recycling waste pile.")
            self.deck.cards = self.waste.cards[:]
            self.waste.cards.clear()

        # Deal new cards from the deck to next cards
        num_cards_to_deal = min(len(self.deck.cards),
                                self.config.get('cards_per_turn', 3))
        if num_cards_to_deal > 0:
            for _ in range(num_cards_to_deal):
                card = self.deck.cards.pop(0)
                card.set_visible(True)
                self.next_cards.cards.append(card)
        else:
            print("No cards left to deal.")

        #self.show_cards()
        return True

    def move_card(self, source, dest, num_cards=1):
        """
        Move a card or a sequence of cards from one stack to another.

        Args:
            source (Stack): The stack from which the card(s) are to be moved.
            dest (Stack/int/str): The destination to move the card(s) to. Can be a Stack object or an identifier.
            num_cards (int, optional): The number of cards to move. Defaults to 1.

        Returns:
            int: 0 if the move is invalid, otherwise a positive integer representing the successful move.
        """
        if isinstance(dest, int):
            dest = dest - 1  # Adjust for 0-based index

        if not self.is_valid_move_request(source, dest, num_cards):
            #print("Invalid move.")
            return 0

        if isinstance(source, Stack):
            cards = self.get_cards_to_move(source, num_cards)
            if self.is_move_valid(source, dest, cards):
                self.save_state()
                result = self.process_move(source, dest, cards)

                # Check if the source is a tableau stack and turn over the next card
                if source.type == "Tableau Stack" and source.cards:
                    source.cards[-1].visible = True

                return result

        #print("Invalid source for move.")
        return 0

    def is_move_valid(self, source, dest, cards):
        """
        Check if a proposed move is valid based on the game rules.

        Args:
            source (Stack): The stack from which the card(s) are to be moved.
            dest (Stack/int): The destination stack or identifier.
            cards (list): The list of Card objects proposed to be moved.

        Returns:
            bool: True if the move is valid, False otherwise.
        """

        # Validate move from foundation
        if isinstance(dest, int):
            return self.is_valid_tableau_move(self.t_stack[dest], cards[0])   

        return True  # For other moves, add respective validations

    def is_valid_move_request(self, source, dest, num_cards):
        """
        Validate a move request based on the source, destination, and number of cards.

        Args:
            source (Stack): The source stack.
            dest (Stack/int/str): The destination stack or identifier.
            num_cards (int): Number of cards to be moved.

        Returns:
            bool: True if the move request is valid, False otherwise.
        """
        if isinstance(source, Stack):
            return (self.is_valid_tableau_destination(dest) or isinstance(dest, str) and dest in ['f', 't']) and \
                self.are_cards_movable(source, num_cards)
        return False

    def get_cards_to_move(self, source_stack, num_cards):
        """
        Get the list of cards to be moved from the source stack.

        Args:
            source_stack (Stack): The stack from which the cards are to be moved.
            num_cards (int): The number of cards to move.

        Returns:
            list: A list of Card objects to be moved.
        """
        if len(source_stack.cards) < num_cards:
            return []  # Not enough cards to move
        return source_stack.cards[-num_cards:]

    def process_move(self, source_stack, dest, cards):
        """
        Process the move of cards from the source stack to the destination.

        Args:
            source_stack (Stack): The stack from which the cards are being moved.
            dest (int/str): The identifier of the destination stack or type.
            cards (list): The cards to be moved.

        Returns:
            int: Numeric code indicating the result of the move.
        """
        if dest == 'f':
            # Moving to foundation (only allow single card move)
            return self.move_to_foundation(source_stack, cards[0]) if len(cards) == 1 else 0

        elif isinstance(dest, int):  # Moving to tableau
            dest_stack = self.t_stack[dest]
            for card in cards:
                dest_stack.add_card(card)
                source_stack.remove_card()

            # Format the list of card representations into a string for output
            cards_str = ', '.join([str(card) for card in cards])
            print(f"Card {cards_str} moved to tableau stack.")
            return 1

        # Add any additional destination types here

        return 0

    def is_valid_source_and_destination(self, source, dest, num_cards):
        """
        Check if the source and destination are valid for the move.

        Args:
            source (Stack): The source stack.
            dest (int/str): The destination stack or its identifier.
            num_cards (int): The number of cards to be moved.

        Returns:
            bool: True if the source and destination are valid, False otherwise.
        """
        if isinstance(dest, str) and dest == 'f':
            return True  # Destination is the foundation
        if isinstance(dest, int):
            # Destination is a tableau stack
           return 0 <= dest - 1 < len(self.t_stack) and ("Tableau Stack" in source.type or num_cards == 1)
        return False

    def are_cards_movable(self, source_stack, num_cards):
        """
        Check if the specified number of cards from the source stack are visible and can be moved.

        Args:
            source_stack (Stack): The stack from which the cards are to be moved.
            num_cards (int): The number of cards to check.

        Returns:
            bool: True if the cards can be moved, False otherwise.
        """
        if len(source_stack.cards) < num_cards:
            return False  # Not enough cards in the stack

        # Check if all the selected cards are visible
        return all(card.visible for card in source_stack.cards[-num_cards:])

    def is_valid_tableau_destination(self, dest):
        """
        Determine if the specified destination is a valid tableau stack.

        Args:
            dest (int): The index of the tableau stack.

        Returns:
            bool: True if the destination is a valid tableau stack, False otherwise.
        """
        return isinstance(dest, int) and dest < len(self.t_stack)

    def is_valid_tableau_move(self, dest_stack, card):
        """
        Validate a move to a tableau stack based on the game rules.

        Args:
            dest_stack (Stack): The destination tableau stack.
            card (Card): The card to be moved.

        Returns:
            bool: True if the move is valid according to the tableau rules, False otherwise.
        """

        if dest_stack.is_empty():
            # Only kings (number 13) can be moved to an empty stack
            return card.number == 13

        top_dest_card = dest_stack.get_top_card()

        # Validate color - they must be different
        is_valid_color = (top_dest_card.color != card.color)

        # Validate sequence - card number must be exactly one less
        is_valid_sequence = (top_dest_card.number == card.number + 1)

        return is_valid_color and is_valid_sequence

    def move_to_foundation(self, source_stack, card):
        """
        Attempt to move a card to the foundation.

        Args:
            source_stack (Stack): The stack from which the card is being moved.
            card (Card): The card to be moved.

        Returns:
            int: Numeric code indicating the result of the move. 0 for failure, 2 for success, 5 for game completion.
        """
        for foundation_stack in self.foundation:
            # If the foundation stack is not empty and the card suits match
            if foundation_stack.cards and card.suit == foundation_stack.get_top_card().suit:
                # If the card number is one more than the top card of the foundation stack
                if card.number == foundation_stack.get_top_card().number + 1:
                    # Move the card to the foundation stack
                    foundation_stack.add_card(source_stack.remove_card())
                    print(f"Card {str(card)} moved to foundation.")
                    return 5 if not self.status() else 100

            # If the foundation stack is empty and the card is an Ace (number 1)
            elif not foundation_stack.cards and card.number == 1:
                # Move the card to the new foundation pile
                foundation_stack.add_card(source_stack.remove_card())
                print(f"Card {str(card)} moved to new foundation pile.")
                return 5

        #print(f"Card {str(card)} does not fit in foundation.")
        return 0

    def play(self):
        """
        Main game loop for playing Solitaire. Manages user interactions and game progress until completion.
        """
        self.complete = self.status()
        while not self.complete:
            self.show_current_state()
            user_input = self.get_user_input()
            self.handle_user_action(user_input)
            self.complete = self.status()
        print("Congratulations! You've completed the game.")

    def show_current_state(self):
        """
        Display the current state of the game, prompting the user for their next action.
        """
        print("Current board:")
        self.show_cards()
        print("Enter your move or command (Enter to deal, 's' to show, 'u' to undo, 'q' to quit):")

    def get_user_input(self):
        """
        Obtain input from the user.

        Returns:
            str: The user's input, converted to lowercase and stripped of leading/trailing whitespace.
        """
        return input().lower().strip()

    def handle_user_action(self, user_input):
        """
        Handle the user's action based on their input.

        Args:
            user_input (str): The user's input command or action.
        """
        if user_input == 'u':
            self.undo_move()
            return
        if user_input == 's':
            self.show_cards()
        elif user_input == '':
            self.deal_next_cards()
        elif user_input == 'q':
            print("Game ended.")
            exit()
        elif len(user_input) in [1, 2]:
            self.parse_and_execute_move(user_input)
        else:
            print("Invalid input. Please try again.")

    def parse_and_execute_move(self, move):
        """
        Parse and execute a card move based on user input.

        Args:
            move (str): The user's move command.
        """
        parts = list(move)
        if len(parts) == 1:
            source = parts[0]
            dest = 'f'
        if len(parts) == 2:
            source, dest = parts
        self.parse_parts(source, dest)

    def parse_parts(self, source, dest, num_cards=None):
        if source == 'n':
            source_stack = self.next_cards
            num_cards = 1  # Only one card can be moved from next cards
        # Adjust for 1-based index
        elif source.isdigit():
            source_index = int(source) - 1  # Convert to 0-based index
            if source_index < 0 or source_index >= self.num_t_stack:
                print(f"Invalid source. Please enter a number between 1 and {self.num_t_stack}.")
                return
            source_stack = self.t_stack[source_index]
            if dest == 'f':
                num_cards = 1  # Only one card can be moved to the foundation
            elif num_cards is None:
                num_cards = self.get_num_cards_to_move(source_stack)
        else:
            #print("Invalid source.")
            return

        if dest == 'f':
            dest_stack = 'f'
        elif dest.isdigit():
            dest_stack = int(dest)
        else:
            print("Invalid destination.")
            return

        result = self.move_card(source_stack, dest_stack, num_cards)
        return result

    def get_num_cards_to_move(self, source_stack):
        """
        Determine the number of cards the user wishes to move from a source stack.

        Args:
            source_stack (Stack): The stack from which the cards are to be moved.

        Returns:
            int: The number of cards the user wishes to move.
        """
        visible_cards_count = len(
            [card for card in source_stack.cards if card.visible])
        if visible_cards_count > 1:
            print(
                f"Move how many cards from {source_stack.type}? (1-{visible_cards_count}, 'a' for all)")
            user_input = input().lower().strip()
            if user_input.isdigit() and 1 <= int(user_input) <= visible_cards_count:
                return int(user_input)
            elif user_input == 'a':
                return visible_cards_count
        return 1  # Default to moving only the top card

    def status(self):
        """
        Check the status of the game to determine if it is complete.

        Returns:
            bool: True if the game is complete (all cards are in the foundation), False otherwise.
        """
        total_cards_in_foundation = sum(
            len(stack.cards) for stack in self.foundation)
        return total_cards_in_foundation == 52

    def save_state(self):
        """
        Save the current state of the game.
        """
        # Create a deep copy of the current state
        state = {
            'foundation': deepcopy(self.foundation),
            't_stack': deepcopy(self.t_stack),
            'waste': deepcopy(self.waste),
            'next_cards': deepcopy(self.next_cards),
            'deck': deepcopy(self.deck)
        }
        # Push the copied state onto a stack
        self.history.append(state)

    def undo_move(self):
        """
        Undo the last move.
        """
        if self.history:
            last_state = self.history.pop()
            self.foundation = last_state['foundation']
            self.t_stack = last_state['t_stack']
            self.waste = last_state['waste']
            self.next_cards = last_state['next_cards']
            self.deck = last_state['deck']
            print("Last move undone.")
        else:
            print("No more moves to undo.")

