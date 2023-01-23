import gym
from solitaire_gym import SolitaireEnv
import random

solitaire_env = SolitaireEnv()
state = solitaire_env.reset()
done = False



results = []
for _ in range(10000):
    #try:
    rewards = []
    solitaire_env.game.deal_next_cards()
    while not done:
        action = solitaire_env.action_space.sample()
        dest_action = solitaire_env.dest_action_space.sample() # Select a destination for the move
        if (action == 12):
            x=1
        state, reward, done, _ = solitaire_env.step(action, dest_action)
        rewards.append(reward)
        print(f"Current state: {state}")
        print(f"Current reward: {reward}")
        if reward > 0.5:
            pass
        window=50000
        if len(rewards)>window:
            if max(rewards[:-window])<=0.5:
                break
    if done:
        results.append(True)
        print("Game complete!")
    else:
        results.append(False)
        print("Game could not be completed.")
    #except Exception as e:
    #    results.append(e)

print(results)