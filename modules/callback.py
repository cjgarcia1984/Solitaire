from stable_baselines3.common.callbacks import BaseCallback

class ModelDataCallback(BaseCallback):
    def __init__(self, model, debug=False, verbose=0):
        super(ModelDataCallback, self).__init__(verbose)
        self.model = model
        self.debug = debug

    def _on_step(self) -> bool:
        if self.debug:
            self.training_env.envs[0].unwrapped.model_stats['exploration_rate'] = self.model.exploration_rate
        else:
            self.training_env.unwrapped.model_stats['exploration_rate'] = self.model.exploration_rate
        return True
