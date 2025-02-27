# import os
# os.environ["KERAS_BACKEND"] = "tensorflow"
#
# import keras
# from keras import layers
#
# import gymnasium as gym
# from gymnasium.wrappers import AtariPreprocessing, FrameStack
# import numpy as np
# import tensorflow as tf
#
# # Configuration parameters for the whole setup
# seed = 42
# gamma = 0.99  # Discount factor for past rewards
# epsilon = 1.0  # Epsilon greedy parameter
# epsilon_min = 0.1  # Minimum epsilon greedy parameter
# epsilon_max = 1.0  # Maximum epsilon greedy parameter
# epsilon_interval = (
#     epsilon_max - epsilon_min
# )  # Rate at which to reduce chance of random action being taken
# batch_size = 32  # Size of batch taken from replay buffer
# max_steps_per_episode = 10000
# max_episodes = 10  # Limit training episodes, will run until solved if smaller than 1
#
# # Use the updated Atari environment
# # Specify the `render_mode` parameter to show the attempts of the agent in a pop up window.
# # Create the environment with no frame skipping
# env = gym.make("ALE/Breakout-v5", frameskip=1)
#
# # Apply the AtariPreprocessing wrapper
# env = AtariPreprocessing(env, frame_skip=4)  # Adjust the frame_skip parameter as needed
#
# # Stack four frames
# env = FrameStack(env, 4)
# env.seed(seed)
#
# num_actions = env.action_space.n  # Updated to get the number of actions dynamically
#
#
# def create_q_model():
#     # Network defined by the Deepmind paper
#     return keras.Sequential(
#         [
#             layers.Lambda(
#                 lambda tensor: keras.ops.transpose(tensor, [0, 2, 3, 1]),
#                 output_shape=(84, 84, 4),
#                 input_shape=(4, 84, 84),
#             ),
#             # Convolutions on the frames on the screen
#             layers.Conv2D(32, 8, strides=4, activation="relu", input_shape=(4, 84, 84)),
#             layers.Conv2D(64, 4, strides=2, activation="relu"),
#             layers.Conv2D(64, 3, strides=1, activation="relu"),
#             layers.Flatten(),
#             layers.Dense(512, activation="relu"),
#             layers.Dense(num_actions, activation="linear"),
#         ]
#     )
#
#
# # The first model makes the predictions for Q-values which are used to
# # make a action.
# model = create_q_model()
# # Build a target model for the prediction of future rewards.
# # The weights of a target model get updated every 10000 steps thus when the
# # loss between the Q-values is calculated the target Q-value is stable.
# model_target = create_q_model()
#
# # In the Deepmind paper they use RMSProp however then Adam optimizer
# # improves training time
# optimizer = keras.optimizers.Adam(learning_rate=0.00025, clipnorm=1.0)
#
# # Experience replay buffers
# action_history = []
# state_history = []
# state_next_history = []
# rewards_history = []
# done_history = []
# episode_reward_history = []
# running_reward = 0
# episode_count = 0
# frame_count = 0
# # Number of frames to take random action and observe output
# epsilon_random_frames = 50000
# # Number of frames for exploration
# epsilon_greedy_frames = 1000000.0
# # Maximum replay length
# # Note: The Deepmind paper suggests 1000000 however this causes memory issues
# max_memory_length = 100000
# # Train the model after 4 actions
# update_after_actions = 4
# # How often to update the target network
# update_target_network = 10000
# # Using huber loss for stability
# loss_function = keras.losses.Huber()
#
# while True:
#     observation, _ = env.reset()
#     state = np.array(observation)
#     episode_reward = 0
#
#     for timestep in range(1, max_steps_per_episode):
#         frame_count += 1
#
#         # Use epsilon-greedy for exploration
#         if frame_count < epsilon_random_frames or epsilon > np.random.rand(1)[0]:
#             # Take random action
#             action = np.random.choice(num_actions)
#         else:
#             # Predict action Q-values
#             # From environment state
#             state_tensor = keras.ops.convert_to_tensor(state)
#             state_tensor = keras.ops.expand_dims(state_tensor, 0)
#             action_probs = model(state_tensor, training=False)
#             # Take best action
#             action = keras.ops.argmax(action_probs[0]).numpy()
#
#         # Decay probability of taking random action
#         epsilon -= epsilon_interval / epsilon_greedy_frames
#         epsilon = max(epsilon, epsilon_min)
#
#         # Apply the sampled action in our environment
#         state_next, reward, done, _, _ = env.step(action)
#         state_next = np.array(state_next)
#
#         episode_reward += reward
#
#         # Save actions and states in replay buffer
#         action_history.append(action)
#         state_history.append(state)
#         state_next_history.append(state_next)
#         done_history.append(done)
#         rewards_history.append(reward)
#         state = state_next
#
#         # Update every fourth frame and once batch size is over 32
#         if frame_count % update_after_actions == 0 and len(done_history) > batch_size:
#             # Get indices of samples for replay buffers
#             indices = np.random.choice(range(len(done_history)), size=batch_size)
#
#             # Using list comprehension to sample from replay buffer
#             state_sample = np.array([state_history[i] for i in indices])
#             state_next_sample = np.array([state_next_history[i] for i in indices])
#             rewards_sample = [rewards_history[i] for i in indices]
#             action_sample = [action_history[i] for i in indices]
#             done_sample = keras.ops.convert_to_tensor(
#                 [float(done_history[i]) for i in indices]
#             )
#
#             # Build the updated Q-values for the sampled future states
#             # Use the target model for stability
#             future_rewards = model_target.predict(state_next_sample)
#             # Q value = reward + discount factor * expected future reward
#             updated_q_values = rewards_sample + gamma * keras.ops.amax(
#                 future_rewards, axis=1
#             )
#
#             # If final frame set the last value to -1
#             updated_q_values = updated_q_values * (1 - done_sample) - done_sample
#
#             # Create a mask so we only calculate loss on the updated Q-values
#             masks = keras.ops.one_hot(action_sample, num_actions)
#
#             with tf.GradientTape() as tape:
#                 # Train the model on the states and updated Q-values
#                 q_values = model(state_sample)
#
#                 # Apply the masks to the Q-values to get the Q-value for action taken
#                 q_action = keras.ops.sum(keras.ops.multiply(q_values, masks), axis=1)
#                 # Calculate loss between new Q-value and old Q-value
#                 loss = loss_function(updated_q_values, q_action)
#
#             # Backpropagation
#             grads = tape.gradient(loss, model.trainable_variables)
#             optimizer.apply_gradients(zip(grads, model.trainable_variables))
#
#         if frame_count % update_target_network == 0:
#             # update the the target network with new weights
#             model_target.set_weights(model.get_weights())
#             # Log details
#             template = "running reward: {:.2f} at episode {}, frame count {}"
#             print(template.format(running_reward, episode_count, frame_count))
#
#         # Limit the state and reward history
#         if len(rewards_history) > max_memory_length:
#             del rewards_history[:1]
#             del state_history[:1]
#             del state_next_history[:1]
#             del action_history[:1]
#             del done_history[:1]
#
#         if done:
#             break
#
#     # Update running reward to check condition for solving
#     episode_reward_history.append(episode_reward)
#     if len(episode_reward_history) > 100:
#         del episode_reward_history[:1]
#     running_reward = np.mean(episode_reward_history)
#
#     episode_count += 1
#
#     if running_reward > 40:  # Condition to consider the task solved
#         print("Solved at episode {}!".format(episode_count))
#         break
#
#     if (
#         max_episodes > 0 and episode_count >= max_episodes
#     ):  # Maximum number of episodes reached
#         print("Stopped at episode {}!".format(episode_count))
#         break


