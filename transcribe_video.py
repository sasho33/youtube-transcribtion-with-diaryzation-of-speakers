import whisperx
import yt_dlp
import os
import gc
import unicodedata
import re
import glob
import os
import torch

os.add_dll_directory(
    r"C:\Users\Rayman\Desktop\University\Master Dissertation\Programming\python 309_v2\venv\Lib\site-packages\torch\lib"
)

def slugify_filename(filename):
    name = unicodedata.normalize("NFKD", filename)
    name = name.encode("ascii", "ignore").decode("ascii")
    return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip().lower().replace(" ", "_")

def download_youtube_audio(url, output_path="./audio"):
    """Download audio from YouTube video"""
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # 🔍 Find the downloaded .wav file
    wav_files = [f for f in os.listdir(output_path) if f.endswith(".wav")]
    if not wav_files:
        raise FileNotFoundError("WAV file not found after download.")

    downloaded_file = os.path.join(output_path, wav_files[0])
    print(f"✅ WAV file downloaded: {downloaded_file}")

    # 🧹 Normalize filename
    safe_name = slugify_filename(os.path.splitext(wav_files[0])[0])
    safe_file = os.path.join(output_path, f"{safe_name}.wav")

    if downloaded_file != safe_file:
        if os.path.exists(safe_file):
            os.remove(safe_file)
        os.rename(downloaded_file, safe_file)

    return safe_file


def transcribe_with_diarization(audio_file, hf_token=None):
    
    device = "cuda"
    batch_size = 4
    compute_type = "float16"
    language = "en"

    print("Loading Whisper model...")
    model = whisperx.load_model("large-v2", device, compute_type=compute_type, local_files_only=False)

    print("Loading audio...")
    audio = whisperx.load_audio(audio_file)

    print("Transcribing...")
    result = model.transcribe(audio, batch_size=batch_size, language="en")
    
    del model
    gc.collect()

    # print("Aligning transcription...")
    # model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    # result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

    # del model_a
    gc.collect()

    if hf_token:
        print("Performing speaker diarization...")
        try:
            diarize_model = whisperx.diarize.DiarizationPipeline(use_auth_token=hf_token, device=device)
            diarize_segments = diarize_model(audio, min_speakers=2, max_speakers=2)
            print(f"diarize_segments: {len(diarize_segments)} segments found, content: {diarize_segments[:5]}")
            result = whisperx.assign_word_speakers(diarize_segments, result)
            del diarize_model
            gc.collect()
            print("Diarization completed!")
        except Exception as e:
            print(f"Diarization failed: {e}")
            print("Continuing without speaker labels...")
    else:
        print("No HF token provided, skipping diarization...")

    return result

def save_transcript(result, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        for segment in result["segments"]:
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            text = segment.get('text', '').strip()
            speaker = segment.get('speaker', 'Unknown')
            f.write(f"[{start:.2f}s - {end:.2f}s] {speaker}: {text}\n")

def print_transcript_preview(result):
    print("\n" + "="*50)
    print("TRANSCRIPT PREVIEW")
    print("="*50)
    for i, segment in enumerate(result["segments"][:5]):
        start = segment.get('start', 0)
        end = segment.get('end', 0)
        text = segment.get('text', '').strip()
        speaker = segment.get('speaker', 'Unknown')
        print(f"[{start:.2f}s - {end:.2f}s] {speaker}: {text}")
    if len(result["segments"]) > 5:
        print(f"... and {len(result['segments']) - 5} more segments")

if __name__ == "__main__":
    youtube_url = "https://www.youtube.com/watch?v=jFsV6FydeJc"
    hf_token = "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"  # Or None to skip diarization

    try:
        print("Starting YouTube transcription...")
        print(f"URL: {youtube_url}")

        print("\n1. Downloading YouTube audio...")
        audio_file = download_youtube_audio(youtube_url)

        print("\n2. Starting transcription process...")
        result = transcribe_with_diarization(audio_file, hf_token)

        output_file = "transcript.txt"
        save_transcript(result, output_file)
        print(f"\n3. Transcript saved to: {output_file}")

        print_transcript_preview(result)
        print(f"\nTotal segments: {len(result['segments'])}")
        print("Transcription completed successfully!")
        os.remove(audio_file)

    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()