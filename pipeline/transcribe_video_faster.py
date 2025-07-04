# File: pipeline/transcribe_video.py
import sys
import os
import subprocess
from pathlib import Path
import torch
import re
from faster_whisper import WhisperModel
import pyannote.audio

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

def transcribe_youtube_video(youtube_url, video_title="Unknown podkast", event_title="Unknown Event"):
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
        
        device = "cuda"
        compute_type = "float16"
        
        try:
            print("→ Starting transcription with Faster Whisper...")
            # Initialize Faster Whisper model
            whisper_model = WhisperModel(
                "large-v2", 
                device=device, 
                compute_type=compute_type
            )

            # Transcribe
            segments, info = whisper_model.transcribe(
                str(audio_path), 
                beam_size=5,
                language="en"
            )

            # Speaker Diarization with Pyannote
            print("→ Starting speaker diarization...")
            diarization = pyannote.audio.Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=HF_TOKEN
            )
            diarization_result = diarization(str(audio_path))

            # Combine transcription with diarization
            print("→ Combining transcription and diarization...")
            segments_with_speakers = []
            for segment in segments:
                # Find the speaker for this segment
                speaker = "Unknown"
                for turn, _, speaker_id in diarization_result.itertracks(yield_label=True):
                    if turn.start <= segment.start and segment.end <= turn.end:
                        speaker = speaker_id
                        break
                
                segments_with_speakers.append({
                    'text': segment.text,
                    'speaker': speaker
                })

            # Save transcript
            print("→ Saving transcript...")
            with open(output_file, "w", encoding="utf-8") as f:
                current_speaker = None
                current_text = []

                for segment in segments_with_speakers:
                    # Group text by speaker
                    if segment['speaker'] != current_speaker:
                        # Write previous speaker's text if exists
                        if current_speaker and current_text:
                            f.write(f"{current_speaker}: {' '.join(current_text).strip()}\n\n")
                        
                        # Reset for new speaker
                        current_speaker = segment['speaker']
                        current_text = [segment['text']]
                    else:
                        # Accumulate text for same speaker
                        current_text.append(segment['text'])

                # Write last speaker's text
                if current_speaker and current_text:
                    f.write(f"{current_speaker}: {' '.join(current_text).strip()}\n")

            print(f"✓ Transcript saved to {output_file}")
            return output_file

        except Exception as processing_error:
            print(f"❌ Error processing audio: {processing_error}")
            raise
        
        finally:
            # Always attempt to delete the audio file, whether processing succeeds or fails
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
        "East vs West 17"
    )