import whisperx
import yt_dlp
import os
import gc
import unicodedata
import torch
from pydub import AudioSegment

# Ensure Torch DLL path is registered for CUDA/cuDNN
os.add_dll_directory(
    r"C:\Users\Rayman\Desktop\University\Master Dissertation\Programming\python 309_v2\venv\Lib\site-packages\torch\lib"
)

def slugify_filename(filename):
    name = unicodedata.normalize("NFKD", filename)
    name = name.encode("ascii", "ignore").decode("ascii")
    return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip().lower().replace(" ", "_")

def download_youtube_audio(url, output_path="./audio"):
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

    wav_files = [f for f in os.listdir(output_path) if f.endswith(".wav")]
    if not wav_files:
        raise FileNotFoundError("WAV file not found after download.")

    downloaded_file = os.path.join(output_path, wav_files[0])
    safe_name = slugify_filename(os.path.splitext(wav_files[0])[0])
    safe_file = os.path.join(output_path, f"{safe_name}.wav")

    if downloaded_file != safe_file:
        if os.path.exists(safe_file):
            os.remove(safe_file)
        os.rename(downloaded_file, safe_file)

    print(f"✅ WAV file saved: {safe_file}")
    return safe_file

def split_audio(audio_path, chunk_length_ms=10 * 60 * 1000):
    audio = AudioSegment.from_wav(audio_path)
    chunks = []
    basename = os.path.splitext(os.path.basename(audio_path))[0]
    out_dir = os.path.dirname(audio_path)

    for i, start in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk = audio[start:start + chunk_length_ms]
        chunk_path = os.path.join(out_dir, f"{basename}_part{i+1}.wav")
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    return chunks

def transcribe_with_diarization(audio_file, hf_token=None):
    device = "cuda"
    compute_type = "float16"
    language = "en"

    model = whisperx.load_model("large-v2", device, compute_type=compute_type, local_files_only=False)
    audio = whisperx.load_audio(audio_file)
    result = model.transcribe(audio, language=language, batch_size=4)
    del model
    gc.collect()

    if hf_token:
        try:
            diarize_model = whisperx.diarize.DiarizationPipeline(use_auth_token=hf_token, device=device)
            diarize_segments = diarize_model(audio, min_speakers=2, max_speakers=2)
            result = whisperx.assign_word_speakers(diarize_segments, result)
            del diarize_model
            gc.collect()
        except Exception as e:
            print(f"⚠️ Diarization failed: {e}")
    return result

def save_transcript(result, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        for seg in result["segments"]:
            start = seg.get('start', 0)
            end = seg.get('end', 0)
            text = seg.get('text', '').strip()
            speaker = seg.get('speaker', 'Unknown')
            f.write(f"[{start:.2f}s - {end:.2f}s] {speaker}: {text}\n")

def print_transcript_preview(result):
    print("\n" + "=" * 50)
    print("TRANSCRIPT PREVIEW")
    print("=" * 50)
    for i, seg in enumerate(result["segments"][:5]):
        print(f"[{seg['start']:.2f}s - {seg['end']:.2f}s] {seg.get('speaker', 'Unknown')}: {seg['text'].strip()}")
    if len(result["segments"]) > 5:
        print(f"... and {len(result['segments']) - 5} more segments")

if __name__ == "__main__":
    youtube_url = "https://www.youtube.com/watch?v=jFsV6FydeJc"
    hf_token = "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"

    try:
        print("🚀 Starting transcription pipeline")
        audio_file = download_youtube_audio(youtube_url)
        chunk_paths = split_audio(audio_file)

        all_segments = []
        for chunk in chunk_paths:
            print(f"\n🔹 Processing chunk: {chunk}")
            result = transcribe_with_diarization(chunk, hf_token)
            all_segments.extend(result["segments"])
            os.remove(chunk)

        final_result = {"segments": all_segments}
        output_path = "transcript.txt"
        save_transcript(final_result, output_path)
        print_transcript_preview(final_result)
        print(f"\n✅ All done. Transcript saved to {output_path}")
        os.remove(audio_file)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
