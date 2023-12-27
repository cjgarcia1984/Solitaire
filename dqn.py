from stable_baselines3 import DQN
from stable_baselines3.dqn.policies import MlpPolicy
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.evaluation import evaluate_policy
from modules.callback import ExplorationRateCallback
from modules.solitaire_env import SolitaireEnv  # Replace with the path to your SolitaireEnv
import yaml
# Create the environment
env = SolitaireEnv(config=yaml.safe_load(open("/home/chris/Solitaire/configs/config.yaml")))

# Check the environment (optional but recommended)
check_env(env, warn=True)

def train_dqn_agent():
    # Initialize the agent
    model = DQN(MlpPolicy, env, verbose=1, 
                learning_rate=0.001,
                batch_size=32,
                learning_starts=5000,
                buffer_size=1000000,
                exploration_fraction=0.5, 
                exploration_final_eps=0.01, 
                target_update_interval=1000,
                )

    # Create the callback and pass the model to it
    callback = ExplorationRateCallback(model=model)

    # Train the agent
    print("Training the DQN agent...")
    model.learn(total_timesteps=1000000, callback=callback)
    print("Training completed!")

    # Save the model (optional)
    model.save("dqn_solitaire")

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
