from stable_baselines3.common.callbacks import BaseCallback

class ExplorationRateCallback(BaseCallback):
    def __init__(self, model, verbose=0):
        super(ExplorationRateCallback, self).__init__(verbose)
        self.model = model

    def _on_step(self) -> bool:
        # Compute the exploration rate just before the next step
        total_timesteps = self.model.num_timesteps + 1  # anticipating the next step
        exploration_fraction = self.model.exploration_fraction
        initial_eps = 1.0
        final_eps = self.model.exploration_final_eps
        fraction = min(float(total_timesteps) / (exploration_fraction * self.model._total_timesteps), 1.0)
        current_eps = initial_eps + fraction * (final_eps - initial_eps)

        # Set the exploration rate in the environment
        self.training_env.envs[0].set_exploration_rate(current_eps)

        return True
