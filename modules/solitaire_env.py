import gymnasium
from gymnasium import spaces
from modules.solitaire import Solitaire
import numpy as np
import random
import csv

def sequential_num_generator(start=1, end=None):
    i = start
    while end is None or i < end:
        yield i
        i += 1

# Constants for encoding
NUM_SUITS = 4
NUM_RANKS = 13
NUM_COLORS = 2


# Change 10 to any other end value or remove it for an infinite sequence
number_gen = sequential_num_generator(start=1, end=None)


class SolitaireEnv(gymnasium.Env):
    metadata = {'render.modes': ['human', 'ansi']}

    def __init__(self, config=None):
        super(SolitaireEnv, self).__init__()
        # Initialize the Solitaire game
        self.config = config.get('env')
        self.game = Solitaire(config=config)
        self.action_log_file = self.config.get('action_log_file', 'action_log.csv')
        with open(self.action_log_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['total_episode_count', 'episode', 'step', 'action', 'source_stack', 'destination_stack', 'num_cards', 'reward', 'terminated', 'exploration_rate'])

        self.num_source_stacks = 10
        self.num_destinations = 8  # 7 tableau stacks, 1 foundation stack
        self.max_cards_per_move = NUM_RANKS  # Maximum number of cards that can be moved at once
        # Define action space (source_stack, destination_stack, num_cards)
        # 9 source stacks, 8 destination stacks, 1 card
        self.action_space = spaces.Discrete(
            self.num_source_stacks * self.num_destinations * self.max_cards_per_move)
        self.global_action_history = []
        self.action_repeat_threshold = 2

        # Number of steps with no progress to consider stagnation

        self.steps_since_progress = 0

        # Define observation space (using a simple representation for now)
        # For a more complex representation, you might need a multi-dimensional Box or a Dict space
        self.max_cards_per_stack = 24  # or any number that suits your game
        num_elements = NUM_RANKS * self.max_cards_per_stack  # 13 cards per stack
        self.observation_space = spaces.Box(
            low=-1, high=52, shape=(num_elements,), dtype=np.int32)

        self.current_seed = None  # Initialize a variable to store the current seed
        self.prev_state = {
            'foundation_count': [0, 0, 0, 0],
            'hidden_cards': set()
        }
        # Define a dictionary for rewards
        self.reward_values = self.config.get('reward_values', {})
        self.current_episode = 0
        self.total_episodes_count = 0
        self.current_step = 0
        self.move_count = 0
        self.exploration_rate = None

    def reset(self, seed=2, return_info=False, options=None):
        self.global_action_history = []

        seed = next(number_gen)
        config = {'cards_per_turn': 3, 'random_seed': seed}
        self.game = Solitaire(config)
        observation = self.get_observation()
        info = {}  # You can add additional reset info if needed
        self.current_episode += 1
        self.current_step = 0
        print(f"Successful moves: {self.move_count}")
        self.move_count = 0
        # Make sure to return a tuple of (observation, info)
        return observation, info

    def step(self, action):
        # Extract action details
        if isinstance(action, np.ndarray):
            action = int(action)
        source_idx, dest_idx, num_cards = self.decode_action(action)

        # Initialize reward
        reward = 0

        # Get the game state before the action
        prev_state = self.get_game_state()
        
        # Execute the action
        if source_idx == 9:  # Deal next cards action
            self.game.deal_next_cards()
            reward += self.reward_values['deal_cards']
        else:
            source_stack = self.get_stack(source_idx)
            dest_stack = self.get_stack(dest_idx)
            move_result = self.game.parse_parts(source_stack, dest_stack, num_cards=num_cards)
            if move_result:
                self.move_count += 1
                reward += self.reward_values['move_success']
                # Check for king moved to new empty stack
                # Check if the destination is a tableau stack and the bottom card of the move is a king
                if dest_stack.isdigit() and num_cards > 0:
                    tableau_index = int(dest_stack) - 1
                    stack = self.game.t_stack[tableau_index]
                    if len(stack.cards) >= num_cards:
                        bottom_card = stack.cards[-num_cards]
                        if bottom_card.number == 13 and bottom_card.visible and num_cards == len(stack.cards):  # King
                            reward += self.reward_values['move_king_to_empty_tableau']
            else:
                reward += self.reward_values['move_fail']


        # Get the updated game state
        new_state = self.get_game_state()

        # Check for progress in the foundation
        if new_state['foundation_count'] > prev_state['foundation_count']:
            reward += self.reward_values['add_to_foundation']
        elif new_state['foundation_count'] < prev_state['foundation_count']:
            reward += self.reward_values['remove_from_foundation']

        # Check for revealing hidden cards
        if len(new_state['hidden_cards']) < len(prev_state['hidden_cards']):
            reward += self.reward_values['reveal_hidden']


        # Update global action history
        self.global_action_history.append(action)
        if len(self.global_action_history) > self.config.get('max_global_history_length', 10):
            self.global_action_history.pop(0)

        # Calculate the frequency of the current action in the last x actions
        recent_action_count = self.global_action_history.count(action)

        # Apply penalty if action is repeated more than threshold and not the 'deal next cards' action
        if recent_action_count > self.config.get('action_repeat_threshold', 2) and source_idx != 9:
            penalty = self.reward_values['repeat_action'] * (recent_action_count ** 2)
            reward += penalty

        # Check for game completion and stagnation
        terminated = self.game.complete
        if self.has_made_progress():
            self.steps_since_progress = 0
        else:
            self.steps_since_progress += 1
        if self.steps_since_progress >= self.config.get('stagnation_threshold', 1000):
            terminated = True
            self.game.show_cards()


        # Reward for completing the game
        if self.game.status():
            reward += self.reward_values['game_complete']
            print(f"Game completed in {self.current_step} steps")
            terminated = True

        # Get the observation and additional info
        observation = self.get_observation()
        truncated = False
        info = {}
        self.current_step += 1
        self.total_episodes_count += 1

        self.log_action([self.total_episodes_count, self.current_episode, self.current_step, action, source_idx, dest_idx, num_cards, reward, terminated, self.exploration_rate])

        return observation, reward, terminated, truncated, info

    def log_action(self, log_data):
        with open(self.action_log_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(log_data)


    def has_made_progress(self):
        # Get the current game state
        current_state = self.get_game_state()

        # Compare the current state with the previous state to determine progress
        progress_made = current_state['foundation_count'] != self.prev_state['foundation_count'] \
            or current_state['hidden_cards'] != self.prev_state['hidden_cards']

        # Update previous state for the next comparison
        self.prev_state = current_state

        return progress_made

    def get_game_state(self):
        # Collect the current game state information
        foundation_count = [len(stack.cards) for stack in self.game.foundation]
        hidden_cards = set()
        for stack in self.game.t_stack:
            
            for card in stack.cards:
                if not card.visible:
                    hidden_cards.add((card.suit, card.number))
        return {'foundation_count': foundation_count, 'hidden_cards': hidden_cards}

    def render(self, mode='human'):
        if mode == 'human' or mode == 'ansi':
            self.game.show_cards()

    def close(self):
        pass

    def get_stack(self, idx):
        # Map index to the corresponding stack in the game
        if idx < 7:
            return str(idx+1)  # Tableau stacks 0-6
        elif idx == 7:
            return 'f'  # Foundation stacks 0-3
        elif idx == 8:
            return 'n'  # Next cards stack

    def get_observation(self):
        # Initialize the observation array
        observation = np.zeros((13, self.max_cards_per_stack), dtype=np.int8)

        for stack_idx, stack in enumerate(self.game.t_stack + self.game.foundation + [self.game.waste] + [self.game.next_cards]):
            for card_idx in range(self.max_cards_per_stack):
                if card_idx < len(stack.cards):
                    card = stack.cards[card_idx]
                    if card.visible:
                        observation[stack_idx, card_idx] = self.encode_card(card)
                    else:
                        observation[stack_idx, card_idx] = -1  # Hidden card
                else:
                    observation[stack_idx, card_idx] = 0  # Missing card

        return observation.flatten()

    def encode_card(self, card):
        if card is None:
            return 0  # Represent missing cards as 0
        suit_order = {'Hearts': 0, 'Diamonds': 13, 'Clubs': 26, 'Spades': 39}
        card_number = suit_order[card.suit] + card.number
        return card_number

    def decode_action(self, action):
        num_destinations = 8

        #if action == self.action_space.n - 1:
        #    source_stack = 9
        #    destination_stack = 1
        #    num_cards = 1
        #else:
        source_stack = action // (num_destinations * self.max_cards_per_move)
        action %= (num_destinations * self.max_cards_per_move)
        destination_stack = action // self.max_cards_per_move
        # Adding 1 because num_cards is 1-indexed
        num_cards = action % self.max_cards_per_move + 1

        return source_stack, destination_stack, num_cards

    def set_exploration_rate(self, rate):
        self.exploration_rate = rate