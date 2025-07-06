from pyannote.audio import Pipeline as PyannotePipeline
from pyannote.core import Segment
import torch
import whisper_s2t
import gc
import os
import re
import subprocess
from pathlib import Path
import sys

# Append project root and import config
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import HF_TOKEN, AUDIO_DIR, TRANSCRIPT_DIR

def cleanup_gpu_memory():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    gc.collect()
    print("→ GPU memory cleaned up")

def cleanup_audio_file(audio_path):
    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"✓ Deleted audio file: {audio_path}")
    except Exception as e:
        print(f"❌ Error deleting audio file {audio_path}: {e}")

def transcribe_youtube_video(youtube_url, video_title="Unknown podkast", event_title="Unknown Event"):
    cleanup_gpu_memory()
    safe_title = re.sub(r'[^\w\-_\. ]', '_', video_title).strip()

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = AUDIO_DIR / f"{safe_title}.wav"

    transcript_dir = TRANSCRIPT_DIR / event_title
    transcript_dir.mkdir(parents=True, exist_ok=True)
    output_file = transcript_dir / f"{safe_title}.txt"

    if output_file.exists():
        print(f"✓ Transcript already exists: {output_file}")
        return None

    try:
        print("→ Downloading audio...")
        subprocess.run([
            "yt-dlp", "-x", "--audio-format", "wav",
            "--audio-quality", "0",
            "--postprocessor-args", "-ar 16000 -ac 1",
            "--output", str(audio_path),
            youtube_url
        ], check=True)

        print("→ Transcribing with WhisperS2T...")
        model = whisper_s2t.load_model(
            model_identifier="large-v3",
            backend="CTranslate2",
            device="cuda",
            compute_type="float16",
            asr_options={
                "beam_size": 5,
                "best_of": 5,
                "language": "en",
                "task": "transcribe",
                "word_timestamps": True,
                "condition_on_previous_text": False
            }
        )
        out = model.transcribe_with_vad(
            [str(audio_path)],
            lang_codes=["en"],
            tasks=["transcribe"],
            initial_prompts=[None],
            batch_size=12
        )[0]  # first file result

        print("→ Running speaker diarization with pyannote...")
        diarizer = PyannotePipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=HF_TOKEN
        )
        diarization = diarizer(str(audio_path))

        print("→ Assigning speakers...")
        speaker_segments = list(diarization.itertracks(yield_label=True))

        with open(output_file, "w", encoding="utf-8") as f:
            for segment in out:
                start = segment['start']
                end = segment['end']
                text = segment['text'].strip()

                # Find speaker for current segment
                speaker = "Unknown"
                for speech_segment, _, label in speaker_segments:
                    if speech_segment.start <= start <= speech_segment.end:
                        speaker = label
                        break

                f.write(f"{speaker}: {text}\n")

        print(f"✓ Transcript with speakers saved: {output_file}")
        return output_file

    except Exception as e:
        print(f"❌ Error: {e}")
        raise

    finally:
        cleanup_audio_file(audio_path)
        cleanup_gpu_memory()

if __name__ == "__main__":
    transcribe_youtube_video(
        "https://www.youtube.com/watch?v=jFsV6FydeJc",
        "Cvetkov and Terzi",
        "East vs West 17"
    )
