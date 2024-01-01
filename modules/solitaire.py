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
            self.config = self.open_config(config_path)
        if config:
            self.config = config
        self.history = []
        self.num_t_stack = 7
        self.foundation = {s: Stack(stack_type=f"Foundation", suit=s) for s in [
            "Spades", "Hearts", "Clubs", "Diamonds"]}
        self.t_stack = [Stack(stack_type="Tableau Stack")
                        for _ in range(self.num_t_stack)]
        self.waste = Stack(stack_type="Waste")
        self.next_cards = Stack(stack_type="Next Cards")
        self.complete = False
        self.show_messages = self.config.get('show_messages', True)
        self.deck = Deck(self.config.get("random_seed"))
        self.reward_dict = self.config.get(
            'reward_dict', self.open_config('configs/rewards.yaml'))
        self.points = 0  # Initialize points
        self.num_waste_cards = 0
        self.deal_cards()

    def open_config(self, config_path):
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_path}' not found.")
            return {}
        except yaml.YAMLError as e:
            print(f"Error reading configuration file: {e}")
            return {}

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
        print('=' * 60)

        # Display current score
        self.show_score()

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
        # Ensure consistent ordering of suits
        foundation_keys = list(self.foundation.keys())
        for idx, suit in enumerate(foundation_keys):
            top_card = str(self.foundation[suit].get_top_card(
            )) if self.foundation[suit].cards else "[]"
            # Display stack number in parentheses before the suit
            print(f"({idx + 1}){suit}: {top_card}", end='  ')
        print('\n' + '-' * 60)

    def deal_next_cards(self):
        """
        Deal the next set of cards from the deck to the Next Cards stack and handle the recycling of the waste pile if necessary.
        Returns True if the operation is successful.
        """
        # Move current next cards to the waste pile
        messages = []
        self.save_state()
        while self.next_cards.cards:
            card = self.next_cards.cards.pop(0)
            self.waste.cards.append(card)

        # Recycling waste pile if the deck is empty
        if not self.deck.cards and self.waste.cards:
            waste_card_count = len(self.waste.cards)
            if waste_card_count < self.num_waste_cards:
                messages.append("recycle_waste_pile_and_used_cards")
            else:
                messages.append("recycling_waste_pile")
            self.num_waste_cards = waste_card_count

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
            messages.append("dealing_next_cards")
        else:
            messages.append("no_cards_to_deal")
        return messages

    def move_card(self, source, dest, num_cards):
        """
        Move a card or a sequence of cards from one stack to another.
        Updated to handle error and success keys.
        """
        messages = []
        valid, move_keys = self.validate_move(source, dest, num_cards)
        messages.extend(move_keys)

        if not valid:
            return False, messages

        cards = self.get_cards_to_move(source, num_cards)
        if cards:
            self.save_state()  # Save the game state before making the move
            result = self.process_move(source, dest, num_cards)
            if not result:
                messages.append("error_moving_cards")
                return False, messages
            # Turn over the next card in the tableau stack if applicable
            if source.type == "Tableau Stack" and source.cards:
                if not source.cards[-1].visible:
                    source.cards[-1].visible = True
                    messages.append("reveal_hidden_card")
            return result, messages
        else:
            messages.append("no_cards_to_move")
            return False, messages

    def process_move(self, source, dest, num_cards):
        """
        Process the move of cards from the source stack to the destination.

        Args:
            source_stack (Stack): The stack from which the cards are being moved.
            dest (int/str): The identifier of the destination stack or type.
            cards (list): The cards to be moved.

        Returns:
            tuple: (bool, str) - A boolean indicating the success of the move and a string describing the action.
        """
        cards_to_move = self.get_cards_to_move(source, num_cards)
        for card in cards_to_move:
            dest.add_card(card)
            source.remove_card()
        return True

    def validate_move(self, source, dest, num_cards):
        """
        Check if a proposed move is valid based on the game rules.
        Now returns an error/success key instead of a message.
        """
        cards = self.get_cards_to_move(source, num_cards)
        messages = []
        if not cards:
            messages.append("requested_too_many_cards")
            return False, messages
        else:
            messages.append("requested_valid_number_of_cards")

        if not self.are_cards_movable(source, len(cards)):
            messages.append("cards_not_movable")
            return False, messages
        else:
            messages.append("cards_movable")

        if source.type == "Foundation" and dest.type == "Tableau Stack":
            result, message = self.is_valid_foundation_to_tableau_move(
                source, dest, num_cards)
            messages.append(message)
            return result, messages
        
        elif dest.type == "Foundation":
            if num_cards > 1:
                messages.append("invalid_foundation_move_number")
                return False, messages
            else:
                result, message = self.is_valid_foundation_move(cards[0], dest.suit, source.type)
                messages.append(message)
                return result, messages
        elif dest.type == "Tableau Stack":
            result, message = self.is_valid_tableau_move(dest, source, cards)
            messages.append(message)
            if not result:
                return False, messages
            else:
                return True, messages
        else:
            messages.append("invalid_destination")
            return False, messages

    def is_valid_foundation_to_tableau_move(self, source_foundation, dest_tableau, num_cards):
        """
        Validate a move from a foundation stack to a tableau stack.

        Args:
            source_foundation (Stack): The foundation stack from which the card is being moved.
            dest_tableau (Stack): The tableau stack to which the card is being moved.

        Returns:
            bool: True if the move is valid, False otherwise.
        """
        if num_cards > 1:
            return False, "invalid_foundation_move_number"

        if source_foundation.is_empty():
            return False, "empty_foundation_stack"  # Can't move from an empty foundation

        top_foundation_card = source_foundation.get_top_card()

        if dest_tableau.is_empty():
            if top_foundation_card.number == 13:
                return True, "valid_foundation_to_tableau_move"
            else:
                return False, "invalid_tableau_move_king"

        top_tableau_card = dest_tableau.get_top_card()

        # Check for alternating colors
        if top_foundation_card.color == top_tableau_card.color:
            return False, "invalid_foundation_move_suit"

        # Check for descending order
        if top_foundation_card.number != top_tableau_card.number - 1:
            return False, "invalid_foundation_move_number"

        return True, "valid_foundation_to_tableau_move"

    def is_valid_foundation_move(self, card, dest_suit, source_type):
        """
        Validate a move to the foundation based on the game rules.
        Updated to return specific dictionary keys.
        """
        if source_type == "Foundation":
            return False, "invalid_foundation_move_foundation"
        if card.suit != dest_suit:
            return False, "invalid_foundation_move_suit"
        if card.number == 1:
            return True, "ace_to_foundation"
        elif self.foundation[card.suit].cards:
            if card.number == self.foundation[card.suit].get_top_card().number + 1:
                return True, "successful_foundation_move"
            else:
                return False, "invalid_foundation_move_number"
        else:
            return False, "invalid_foundation_move_ace"

    def is_valid_tableau_move(self, dest_stack, source_stack, cards):
        """
        Validate a move to a tableau stack based on the game rules.
        Updated to return specific dictionary keys.
        """
        top_card = cards[0]
        if dest_stack.is_empty():
            if top_card.number == 13:
                if source_stack.cards != cards and source_stack.type != "Next Cards":
                    return True, "successful_tableau_move_king"
                else:
                    return True, "successful_tableau_transfer_king"
            else:
                return False, "invalid_tableau_move_king"
        else:
            top_dest_card = dest_stack.get_top_card()
            if top_dest_card.color != top_card.color:
                correct_color = True
            else:
                correct_color = False
            if top_dest_card.number == top_card.number + 1:
                correct_number = True
            else:
                correct_number = False
            if correct_color and correct_number:
                return True, "successful_tableau_move"
            if correct_color and not correct_number:
                return False, "invalid_tableau_move_number"
            if not correct_color and correct_number:
                return False, "invalid_tableau_move_color"
            else:
                return False, "invalid_tableau_move_color_number"

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
            return None  # Not enough cards to move
        return source_stack.cards[-num_cards:]

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

        if source_stack.type == "Next Cards" and num_cards > 1:
            return False

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

    def play(self):
        """
        Main game loop for playing Solitaire. Manages user interactions and game progress until completion.
        """
        self.complete = self.status()
        while not self.complete:
            self.show_current_state()
            available_moves = self.check_available_moves()
            if self.show_messages:
                print("Available moves:")
                for am in available_moves:
                    print(f"{am[0]} > {am[1]} ({am[2]} cards)")

            user_input = self.get_user_input()
            self.handle_user_action(user_input)
            if self.status():
                message = f"game_complete"
                points = self.reward_dict[message][0]
                self.points += points
                self.show_score()
                self.complete = True

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
            self.reward_points(self.deal_next_cards())
        elif user_input == 'q':
            print("Game ended.")
            exit()
        elif len(user_input) in [1, 2, 3]:
            parts = list(user_input)
            if len(parts) == 1:
                source = parts[0]
                dest = 'f'
            if len(parts) == 2:
                source, dest = parts
            if len(parts) == 3:
                if parts[0] == 'f':
                    dest = parts[2]
                    source = "".join(parts[:2])
                elif parts[1] == 'f':
                    dest = "".join(parts[1:])
                    source = parts[0]
            result, messages = self.execute_move(source, dest)
            points = self.reward_points(messages)

        else:
            print("Invalid input. Please try again.")

    def reward_points(self, messages, hide=False):
        """
        Reward points based on the messages returned from the game.
        """
        move_points = 0
        for message in messages:
            points, full_msg = self.reward_dict[message]
            if self.show_messages and not hide:
                print(full_msg)
            self.points += points
            move_points += points
        if self.show_messages and not hide:
            print(f"Total points for move: {move_points}")
            self.show_score()
        return move_points

    def parse_source_stack(self, source):
        if source == 'n':
            source_stack = self.next_cards
        # New code to handle foundation stacks
        elif source.startswith('f') and len(source) == 2 and source[1].isdigit():
            foundation_index = int(source[1]) - 1  # Convert to 0-based index
            if 0 <= foundation_index < 4:
                source_stack = self.foundation[list(self.foundation.keys())[foundation_index]]
            else:
                print(
                    "Invalid foundation stack. Please enter a valid stack (f1, f2, f3, f4).")
                return None
        elif source.isdigit():
            source_index = int(source) - 1  # Convert to 0-based index
            if source_index < 0 or source_index >= self.num_t_stack:
                print(
                    f"Invalid source. Please enter a number between 1 and {self.num_t_stack}.")
                return None
            source_stack = self.t_stack[source_index]
        else:
            return None
        return source_stack

    def parse_destination_stack(self, dest):
        if dest.startswith('f') and len(dest) == 2 and dest[1].isdigit():
            foundation_index = int(dest[1]) - 1  # Convert to 0-based index
            foundation_keys = list(self.foundation.keys())
            if 0 <= foundation_index < len(foundation_keys):
                dest_stack = self.foundation[foundation_keys[foundation_index]]
            else:
                print(
                    "Invalid foundation stack. Please enter a valid stack (f1, f2, f3, f4).")
                return None

        elif dest.isdigit():
            dest = int(dest) - 1  # Convert to 0-based index
            if dest < 0 or dest >= self.num_t_stack:
                print(
                    f"Invalid destination. Please enter a number between 1 and {self.num_t_stack}.")
                return None
            dest_stack = self.t_stack[dest]
        else:
            dest_stack = None
        return dest_stack

    def execute_move(self, source, dest, num_cards=None):
        messages = []
        source = self.parse_source_stack(source)
        if source is not None:
            dest = self.parse_destination_stack(dest)
            if dest is not None:
                messages.append("valid_source_and_valid_destination")
                if num_cards is None:
                    num_cards = self.get_num_cards_to_move(source, dest)
                result, move_msgs = self.move_card(source, dest, num_cards)
                if result:
                    if dest.type == "Foundation":
                        self.complete = self.status()
                messages.extend(move_msgs)
                if self.show_messages:
                    source_cards = dest.cards[-num_cards:]
                    dest_cards = dest.cards[:num_cards]
                    source_cards_str = ', '.join(
                        [str(card) for card in source_cards])
                    dest_cards_str = ', '.join(
                        [str(card) for card in dest_cards])
                    formatted_message = f"Move: {source_cards_str} > {dest_cards_str}. {[messages][-1]}"
                    print(formatted_message)

            else:
                result = False
                messages.append("valid_source_invalid_destination")
        else:
            result = False
            messages.append("invalid_source")
        return result, messages

    def show_score(self):
        """
        Display the current score.
        """
        print(f"Current score: {self.points}")

    def get_num_cards_to_move(self, source, dest, ):
        """
        Determine the number of cards the user wishes to move from a source stack.

        Args:
            source (Stack): The stack from which the cards are to be moved.

        Returns:
            int: The number of cards the user wishes to move.
        """
        if source.type == "Next Cards":
            return 1
        if dest.type == "Foundation":
            return 1
        visible_cards_count = len(
            [card for card in source.cards if card.visible])
        if visible_cards_count > 1:
            print(
                f"Move how many cards from {source.type}? (1-{visible_cards_count}, 'a' for all)")
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
            len(stack.cards) for stack in self.foundation.values())
        return total_cards_in_foundation == 52

    def save_state(self):
        """
        Save the current state of the game.
        """
        # Create a deep copy of the current state
        state = {
            'points': self.points,
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
            self.points = last_state['points']
            self.foundation = last_state['foundation']
            self.t_stack = last_state['t_stack']
            self.waste = last_state['waste']
            self.next_cards = last_state['next_cards']
            self.deck = last_state['deck']
            print("Last move undone.")
        else:
            print("No more moves to undo.")

    def check_available_moves(self):
        """
        Check for available moves in the game and return a list of possible moves,
        including moves involving multiple cards.

        Returns:
            list: A list of tuples representing the possible moves. Each tuple contains
                  the source stack, the destination stack, and the number of cards to be moved.
        """
        possible_moves = []

        # Check for moves from tableau to foundation or other tableau stacks
        for i, source_stack in enumerate(self.t_stack):
            for num_cards in range(1, len(source_stack.cards) + 1):
                cards = source_stack.cards[-num_cards:]
                if all(card.visible for card in cards):  # Only consider visible cards
                    cards_str = ', '.join([str(card) for card in cards])

                    # Check for moves to the foundation
                    for idx, (suit, foundation_stack) in enumerate(self.foundation.items()):
                        if num_cards == 1 and self.is_valid_foundation_move(cards[0], suit, source_stack.type)[0]:
                            possible_moves.append(
                                (f"{i+1}: [{cards_str}]", f"f{idx+1}", num_cards))

                    # Check for moves to other tableau stacks
                    for j, dest_stack in enumerate(self.t_stack):
                        if i != j and self.is_valid_tableau_move(dest_stack, source_stack, cards)[0]:
                            dest_card_str = str(dest_stack.get_top_card()) if dest_stack.cards else 'Empty'
                            possible_moves.append(
                                (f"{i+1}: [{cards_str}]", f"{j+1}: {dest_card_str}", num_cards))

        # Check for moves from next cards to tableau or foundation
        if self.next_cards.cards:
            next_card = self.next_cards.get_top_card()
            next_card_str = str(next_card)

            # Check for moves to the foundation
            for idx, (suit, foundation_stack) in enumerate(self.foundation.items()):
                if self.is_valid_foundation_move(next_card, suit, source_stack.type)[0]:
                    possible_moves.append(
                        (f"N: {next_card_str}", f"f{idx+1}", 1))

            # Check for moves to tableau stacks
            for i, dest_stack in enumerate(self.t_stack):
                if self.is_valid_tableau_move(dest_stack, source_stack, [next_card])[0]:
                    dest_card_str = str(dest_stack.get_top_card()) if dest_stack.cards else 'Empty'
                    possible_moves.append(
                        (f"N: {next_card_str}", f"{i+1}: {dest_card_str}", 1))

        # Check for moves from foundation to tableau
        #for idx, (suit, source_foundation) in enumerate(self.foundation.items()):
        #    if source_foundation.cards:
        #        top_foundation_card = source_foundation.get_top_card()
        #        foundation_card_str = str(top_foundation_card)
        #
        #        # Check for moves to tableau stacks
        #        for i, dest_stack in enumerate(self.t_stack):
        #            if self.is_valid_foundation_to_tableau_move(source_foundation, dest_stack, 1)[0]:
        #                dest_card_str = str(dest_stack.get_top_card()) if dest_stack.cards else 'Empty'
        #                possible_moves.append(
        #                    (f"f{idx+1}: {foundation_card_str}", f"{i+1}: {dest_card_str}", 1))

        return possible_moves

