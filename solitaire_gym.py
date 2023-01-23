import gym
from modules.solitaire import Solitaire
import numpy as np

class SolitaireEnv(gym.Env):
    def __init__(self):
        self.game = Solitaire()
        self.dest_action_space = gym.spaces.Discrete(len(self.game.t_stack) + 4)
        self.action_space = gym.spaces.Discrete(len(self.game.t_stack) + 4 + 2)
        self.observation_space = gym.spaces.Box(low=0, high=1, shape=(self.game.num_t_stack, 13, 4), dtype=np.uint8)

    def get_state(self):
        state = []
        # Extract information from next cards
        
        stack_state = [c.card_id() for c in self.game.next_cards.cards if c.visible]
        state.append(stack_state)
        # Extract information from t_stack
        for stack in self.game.t_stack:
            stack_state = [c.card_id() for c in stack.cards if c.visible]
            state.append(stack_state)
        # Extract information from foundation
        for stack in self.game.foundation:
            stack_state = [c.card_id() for c in stack.cards]
            state.append(stack_state)
        # Extract information from waste
        waste_state = [c.card_id() for c in self.game.waste.cards]
        state.append(waste_state)
        # Extract information from deck
        deck_state = len(self.game.deck.cards)
        state.append(deck_state)

        return state
    
    def step(self, action, dest_action=None):
        reward = 0
        done = False
        if action == len(self.game.t_stack) + 4 + 1:
            if self.game.deal_next_cards():
                self.game.show_cards()
                reward = 0.5
            else:
                print("Deck is empty.")
                return self.get_state(), 0, False, {}
        else:
            result = self.game.move_card(action, dest_action)
            if result[0]:
                if dest_action is None:
                    if self.game.status():
                        reward = 5
                        done = True
                    else:
                        reward = 1
                else:
                    reward = 1
            else:
                print(result[1])
        return self.get_state(), reward, done, {}

    def reset(self):
        self.game.deal_cards()
        return self.observation_space.sample()

    def render(self, mode='human', close=False):
        pass