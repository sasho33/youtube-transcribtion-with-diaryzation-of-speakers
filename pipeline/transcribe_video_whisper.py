# File: pipeline/transcribe_video.py
import sys
import os
import subprocess
from pathlib import Path
import torch
import whisper
import re
from pyannote.audio import Pipeline

# Dynamically add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import HF_TOKEN, AUDIO_DIR, TRANSCRIPT_DIR

def cleanup_audio_file(audio_path):
    """
    Safely delete the audio file
    """
    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"✓ Deleted audio file: {audio_path}")
    except Exception as e:
        print(f"❌ Error deleting audio file {audio_path}: {e}")

def transcribe_youtube_video(
    youtube_url, 
    video_title="Unknown podkast", 
    event_title="Unknown Event", 
    language="en",  # Configurable language
    batch_size=16   # Configurable batch size
):
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
        
        # Transcription Configuration
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        try:
            print(f"→ Starting transcription with Whisper (Language: {language}, Batch Size: {batch_size})...")
            # Load Whisper model
            model = whisper.load_model("large-v2", device=device)
            
            # Transcribe audio
            print("→ Transcribing audio...")
            result = model.transcribe(
                str(audio_path), 
                language=language,  # Use provided language 
                fp16=device == "cuda"
            )

            # Speaker Diarization with Pyannote
            print("→ Starting speaker diarization...")
            diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1", 
                use_auth_token=HF_TOKEN
            )

            # Perform diarization
            diarization = diarization_pipeline(str(audio_path))

            # Combine transcription with diarization
            print("→ Combining transcription and diarization...")
            # Group segments by speaker
            speaker_segments = {}
            for segment in result['segments']:
                segment_text = segment['text'].strip()
                
                # Find the speaker for this segment
                speaker = "Unknown"
                for turn, _, curr_speaker in diarization.itertracks(yield_label=True):
                    if turn.start <= segment['start'] <= turn.end:
                        speaker = curr_speaker
                        break

                # Group text by speaker
                if speaker not in speaker_segments:
                    speaker_segments[speaker] = []
                speaker_segments[speaker].append(segment_text)

            # Save transcript
            print("→ Saving transcript...")
            with open(output_file, "w", encoding="utf-8") as f:
                for speaker, texts in speaker_segments.items():
                    # Join texts into a single paragraph for each speaker
                    full_text = ' '.join(texts).strip()
                    f.write(f"{speaker}: {full_text}\n\n")

            print(f"✓ Transcript saved to {output_file}")
            return output_file

        except Exception as processing_error:
            print(f"❌ Error processing audio: {processing_error}")
            raise
        
        finally:
            # Always attempt to delete the audio file
            cleanup_audio_file(audio_path)

    except subprocess.CalledProcessError as download_error:
        print(f"❌ Audio download failed: {download_error}")
        cleanup_audio_file(audio_path)
        raise RuntimeError(f"yt-dlp failed: {download_error}")
    
    except Exception as general_error:
        print(f"❌ Unexpected error: {general_error}")
        cleanup_audio_file(audio_path)
        raise


if __name__ == "__main__":
    transcribe_youtube_video(
        "https://www.youtube.com/watch?v=jFsV6FydeJc", 
        "Cvetkov and Terzi", 
        "East vs West 17",
        language="en",     # Specify language
        batch_size=4      # Specify batch size
    )
    transcribe_youtube_video(
        "https://www.youtube.com/watch?v=jFsV6FydeJc", 
        "Cvetkov and Terzi", 
        "East vs West 17"
    )