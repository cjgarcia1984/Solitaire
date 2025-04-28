import os
import yaml
from stable_baselines3 import DQN
from stable_baselines3.dqn.policies import MlpPolicy
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.logger import configure
from modules.callbacks import GPUMemoryCallback, CheckpointCallback

from modules.solitaire_env import SolitaireEnv
import shutil

import cProfile
import pstats


def load_config(path):
    """Load YAML configuration file."""
    with open(path, "r") as file:
        return yaml.safe_load(file)


def create_vector_env(config, num_envs):
    """Create a vectorized environment for parallel training."""
    env_fns = [lambda i=i: make_env(config, instance=i) for i in range(num_envs)]
    if config.get("debug"):
        envs = DummyVecEnv(env_fns)  # Replace with SubprocVecEnv for multiprocessing
    else:
        envs = SubprocVecEnv(env_fns)
    return envs


def make_env(config, instance=None):
    """Environment factory that creates and wraps the environment with a Monitor."""
    env = SolitaireEnv(config=config, instance=instance)
    if instance is not None:
        log_path = os.path.join("/home/chris/Solitaire/logs", f"env_{instance}")
        env = Monitor(env, log_path)
    return env


def train_dqn_agent(vec_env, config):
    log_path = config.get("tb_log_path", "/home/chris/Solitaire/tb_logs")
    new_logger = configure(log_path, ["stdout", "tensorboard"])

    model = DQN(
        policy=MlpPolicy,
        env=vec_env,
        verbose=3,
        tensorboard_log=log_path,
        **config["dqn"]["model"],
    )
    model.set_logger(new_logger)

    print(f"Model device: {model.policy.device}")

    # Instantiate your existing GPU callback
    gpu_callback = GPUMemoryCallback()

    # Instantiate your new Checkpoint callback
    checkpoint_callback = CheckpointCallback(
        save_freq=config["dqn"].get("save_interval",500_000),
        save_path="/home/chris/Solitaire/checkpoints",
        verbose=2,
    )

    # Combine callbacks
    from stable_baselines3.common.callbacks import CallbackList

    callback_list = CallbackList([gpu_callback, checkpoint_callback])

    # Train with both callbacks
    model.learn(
        total_timesteps=config["dqn"]["train"]["total_timesteps"] * vec_env.num_envs,
        tb_log_name="DQN_Solitaire",
        log_interval=config["dqn"]["train"].get("log_interval", 4),
        callback=callback_list,
    )

    print("Training completed!")
    return model


def test_dqn_agent(model, env, config):
    """Evaluate and test the trained agent."""
    mean_reward, std_reward = evaluate_policy(
        model, env, n_eval_episodes=config["dqn"]["test"].get("episodes", 10)
    )
    print(f"Mean reward: {mean_reward}, std: {std_reward}")
    obs, info = env.reset()
    for step in range(config["dqn"]["test"].get("steps", 10000)):
        action, _ = model.predict(obs, deterministic=True)
        obs, rewards, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            env.render()
            obs, _ = env.reset()


if __name__ == "__main__":
    config = load_config("/home/chris/Solitaire/configs/config.yaml")
    log_path = config.get("log_path", "/home/chris/Solitaire/logs")
    if config.get("clear_logs", False):
        shutil.rmtree(log_path, ignore_errors=True)
    os.makedirs(log_path, exist_ok=True)  # Ensure log directory exists
    train_env = create_vector_env(config, num_envs=config["env"].get("num", 4))

    profiler = cProfile.Profile()
    profiler.enable()

    model = train_dqn_agent(train_env, config)

    profiler.disable()

    # Save profiler stats to a file
    profiler.dump_stats("/home/chris/Solitaire/profiler_stats.prof")

    os.makedirs("/home/chris/Solitaire/models", exist_ok=True)
    model_path = "/home/chris/Solitaire/models/dqn_solitaire"
    model.save(model_path)

    test_env = make_env(
        config, instance="test"
    )  # Single environment for testing without a unique log path
    test_dqn_agent(model, test_env, config)
    print("Done!")