import os
os.environ["KERAS_BACKEND"] = "tensorflow"

import keras
from keras import layers
import gymnasium as gym
from gymnasium.wrappers import AtariPreprocessing, FrameStack
import numpy as np
import tensorflow as tf

# Configuration parameters for the whole setup
seed = 42
gamma = 0.99  # Discount factor for past rewards
epsilon = 1.0  # Epsilon greedy parameter
epsilon_min = 0.1  # Minimum epsilon greedy parameter
epsilon_max = 1.0  # Maximum epsilon greedy parameter
epsilon_interval = epsilon_max - epsilon_min  # Rate at which to reduce chance of random action being taken
batch_size = 32  # Size of batch taken from replay buffer
max_steps_per_episode = 10000
max_episodes = 10  # Limit training episodes, will run until solved if smaller than 1

# Create the environment with no frame skipping
env = gym.make("ALE/Breakout-v5", frameskip=1, render_mode = "human")

# Apply the AtariPreprocessing wrapper
env = AtariPreprocessing(env, frame_skip=4)

# Stack four frames
env = FrameStack(env, 4)
env.seed(seed)

num_actions = env.action_space.n  # Updated to get the number of actions dynamically

def create_q_model():
    # Network defined by the Deepmind paper
    return keras.Sequential([
        layers.Lambda(lambda tensor: keras.ops.transpose(tensor, [0, 2, 3, 1]), output_shape=(84, 84, 4), input_shape=(4, 84, 84)),
        layers.Conv2D(32, 8, strides=4, activation="relu"),
        layers.Conv2D(64, 4, strides=2, activation="relu"),
        layers.Conv2D(64, 3, strides=1, activation="relu"),
        layers.Flatten(),
        layers.Dense(512, activation="relu"),
        layers.Dense(num_actions, activation="linear"),
    ])

