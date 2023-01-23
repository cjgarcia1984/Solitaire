import gym
from solitaire_gym import SolitaireEnv
import numpy as np
import tensorflow as tf

# Create the solitaire environment
solitaire_env = SolitaireEnv()

# Define the neural network
inputs = tf.keras.layers.Input(shape=solitaire_env.observation_space.shape)
hidden = tf.keras.layers.Dense(64, activation='relu')(inputs)
hidden = tf.keras.layers.Dense(64, activation='relu')(hidden)
logits = tf.keras.layers.Dense(solitaire_env.action_space.n)(hidden)
policy = tf.keras.layers.Softmax()(logits)
value = tf.keras.layers.Dense(1)(hidden)
model = tf.keras.Model(inputs=inputs, outputs=[policy, value])

# Define the optimizer
optimizer = tf.keras.optimizers.Adam()

# Define the loss function
def compute_loss(policy_logits, value, actions, rewards, next_value):
    cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=actions, logits=policy_logits)
    policy_loss = tf.reduce_sum(cross_entropy * rewards)
    value_loss = tf.reduce_sum((value - next_value) ** 2)
    entropy_loss = tf.reduce_sum(tf.nn.softmax(policy_logits) * tf.nn.log_softmax(policy_logits))
    total_loss = policy_loss + 0.5 * value_loss - 0.01 * entropy_loss
    return total_loss

# Keep track of the accumulated rewards
rewards = []

# Define the training loop
for episode in range(10000):
    # Reset the environment and get the initial state
    state = solitaire_env.reset()
    state = state.reshape(1, state.shape[0], state.shape[1], state.shape[2])
    # Set up variables to track the episode's progress
    done = False
    episode_rewards = []
    episode_actions = []
    episode_states = []

    # Run the episode
    while not done:
        # Use the neural network to predict the next action and value
        policy_logits, value = model(state)
        policy_logits = tf.reshape(policy_logits, [-1, solitaire_env.action_space.n])
        policy = tf.nn.softmax(policy_logits)
        action = tf.random.categorical(policy_logits, num_samples=1, dtype=tf.int32)
        dest_action = solitaire_env.dest_action_space.sample() # Select a destination for the move
        num_cards = solitaire_env.num_cards_space.sample()

        # Take the action and observe the new state and reward
        next_state, reward, done, _ = solitaire_env.step(action, dest_action,num_cards)
        episode_rewards.append(reward)
        episode_actions.append(action)
        episode_states.append(state)

        # Use the new state and reward to update the neural network
        with tf.GradientTape() as tape:
            next_policy_logits, next_value = model(np.array([next_state]))
            next_value = next_value[0][0]
            if done:
                next_value = 0
            total_loss = compute_loss(policy_logits, value[0][0], np.array(episode_actions), np.array(episode_rewards), next_value)
        grads = tape.gradient(total_loss, model.trainable_variables)
        optimizer.apply_gradients(zip(grads, model.trainable_variables))

        # Update the state
        state = next_state

    # Record the episode's rewards
    rewards.append(sum(episode_rewards))

    # Print some information about the training progress
    if episode % 100 == 0:
        print(f'Episode {episode}, mean rewards {np.mean(rewards[-100:])}')