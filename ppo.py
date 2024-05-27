from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.evaluation import evaluate_policy

from modules.solitaire_env import SolitaireEnv


def train_agent():
    # Create the environment
    env = SolitaireEnv()

    # Check the environment (optional but recommended)
    check_env(env, warn=True)

    # Initialize the agent
    model = PPO("MlpPolicy", env, verbose=1)

    # Train the agent
    print("Training the agent...")
    model.learn(total_timesteps=100000)
    print("Training completed!")

    # Save the model (optional)
    model.save("ppo_solitaire")

    return model


def test_agent(model):
    # Create the environment
    env = SolitaireEnv()

    # Evaluate the agent
    mean_reward, std_reward = evaluate_policy(model, env, n_eval_episodes=10)
    print(f"Mean reward: {mean_reward}, std: {std_reward}")

    # Test the agent
    obs, info = env.reset()
    total_reward = 0
    for _ in range(10000):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        total_reward += reward  # Accumulate the reward
        env.render()
        if done:
            print(f"Total reward for this episode: {total_reward}")
            total_reward = 0  # Reset the total reward for the next episode
            obs = env.reset()


if __name__ == "__main__":
    model = train_agent()
    test_agent(model)
