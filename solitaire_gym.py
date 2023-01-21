import gym
from modules.cards import Solitaire

class SolitaireEnv(gym.Env):
    def __init__(self):
        self.game = Solitaire()
        self.action_space = gym.spaces.Box(low=0, high=len(self.game.t_stack + self.game.foundation), shape=(1,))
        self.observation_space = gym.spaces.Tuple((
            gym.spaces.Box(low=0, high=len(self.game.next_cards), shape=(1,)),
            gym.spaces.Box(low=0, high=len(self.game.t_stack + self.game.foundation), shape=(1,))
        ))

    def reset(self):
        self.game = Solitaire()
        return self._get_state()

    def step(self, action):
        if action < len(self.game.t_stack):
            stack = self.game.t_stack[action]
            card = stack.get_top_card()
        else:
            action_ = action - len(self.game.t_stack)
            if action_ < len(self.game.foundation):
                stack = self.game.foundation[action_]
                card = stack.get_top_card()
            else:
                raise ValueError(f'Invalid action: {action}')
                
        self.game.move_card(card, "F")
        return self._get_state()

    def _get_state(self):
        return (len(self.game.next_cards), len(self.game.t_stack + self.game.foundation))