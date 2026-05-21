from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from SpadesEnv import SpadesEnv


def mask_fn(env):
    return env._get_action_mask()


def main():
    env = SpadesEnv()
    env = ActionMasker(env, mask_fn)

    model = MaskablePPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
    )

    print("Starting training...")
    model.learn(total_timesteps=1_000_000)
    model.save("spades_agent")
    print("Training complete — model saved to spades_agent.zip")


if __name__ == "__main__":
    main()
