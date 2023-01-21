import gym
from solitaire_gym import SolitaireEnv

solitaire_env = SolitaireEnv()
state = solitaire_env.reset()
done = False
while not done:
    action = int(input("Enter the number of the stack you want to move a card from: "))
    state, reward, done, _ = solitaire_env.step(action)
    print(f"Current state: {state}")
print("Game complete!")