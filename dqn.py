from stable_baselines3 import DQN
from stable_baselines3.dqn.policies import MlpPolicy
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from stable_baselines3.common.monitor import Monitor

import os

# Replace with the path to your SolitaireEnv
from modules.solitaire_env import SolitaireEnv
from modules.callback import ModelDataCallback
import yaml

# Create the environment
env = SolitaireEnv(
    config=yaml.safe_load(open("/home/chris/Solitaire/configs/config.yaml"))
)

# Check the environment (optional but recommended)
check_env(env, warn=True)


def make_env(config, instance):
    def _init():

        config["env_instance"] = instance
        env = SolitaireEnv(config=config)
        # Wrap the environment with the Monitor wrapper
        env = Monitor(env, f"/home/chris/Solitaire/logs/env_{instance}")
        return env

    return _init


def train_dqn_agent():
    num_envs = 4  # Number of parallel environments
    config = yaml.safe_load(open("/home/chris/Solitaire/configs/config.yaml"))
    env_fns = [
        make_env(config, i)
        for i in range(num_envs)
    ]
    # or SubprocVecEnv(env_fns) for multiprocessing
    vec_env = DummyVecEnv(env_fns)

    # Initialize the agent with the vectorized environment
    model = DQN(
        MlpPolicy,
        vec_env,
        verbose=2,
        learning_rate=config["dqn"].get("learning_rate", 0.001),
        batch_size=config["dqn"].get("batch_size", 32),
        learning_starts=config["dqn"].get("learning_starts", 1000),
        buffer_size=config["dqn"].get("buffer_size", 10000),
        exploration_fraction=config["dqn"].get("exploration_fraction", 0.1),
        exploration_final_eps=config["dqn"].get("exploration_final_eps", 0.02),
        target_update_interval=config["dqn"].get("target_update_interval", 500),
    )

    # Create the callback and pass the model to it
    callback = ModelDataCallback(model=model)

    # Train the agent
    print("Training the DQN agent...")
    model.learn(total_timesteps=config["dqn"].get("total_timesteps", 50000), callback=callback)
    print("Training completed!")

    return model


def test_dqn_agent(model):
    # Evaluate the agent
    mean_reward, std_reward = evaluate_policy(model, env, n_eval_episodes=10)
    print(f"Mean reward: {mean_reward}, std: {std_reward}")

    # Test the agent
    obs, info = env.reset()
    for _ in range(10000):
        action, _states = model.predict(obs, deterministic=True)
        obs, rewards, terminated, truncated, info = env.step(action)
        env.render()
        if terminated:
            obs, info = env.reset()


if __name__ == "__main__":
    # Train the agent
    model = train_dqn_agent()
    # Save the agent
    os.makedirs("/home/chris/Solitaire/models", exist_ok=True)
    model.save("/home/chris/Solitaire/models/dqn_solitaire")
    # Test the agent
    test_dqn_agent(model)
    print("Done!")