model = create_q_model()
model_target = create_q_model()

optimizer = keras.optimizers.Adam(learning_rate=0.00025, clipnorm=1.0)
loss_function = keras.losses.Huber()

# Experience replay buffers
action_history, state_history, state_next_history, rewards_history, done_history = [], [], [], [], []
episode_reward_history = []
running_reward = 0
episode_count = 0
frame_count = 0
epsilon_random_frames = 50000
epsilon_greedy_frames = 1000000.0
max_memory_length = 100000
update_after_actions = 4
update_target_network = 10000

while True:
    obs, _ = env.reset()  # Reset observation before the episode starts
    state = np.array(obs)
    episode_reward = 0

    for timestep in range(1, max_steps_per_episode):
        frame_count += 1

        # Use epsilon-greedy for exploration
        if frame_count < epsilon_random_frames or epsilon > np.random.rand(1)[0]:
            action = np.random.choice(num_actions)  # Random action
        else:
            state_tensor = keras.ops.convert_to_tensor(state)
            state_tensor = keras.ops.expand_dims(state_tensor, 0)
            action_probs = model(state_tensor, training=False)
            action = keras.ops.argmax(action_probs[0]).numpy()

        epsilon -= epsilon_interval / epsilon_greedy_frames
        epsilon = max(epsilon, epsilon_min)

        state_next, reward, done, truncated, _ = env.step(action)  # Use `done` and `truncated`
        state_next = np.array(state_next)
        episode_reward += reward

        action_history.append(action)
        state_history.append(state)
        state_next_history.append(state_next)
        done_history.append(done)
        rewards_history.append(reward)
        state = state_next

        # Update model after every `update_after_actions` actions
        if frame_count % update_after_actions == 0 and len(done_history) > batch_size:
            indices = np.random.choice(range(len(done_history)), size=batch_size)
            state_sample = np.array([state_history[i] for i in indices])
            state_next_sample = np.array([state_next_history[i] for i in indices])
            rewards_sample = [rewards_history[i] for i in indices]
            action_sample = [action_history[i] for i in indices]
            done_sample = keras.ops.convert_to_tensor([float(done_history[i]) for i in indices])

            future_rewards = model_target.predict(state_next_sample)
            updated_q_values = rewards_sample + gamma * keras.ops.amax(future_rewards, axis=1)
            updated_q_values = updated_q_values * (1 - done_sample) - done_sample

            masks = keras.ops.one_hot(action_sample, num_actions)
            with tf.GradientTape() as tape:
                q_values = model(state_sample)
                q_action = keras.ops.sum(keras.ops.multiply(q_values, masks), axis=1)
                loss = loss_function(updated_q_values, q_action)

            grads = tape.gradient(loss, model.trainable_variables)
            optimizer.apply_gradients(zip(grads, model.trainable_variables))

        if frame_count % update_target_network == 0:
            model_target.set_weights(model.get_weights())
            print(f"Running reward: {running_reward:.2f} at episode {episode_count}, frame count {frame_count}")

        if len(rewards_history) > max_memory_length:
            del rewards_history[:1], state_history[:1], state_next_history[:1], action_history[:1], done_history[:1]

        # Render the environment for visualization
        env.render()

        # Combine `done` and `truncated` signals for episode termination
        if done or truncated:
            obs, _ = env.reset()  # Reset if done
            break

    episode_reward_history.append(episode_reward)
    if len(episode_reward_history) > 100:
        del episode_reward_history[:1]
    running_reward = np.mean(episode_reward_history)

    episode_count += 1
    if running_reward > 40:  # Check if task is solved
        print(f"Solved at episode {episode_count}!")
        break

    if max_episodes > 0 and episode_count >= max_episodes:
        print(f"Stopped at episode {episode_count}!")
        break
