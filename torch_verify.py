import torch
import whisperx

# print("✅ whisperx version:", whisperx.__version__)
print("✅ load_diarization_model available:", hasattr(whisperx, "load_diarization_model"))

print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU name:", torch.cuda.get_device_name(0))
    print("Device count:", torch.cuda.device_count())
    print("Current device index:", torch.cuda.current_device())
else:
    print("No compatible GPU detected.")