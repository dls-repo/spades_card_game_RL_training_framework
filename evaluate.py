from sb3_contrib import MaskablePPO
from SpadesEnv import SpadesEnv

def mask_fn(env):
    return env._get_action_mask()

env = SpadesEnv()
model = MaskablePPO.load("spades_agent")

wins = 0
total = 100
total_reward = 0

for episode in range(total):
    obs, info = env.reset()
    done = False
    episode_reward = 0

    while not done:
        action_masks = info.get("action_mask")
        action, _ = model.predict(obs, action_masks=action_masks, deterministic=True)
        obs, reward, done, truncated, info = env.step(action)
        episode_reward += reward

    total_reward += episode_reward
    tricks = env.current_round.trick_counts[env.agent]
    bid = env.agent.bid
    print(f"Episode {episode + 1}: bid {bid}, won {tricks} tricks, reward {episode_reward:.1f}")
    if tricks == bid:
        wins += 1

print(f"\nHit bid: {wins}/{total} ({wins}% accuracy)")
print(f"Average reward: {total_reward/total:.2f}")
