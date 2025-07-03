# File: pipeline/transcribe_video.py
import sys
import os
import subprocess
from pathlib import Path
import torch
import whisperx
import re

# Dynamically add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import HF_TOKEN, AUDIO_DIR, TRANSCRIPT_DIR


def transcribe_youtube_video(youtube_url, video_title = "Unknown podkast", event_title="Unknown Event"):
    safe_title = re.sub(r'[^\w\-_\. ]', '_', video_title).strip()

    # Prepare audio and transcript paths
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = AUDIO_DIR / f"{safe_title}.wav"

    transcript_dir = TRANSCRIPT_DIR / event_title
    transcript_dir.mkdir(parents=True, exist_ok=True)
    output_file = transcript_dir / f"{safe_title}.txt"

    if output_file.exists():
        print(f"✓ Transcript already exists: {output_file}")
        return None  # Skip processing to continue loop outside

    try:
        print("→ Downloading audio with yt-dlp...")
        subprocess.run([
            "yt-dlp", "-x", "--audio-format", "wav",
            "--output", str(audio_path),
            youtube_url
        ], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"yt-dlp failed: {e}")
    
    
    
    
    hf_token = HF_TOKEN
    print("→ Using Hugging Face token:", hf_token)

    device = "cuda"
    batch_size = 4
    compute_type = "float16"
    language = "en"
    

    print("→ Starting transcription with WhisperX...")
    model = whisperx.load_model("large-v2", device, compute_type=compute_type, language=language)
    result = model.transcribe(str(audio_path), batch_size=batch_size)

    print("→ Starting diarization...")
    diarize_model = whisperx.diarize.DiarizationPipeline(use_auth_token=hf_token, device=device)
    diarize_segments = diarize_model(str(audio_path))
    result = whisperx.assign_word_speakers(diarize_segments, result)

    print("→ Saving transcript...")
    with open(output_file, "w", encoding="utf-8") as f:
        for segment in result["segments"]:
            speaker = segment.get("speaker", "Speaker")
            text = segment.get("text", "")
            f.write(f"{speaker}: {text.strip()}\n")

    print(f"✓ Transcript saved to {output_file}")
    return output_file


if __name__ == "__main__":
    
    transcribe_youtube_video("https://www.youtube.com/watch?v=jFsV6FydeJc", "Cvetkov and Terzi", "East vs West 17")
