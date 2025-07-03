import torch
import sys
from pathlib import Path
import whisperx
# Dynamically add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import HF_TOKEN, AUDIO_DIR
from pathlib import Path

AUDIO_FILE = AUDIO_DIR / "your_audio_file.wav"  # replace with an existing audio file

def check_whisperx_models():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"✓ Using device: {device}")

    compute_type = "float16"
    language = "en"

    print("→ Loading WhisperX model...")
    model = whisperx.load_model("large-v2", device, compute_type=compute_type, language=language)
    print("✓ WhisperX model loaded")

    print("→ Transcribing audio...")
    result = model.transcribe(str(AUDIO_FILE))
    print(f"✓ Transcription complete. Found {len(result['segments'])} segments.")

    print("→ Loading diarization pipeline...")
    diarize_model = whisperx.diarize.DiarizationPipeline(
        use_auth_token=HF_TOKEN,
        device=device
    )
    print("✓ Diarization pipeline loaded")

    print("→ Running diarization...")
    diarize_segments = diarize_model(str(AUDIO_FILE))
    print(f"✓ Diarization complete. Found {len(diarize_segments)} speaker segments.")

    print("→ Merging speakers with words...")
    result = whisperx.assign_word_speakers(diarize_segments, result)

    print("→ Sample output:")
    for seg in result["segments"][:5]:
        print(f"{seg.get('speaker', 'Speaker')}: {seg['text']}")

    print("\n✓ Diagnostic complete.")

if __name__ == "__main__":
    check_whisperx_models()