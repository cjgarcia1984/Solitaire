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
        self.foundation = {n: Stack(stack_type=f"Foundation") for n in [
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
        for n, s in self.foundation.items():
            top_card = str(s.get_top_card()) if s.cards else "[]"
            print(f"{n}: {top_card}", end='  ')
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
            message = "recycling_waste_pile"
            self.update_points_and_display_message(message)
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
                # self.show_cards()
            message = "dealing_next_cards"
            self.update_points_and_display_message(message, hide=True)
        else:
            message = "dealing_next_cards"
            self.update_points_and_display_message(message)
        return message

    def move_card(self, source, dest, num_cards=1):
        """
        Move a card or a sequence of cards from one stack to another.
        Updated to handle error and success keys.
        """
        valid, move_key = self.validate_move(source, dest, num_cards)

        points, message = self.reward_dict[move_key]
        self.points += points

        if not valid:
            return False, message

        cards = self.get_cards_to_move(source, num_cards)
        if cards:
            self.save_state()  # Save the game state before making the move
            result = self.process_move(source, dest, num_cards)
            if not result:
                return False, "Error moving cards."
            # Turn over the next card in the tableau stack if applicable
            if source.type == "Tableau Stack" and source.cards:
                source.cards[-1].visible = True
                self.points += self.reward_dict["reveal_hidden_card"][0]

            return result, message

        return False, "No cards to move."

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

        if not cards:
            return False, "requested_too_many_cards"
        else:
            self.points += self.reward_dict["requested_valid_number_of_cards"][0]

        if not self.are_cards_movable(source, len(cards)):
            return False, "cards_not_movable"
        else:
            self.points += self.reward_dict["cards_movable"][0]

        if dest.type == "Foundation":
            return self.is_valid_foundation_move(cards[0])
        elif dest.type == "Tableau Stack":
            valid, key = self.is_valid_tableau_move(dest, cards)
            if not valid:
                return False, key
            return True, "successful_tableau_move"
        else:
            return False, "invalid_destination"

    def get_foundation_stack(self, card):
        return self.foundation[card.suit]

    def is_valid_foundation_move(self, card):
        """
        Validate a move to the foundation based on the game rules.
        Updated to return specific dictionary keys.
        """
        if card.number == 1:
            return True, "ace_to_foundation"
        elif self.foundation[card.suit].cards:
            if card.number == self.foundation[card.suit].get_top_card().number + 1:
                return True, "successful_foundation_move"
            else:
                return False, "invalid_foundation_move_number"
        else:
            return False, "invalid_foundation_move_ace"

    def is_valid_tableau_move(self, dest_stack, cards):
        """
        Validate a move to a tableau stack based on the game rules.
        Updated to return specific dictionary keys.
        """
        top_card = cards[0]
        if dest_stack.is_empty():
            if top_card.number == 13:
                if top_card.king_on_bottom == False:
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
            self.deal_next_cards()
        elif user_input == 'q':
            print("Game ended.")
            exit()
        elif len(user_input) in [1, 2]:
            parts = list(user_input)
            if len(parts) == 1:
                source = parts[0]
                dest = 'f'
            if len(parts) == 2:
                source, dest = parts
            self.execute_move(source, dest)
        else:
            print("Invalid input. Please try again.")

    def parse_source_stack(self, source):
        if source == 'n':
            source_stack = self.next_cards
        # Adjust for 1-based index
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

    def parse_destination_stack(self, dest, source):
        if dest == 'f':
            cards_to_move = self.get_cards_to_move(source, 1)
            if cards_to_move:
                dest_stack = self.get_foundation_stack(cards_to_move[0])
            else:
                dest_stack = None

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
        source = self.parse_source_stack(source)
        if source is not None:
            dest = self.parse_destination_stack(dest, source)
            if dest is not None:
                self.points += self.reward_dict["valid_source_and_valid_destination"][0]
                if num_cards is None:
                    num_cards = self.get_num_cards_to_move(source, dest)
                points = self.points
                result, msg = self.move_card(source, dest, num_cards)
                points = self.points - points
                if self.show_messages:
                    source_cards = dest.cards[-num_cards:]
                    dest_cards = dest.cards[:num_cards]
                    source_cards_str = ', '.join(
                        [str(card) for card in source_cards])
                    dest_cards_str = ', '.join(
                        [str(card) for card in dest_cards])
                    formatted_message = f"Move: {source_cards_str} > {dest_cards_str}. {msg}"
                    print(formatted_message)
                if self.show_messages:
                    self.show_score()
                return result, msg, points
            else:
                return False, self.reward_dict["valid_source_invalid_destination"][0], self.reward_dict["valid_source_invalid_destination"][0]
        else:
            return False, self.reward_dict["invalid_source"][1], self.reward_dict["invalid_source"][0]

    def update_points_and_display_message(self, action_key, hide=False):
        """
        Update points and display message based on the action key.

        Args:
            action_key (str): Key to look up in the reward dictionary.
        """
        points, message = self.reward_dict[action_key]
        self.points += points
        if self.show_messages and not hide:
            print(message)

    def show_score(self):
        """
        Display the current score.
        """
        print(f"Current score: {self.points}")

    def get_num_cards_to_move(self, source, dest):
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
