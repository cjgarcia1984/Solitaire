import os
import yaml
from stable_baselines3 import DQN
from stable_baselines3.dqn.policies import MlpPolicy
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

from modules.solitaire_env import SolitaireEnv
from modules.callback import ModelDataCallback

def load_config(path):
    """ Load YAML configuration file. """
    with open(path, 'r') as file:
        return yaml.safe_load(file)

def make_env(config, instance=None):
    """ Environment factory that creates and wraps the environment with a Monitor. """
    env = SolitaireEnv(config=config)
    if instance is not None:
        log_path = os.path.join("/home/chris/Solitaire/logs", f"env_{instance}")
        env = Monitor(env, log_path)
    return env

def create_vector_env(config, num_envs):
    """ Create a vectorized environment for parallel training. """
    env_fns = [lambda i=i: make_env(config, instance=i) for i in range(num_envs)]
    return DummyVecEnv(env_fns)  # Replace with SubprocVecEnv for multiprocessing

def train_dqn_agent(vec_env, config):
    """ Train a DQN agent on the vectorized environment. """
    model = DQN(
        MlpPolicy,
        vec_env,
        verbose=2,
        **config['dqn']['model']  # Unpacking model-specific configuration
    )
    callback = ModelDataCallback(model=model)
    print("Training the DQN agent...")
    model.learn(total_timesteps=config['dqn']['train']['total_timesteps'], callback=callback)
    print("Training completed!")
    return model

def test_dqn_agent(model, env, config):
    """ Evaluate and test the trained agent. """
    mean_reward, std_reward = evaluate_policy(model, env, n_eval_episodes=config["dqn"]['test'].get("episodes", 10))
    print(f"Mean reward: {mean_reward}, std: {std_reward}")

    obs = env.reset()
    for _ in range(config["dqn"]['test'].get("steps", 10000)):
        action, _ = model.predict(obs, deterministic=True)
        obs, rewards, terminated, truncated, info = env.step(action)
        env.render()
        if terminated:
            obs = env.reset()

if __name__ == "__main__":
    config = load_config("/home/chris/Solitaire/configs/config.yaml")
    train_env = create_vector_env(config, num_envs=config['env'].get("num", 4))
    model = train_dqn_agent(train_env, config)

    os.makedirs("/home/chris/Solitaire/models", exist_ok=True)
    model_path = "/home/chris/Solitaire/models/dqn_solitaire"
    model.save(model_path)

    test_env = make_env(config, instance="test")  # Single environment for testing without a unique log path
    test_dqn_agent(model, test_env,config)
    print("Done!")
