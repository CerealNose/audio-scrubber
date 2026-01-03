#!/usr/bin/env python3
import soundfile as sf
import sounddevice as sd
import numpy as np
import subprocess
import os
import sys
import time
import torch
from encodec import EncodecModel
from encodec.utils import convert_audio

# ─── CONFIG ───
VIRTUAL_DEVICE = os.getenv("VIRTUAL_DEVICE", "default")
TARGET_SR = 44100
TARGET_BITS = 24
CODEC_BITRATE = 12.0  # EnCodec bitrate in kbps (1.5, 3, 6, 12, 24)

# ─── 1. RE‑RECORD via loopback ───
def rerecord(input_mp3, output_wav):
    print(f"Re-recording {input_mp3} via loopback...")
    player = subprocess.Popen(
        ["ffmpeg", "-y", "-i", input_mp3, "-f", "f32le", "-ac", "2", "-ar", str(TARGET_SR), "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    
    try:
        with sf.SoundFile(output_wav, mode="w", samplerate=TARGET_SR, 
                          channels=2, subtype=f"PCM_{TARGET_BITS}") as f:
            with sd.InputStream(device=VIRTUAL_DEVICE, channels=2, 
                               samplerate=TARGET_SR, dtype="float32") as stream:
                time.sleep(0.1)
                while player.poll() is None:
                    data, overflow = stream.read(1024)
                    f.write(data)
                for _ in range(10):
                    data, _ = stream.read(1024, exception_on_overflow=False)
                    f.write(data)
    except Exception as e:
        print(f"Error during re-recording: {e}")
        print("Falling back to direct conversion for simulation...")
        subprocess.run(["ffmpeg", "-y", "-i", input_mp3, "-ar", str(TARGET_SR), "-ac", "2", output_wav], check=True)

# ─── 2. NEURAL CODEC SCRUB ───
def neural_scrub(input_wav, output_wav):
    print(f"Applying neural codec scrub to {input_wav}...")
    model = EncodecModel.encodec_model_48khz()
    model.set_target_bandwidth(CODEC_BITRATE)
    
    # Load audio using soundfile
    data, sr = sf.read(input_wav)
    # Convert to torch tensor [channels, samples]
    wav = torch.from_numpy(data).float()
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)
    else:
        wav = wav.transpose(0, 1)
    
    # Resample if necessary
    wav = convert_audio(wav, sr, model.sample_rate, model.channels)
    
    # Encode and decode
    with torch.no_grad():
        encoded_frames = model.encode(wav.unsqueeze(0))
        decoded_wav = model.decode(encoded_frames)
        
    # Convert back to numpy [samples, channels]
    out_data = decoded_wav.squeeze(0).transpose(0, 1).cpu().numpy()
    
    # Save output using soundfile
    sf.write(output_wav, out_data, model.sample_rate, subtype=f"PCM_{TARGET_BITS}")
    print(f"Neural scrub complete: {output_wav}")

# ─── MAIN ───
if __name__ == "__main__":
    import glob
    
    files = sys.argv[1:]
    if not files:
        files = glob.glob("*.mp3")
        
    if not files:
        print("No MP3 files found or provided.")
        sys.exit(1)

    for mp3 in files:
        if not mp3.lower().endswith(".mp3"):
            continue
            
        print(f"Processing {mp3}...")
        temp = mp3.replace(".mp3", "_rerecord.wav")
        final = mp3.replace(".mp3", "_clean.wav")
        
        rerecord(mp3, temp)
        if CODEC_BITRATE:
            try:
                neural_scrub(temp, final)
                if os.path.exists(temp):
                    os.remove(temp)
            except Exception as e:
                print(f"Neural scrub failed: {e}")
                if not os.path.exists(final):
                    os.rename(temp, final)
        else:
            os.rename(temp, final)
        print(f"Done! → {final}")
