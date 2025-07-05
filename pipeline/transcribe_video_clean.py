import sys
import os
import subprocess
from pathlib import Path
import torch
import whisperx
import re
import gc

# Dynamically add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from pipeline.config import HF_TOKEN, AUDIO_DIR, TRANSCRIPT_DIR

def cleanup_gpu_memory():
    """
    Explicitly clear GPU memory
    """
    try:
        # Clear PyTorch cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        
        # Force Python garbage collection
        gc.collect()
        
        print("→ GPU memory cleaned up")
    except Exception as e:
        print(f"❌ Error cleaning up GPU memory: {e}")

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
    # Cleanup any previous GPU memory usage before starting
    cleanup_gpu_memory()

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
        
        hf_token = HF_TOKEN
        print("→ Using Hugging Face token:", hf_token)

        device = "cuda"
        batch_size = 12
        compute_type = "float16"
        language = "en"
        
        try:
            print("→ Starting transcription with WhisperX...")
            model = None
            diarize_model = None
            
            try:
                # Load Whisper model
                model = whisperx.load_model("large-v3", device, compute_type=compute_type, language=language)
                
                # Transcribe
                result = model.transcribe(str(audio_path), batch_size=batch_size)

                print("→ Starting diarization...")
                diarize_model = whisperx.diarize.DiarizationPipeline(
                    model_name="pyannote/speaker-diarization-3.1", 
                    use_auth_token=hf_token, 
                    device=device, 
                    
                )
                diarize_segments = diarize_model(str(audio_path), min_speakers=2, max_speakers=5)
                result = whisperx.assign_word_speakers(diarize_segments, result)

                print("→ Saving transcript...")
                with open(output_file, "w", encoding="utf-8") as f:
                    for segment in result["segments"]:
                        speaker = segment.get("speaker", "Speaker")
                        text = segment.get("text", "")
                        f.write(f"{speaker}: {text.strip()}\n")

                print(f"✓ Transcript saved to {output_file}")
                return output_file

            except Exception as processing_error:
                print(f"❌ Error processing audio: {processing_error}")
                raise
            
            finally:
                # Explicitly delete models and clear references
                if model:
                    del model
                if diarize_model:
                    del diarize_model

        except subprocess.CalledProcessError as download_error:
            print(f"❌ Audio download failed: {download_error}")
            raise RuntimeError(f"yt-dlp failed: {download_error}")
        
        finally:
            # Always attempt to delete the audio file
            cleanup_audio_file(audio_path)
            
            # Clean up GPU memory after processing
            cleanup_gpu_memory()

    except Exception as general_error:
        print(f"❌ Unexpected error: {general_error}")
        cleanup_audio_file(audio_path)
        cleanup_gpu_memory()
        raise


if __name__ == "__main__":
    transcribe_youtube_video(
        "https://www.youtube.com/watch?v=jFsV6FydeJc", 
        "Cvetkov and Terzi", 
        "East vs West 17"
    )