import torch
import whisperx
import numpy as np


# print("✅ whisperx version:", whisperx.__version__)
print("✅ load_diarization_model available:", hasattr(whisperx, "load_diarization_model"))
print("NumPy version:", np.__version__)
print("CUDA version:", torch.version.cuda)

print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU name:", torch.cuda.get_device_name(0))
    print("Device count:", torch.cuda.device_count())
    print("Current device index:", torch.cuda.current_device())
else:
    print("No compatible GPU detected.")



    



