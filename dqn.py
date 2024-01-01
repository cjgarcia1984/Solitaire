from stable_baselines3 import DQN
from stable_baselines3.dqn.policies import MlpPolicy
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

# Replace with the path to your SolitaireEnv
from modules.solitaire_env import SolitaireEnv
from modules.callback import ModelDataCallback
import yaml
# Create the environment
env = SolitaireEnv(config=yaml.safe_load(
    open("/home/chris/Solitaire/configs/config.yaml")))

# Check the environment (optional but recommended)
check_env(env, warn=True)

def make_env(config_path, instance):
    def _init():
        config = yaml.safe_load(open(config_path))
        config['env_instance'] = instance
        env = SolitaireEnv(config=config)
        return env
    return _init

def train_dqn_agent():
    num_envs = 4  # Number of parallel environments
    env_fns = [make_env("/home/chris/Solitaire/configs/config.yaml", i) for i in range(num_envs)]
    vec_env = DummyVecEnv(env_fns)  # or SubprocVecEnv(env_fns) for multiprocessing

    # Initialize the agent with the vectorized environment
    model = DQN(MlpPolicy, vec_env, verbose=1,
                learning_rate=0.0001,
                batch_size=16,
                learning_starts=50000,
                buffer_size=5000000,
                exploration_fraction=0.75,
                exploration_final_eps=0.01,
                target_update_interval=1000,
                )

    # Create the callback and pass the model to it
    callback = ModelDataCallback(model=model)

    # Train the agent
    print("Training the DQN agent...")
    model.learn(total_timesteps=50000000, callback=callback)
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
    model = train_dqn_agent()
    test_dqn_agent(model)
