import sys
import numpy as np
import torch
import whisperx

print("Python version:", sys.version)
print("NumPy version:", np.__version__)
print("PyTorch version:", torch.__version__)
print("WhisperX version:", whisperx.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA version:", torch.version.cuda)