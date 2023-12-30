from stable_baselines3.common.callbacks import BaseCallback

class ModelDataCallback(BaseCallback):
    def __init__(self, model, verbose=0):
        super(ModelDataCallback, self).__init__(verbose)
        self.model = model

    def _on_step(self) -> bool:
        self.training_env.envs[0].model_stats['exploration_rate'] = self.model.exploration_rate
        return True
