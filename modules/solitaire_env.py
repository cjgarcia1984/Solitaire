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
        self.config = config
        self.game = Solitaire(config=config)
        self.action_log_file = self.config.get("env").get(
            'action_log_file', 'action_log.csv')
        with open(self.action_log_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['total_episode_count', 'episode', 'step', 'action', 'source_stack',
                            'destination_stack', 'num_cards', 'reward', 'terminated', 'exploration_rate', 'return_message', 'move_count', 'games_completed'])

        self.num_source_stacks = 9
        self.num_destinations = 8  # 7 tableau stacks, 1 foundation stack
        # Maximum number of cards that can be moved at once
        self.max_cards_per_move = NUM_RANKS
        # Define action space (source_stack, destination_stack, num_cards)
        # 9 source stacks, 8 destination stacks, 1 card
        self.action_space = spaces.Discrete(
            self.num_source_stacks * self.num_destinations * self.max_cards_per_move + 1)
        self.action_repeat_threshold = 2

        # Number of steps with no progress to consider stagnation

        self.steps_since_progress = 0

        # Define observation space (using a simple representation for now)
        # For a more complex representation, you might need a multi-dimensional Box or a Dict space
        self.max_cards_per_stack = 24  # or any number that suits your game
        num_elements = NUM_RANKS * self.max_cards_per_stack  # 13 cards per stack
        self.observation_space = spaces.Box(
            low=-1, high=52, shape=(num_elements,), dtype=np.int32)

        self.current_seed = None
        self.prev_state = {
            'foundation_count': [0, 0, 0, 0],
            'hidden_cards': set()
        }

        self.current_episode = 0
        self.total_episodes_count = 0
        self.current_step = 0
        self.move_count = 0
        self.model_stats = {}
        self.no_moves = []
        self.games_completed = 0

    def reset(self, seed=2, return_info=False, options=None):
        self.steps_since_progress = 0
        seed = next(number_gen)
        self.current_seed = seed
        config = self.config
        print(f"Successful moves: {self.move_count}")
        config.update({'random_seed': seed})
        self.game = Solitaire(config)
        print("New game started.")
        self.no_moves = []
        observation = self.get_observation()
        info = {}  # You can add additional reset info if needed
        self.current_episode += 1
        self.current_step = 0
        
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

        # Execute the action

        if source_idx == 9:  # Deal next cards action
            messages = self.game.deal_next_cards()
            self.steps_since_progress += 1
            deal = True
            move_result = False
        else:
            deal = False
            source_stack = self.get_stack(source_idx)
            dest_stack = self.get_stack(dest_idx)
            move_result, messages = self.game.execute_move(
                source_stack, dest_stack, num_cards=num_cards)

        reward = self.game.reward_points(messages)

        if move_result:
            self.move_count += 1
        if move_result and reward > 10:
            self.steps_since_progress = 0
        else:
            self.steps_since_progress += 1

        
        # Check for game stagnation
        terminated = self.game.complete

        if self.steps_since_progress >= self.config.get("env").get('stagnation_threshold', 1000):
            moves = False
            if deal:
                if not moves:
                    if not self.game.check_available_moves():
                        moves = False
                        if self.game.next_cards.cards:
                            if self.no_moves.count(self.game.next_cards.cards[-1]) > 2:
                                terminated = True
                                end_message = "No more moves available. Cards remain in deck."
                        else:
                            if not self.game.deck.cards and not self.game.waste.cards:
                                terminated = True
                                end_message = "No more moves available. Deck and waste are empty."
                        self.no_moves.append(self.game.next_cards.cards[-1])
                    else:
                        moves = True
                        self.no_moves = []
        else:
            self.no_moves = []

        # Get the observation and additional info
        observation = self.get_observation()
        truncated = False
        info = {}
        self.current_step += 1
        self.total_episodes_count += 1

        self.log_action([self.total_episodes_count, self.current_episode, self.current_step, action,
                        source_idx, dest_idx, num_cards, reward, terminated, self.model_stats.get('exploration_rate', 0), messages, self.move_count, self.games_completed])

        
        if self.game.complete:
            terminated = True
            self.games_completed += 1
            end_message = "game_complete"
            reward += self.game.reward_points(end_message)
            

        if terminated:
            print(f"Current seed: {self.current_seed}")
            self.game.show_score()
            self.game.show_cards()
            print(end_message)

        return observation, reward, terminated, truncated, info

    def log_action(self, log_data):
        with open(self.action_log_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(log_data)

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

        for stack_idx, stack in enumerate(self.game.t_stack + list(self.game.foundation.values()) + [self.game.waste] + [self.game.next_cards]):
            for card_idx in range(self.max_cards_per_stack):
                if card_idx < len(stack.cards):
                    card = stack.cards[card_idx]
                    if card.visible:
                        observation[stack_idx,
                                    card_idx] = self.encode_card(card)
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

        # if action == self.action_space.n - 1:
        #    source_stack = 9
        #    destination_stack = 1
        #    num_cards = 1
        # else:
        if action == self.action_space.n - 1:
            source_stack = 9
            destination_stack = 1
            num_cards = 1
        source_stack = action // (num_destinations * self.max_cards_per_move)
        action %= (num_destinations * self.max_cards_per_move)
        destination_stack = action // self.max_cards_per_move
        # Adding 1 because num_cards is 1-indexed
        num_cards = action % self.max_cards_per_move + 1

        return source_stack, destination_stack, num_cards

    def set_exploration_rate(self, rate):
        self.exploration_rate = rate
