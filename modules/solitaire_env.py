import gymnasium
from gymnasium import spaces
from modules.solitaire import Solitaire

import numpy as np
import random
import csv
import pandas as pd
import os
import time


def exploration_rate(
    current_step, final_rate, exploration_fraction, learning_starts, total_timesteps
):
    """
    Compute the exploration rate (epsilon) for epsilon-greedy strategy.

    Args:
    current_step (int): The current training step.
    config (dict): Configuration dictionary containing exploration parameters.

    Returns:
    float: The exploration rate for the current step.
    """
    initial_rate = 1.0
    decay_steps = int(total_timesteps * exploration_fraction)

    # Ensure the decay is within the decay steps, starting after learning starts
    if current_step < learning_starts:
        return initial_rate

    decay_step = current_step - learning_starts
    rate = (
        initial_rate
        - (initial_rate - final_rate) * min(decay_step, decay_steps) / decay_steps
    )
    return max(final_rate, rate)


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
    metadata = {"render.modes": ["human", "ansi"]}
    total_steps = 0
    start_time = time.time()

    def __init__(self, config=None, instance=None):
        super(SolitaireEnv, self).__init__()
        # Initialize the Solitaire game
        self.config = config
        self.game = Solitaire(config=config)
        self.action_log = []

        self.num_source_stacks = 12
        self.num_destinations = 11  # 7 tableau stacks, 1 foundation stack
        # Maximum number of cards that can be moved at once
        self.max_cards_per_move = NUM_RANKS
        # Define action space (source_stack, destination_stack, num_cards)
        # 9 source stacks, 8 destination stacks, 1 card
        self.action_space = spaces.Discrete(
            self.num_source_stacks * self.num_destinations * self.max_cards_per_move + 1
        )

        # Number of steps with no progress to consider stagnation
        self.steps_since_progress = 0

        self.log_path = self.config.get("log_path")

        # Define observation space (using a simple representation for now)
        # For a more complex representation, you might need a multi-dimensional Box or a Dict space
        self.max_cards_per_stack = 24  # or any number that suits your game
        num_elements = NUM_RANKS * self.max_cards_per_stack  # 13 cards per stack
        self.observation_space = spaces.Box(
            low=-1, high=52, shape=(num_elements,), dtype=np.int32
        )

        self.current_seed = None
        self.prev_state = {"foundation_count": [0, 0, 0, 0], "hidden_cards": set()}

        self.current_episode = 0
        self.current_step = 0
        self.move_count = 0
        self.model_stats = {}
        self.games_completed = 0
        self.env_instance = instance

        self.time = time.time()

    def reset(self, seed=2, return_info=False, options=None):
        self.steps_since_progress = 0
        seed = next(number_gen)
        self.current_seed = seed
        config = self.config
        print(f"Successful moves: {self.move_count}")
        config.update({"random_seed": seed})
        self.game = Solitaire(config)
        print("New game started.")
        observation = self.get_observation()
        info = {}  # You can add additional reset info if needed
        self.current_episode += 1
        self.current_step = 0
        self.move_count = 0
        self.time = time.time()
        return observation, info

    def step(self, action):
        # Extract action details
        if isinstance(action, np.ndarray):
            action = int(action)
        source_idx, dest_idx, num_cards = self.decode_action(action)

        # Initialize reward
        reward = 0

        # Execute the action

        if source_idx == 12:  # Deal next cards action
            messages = self.game.deal_next_cards()
            self.steps_since_progress += 1
            deal = True
            move_result = False
        else:
            deal = False
            source_stack = self.get_stack(source_idx)
            dest_stack = self.get_stack(dest_idx)
            move_result, messages = self.game.execute_move(
                source_stack, dest_stack, num_cards=num_cards
            )

        reward = self.game.reward_points(messages)

        if move_result:
            self.move_count += 1
        if move_result and reward > 10:
            self.steps_since_progress = 0
        else:
            self.steps_since_progress += 1

        terminated = False
        if self.steps_since_progress >= self.config.get("env").get(
            "stagnation_threshold", 1000
        ):
            if self.steps_since_progress >= self.config.get("env").get(
                "max_steps_per_game", 100000
            ):
                terminated = True
                end_message = "Exceeded max steps."
            if not self.game.check_available_moves():
                terminated = True
                end_message = "No more moves available."

        # Get the observation and additional info
        observation = self.get_observation()
        info = {}
        self.current_step += 1
        SolitaireEnv.total_steps += 1

        if self.game.complete:
            self.games_completed += 1
            end_message = ["game_complete"]
            reward += self.game.reward_points(end_message)

        if terminated:
            print(f"Current seed: {self.current_seed}")
            self.game.show_score()
            self.game.show_cards()
            print(end_message)

        if SolitaireEnv.total_steps % self.config["env"].get("save_every") == 0:
            elapsed = time.time() - self.time
            total_elapsed = time.time() - SolitaireEnv.start_time
            self.save_log()
            print(
                f"Env {self.env_instance} Game:  Step {self.current_step}, Time Elapsed: {int(elapsed)}s ({self.current_step / elapsed:.0f} steps/s)"
            )
            print(
                f"Env {self.env_instance} Total:  Step {SolitaireEnv.total_steps}, Time Elapsed: {int(total_elapsed)}s ({SolitaireEnv.total_steps / total_elapsed:.0f} steps/s)"
            )
            self.game.show_cards()

        unadjusted_reward = reward
        reward = self.adjust_reward(reward)

        self.log_action(
            {
                "episode": self.current_episode,
                "step": self.current_step,
                "total_steps": SolitaireEnv.total_steps,
                "action": action,
                "source_stack": source_idx,
                "destination_stack": dest_idx,
                "num_cards": num_cards,
                "unadjusted_reward": unadjusted_reward,
                "reward": reward,
                "terminated": terminated,
                "exploration_rate": exploration_rate(
                    SolitaireEnv.total_steps,
                    self.config["dqn"]["model"]["exploration_final_eps"],
                    self.config["dqn"]["model"]["exploration_fraction"],
                    self.config["dqn"]["model"]["learning_starts"],
                    self.config["dqn"]["train"]["total_timesteps"],
                ),
                "return_message": messages,
                "move_count": self.move_count,
                "games_completed": self.games_completed,
                "env_instance": self.env_instance,
            }
        )

        return observation, reward, self.game.complete, terminated, info

    def adjust_reward(self, reward):
        if reward > 0:
            reward *= 1 + self.game.get_foundation_count() / 52
        return reward

    def render(self, mode="human"):
        if mode == "human" or mode == "ansi":
            self.game.show_cards()

    def close(self):
        pass

    def get_stack(self, idx):
        # Map index to the corresponding stack in the game
        if idx < 7:
            return str(idx + 1)  # Tableau stacks 0-6
        elif 6 < idx < 11:
            return f"f{idx+1-7}"  # Foundation stacks 0-3
        elif idx == 11:
            return "n"  # Next cards stack
        else:
            raise ValueError(f"Invalid stack index: {idx}")

    def get_observation(self):
        # Initialize the observation array
        observation = np.zeros((13, self.max_cards_per_stack), dtype=np.int8)

        for stack_idx, stack in enumerate(
            self.game.t_stack
            + list(self.game.foundation.values())
            + [self.game.waste]
            + [self.game.next_cards]
        ):
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
        suit_order = {"Hearts": 0, "Diamonds": 13, "Clubs": 26, "Spades": 39}
        card_number = suit_order[card.suit] + card.number
        return card_number

    def decode_action(self, action):
        num_destinations = 11
        if action == self.action_space.n - 1:
            source_stack = 12
            destination_stack = 1
            num_cards = 1
        source_stack = action // (num_destinations * self.max_cards_per_move)
        action %= num_destinations * self.max_cards_per_move
        destination_stack = action // self.max_cards_per_move
        # Adding 1 because num_cards is 1-indexed
        num_cards = action % self.max_cards_per_move + 1

        return source_stack, destination_stack, num_cards

    def log_action(self, log_row):
        self.action_log.append(log_row)

    def save_log(self):
        # Save the action log to a CSV file
        log_df = pd.DataFrame(self.action_log)
        full_log_path = f"{self.log_path}/{self.env_instance}_{log_df.loc[0,'total_steps']}_{log_df['step'].max()}.csv"
        os.makedirs(self.log_path, exist_ok=True)
        log_df.to_csv(
            full_log_path,
            index=False,
        )
        self.action_log = []
