from stable_baselines3.common.callbacks import BaseCallback
import torch
import psutil
import os

class GPUMemoryCallback(BaseCallback):
    def __init__(self, verbose=0):
        super(GPUMemoryCallback, self).__init__(verbose)

    def _on_step(self) -> bool:
        if torch.cuda.is_available():
            memory_allocated = torch.cuda.memory_allocated(0) / 1024 / 1024
            memory_reserved = torch.cuda.memory_reserved(0) / 1024 / 1024
            self.logger.record("gpu/memory_allocated_MB", memory_allocated)
            self.logger.record("gpu/memory_reserved_MB", memory_reserved)

        cpu_memory = psutil.virtual_memory().used / 1024 / 1024
        self.logger.record("cpu/memory_used_MB", cpu_memory)

        return True  # Always return True to continue training


class CheckpointCallback(BaseCallback):
    def __init__(self, save_freq: int, save_path: str, name_prefix: str = "dqn_checkpoint", verbose=0):
        super(CheckpointCallback, self).__init__(verbose)
        self.save_freq = save_freq
        self.save_path = save_path
        self.name_prefix = name_prefix

        os.makedirs(save_path, exist_ok=True)

    def _on_step(self) -> bool:
        if self.num_timesteps % self.save_freq == 0:
            checkpoint_file = os.path.join(
                self.save_path, f"{self.name_prefix}_{self.num_timesteps}_steps.zip"
            )
            self.model.save(checkpoint_file)
            if self.verbose > 0:
                print(f"Checkpoint saved to {checkpoint_file}")

        return True