#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import sys
import subprocess
import soundfile as sf
import sounddevice as sd
import torch
from encodec import EncodecModel
from encodec.utils import convert_audio

# ─── CORE LOGIC (Adapted for GUI) ───

def rerecord(input_mp3, output_wav, device_name, status_callback):
    status_callback(f"Re-recording {os.path.basename(input_mp3)}...")
    target_sr = 44100
    target_bits = 24
    
    player = subprocess.Popen(
        ["ffmpeg", "-y", "-i", input_mp3, "-f", "f32le", "-ac", "2", "-ar", str(target_sr), "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    
    try:
        with sf.SoundFile(output_wav, mode="w", samplerate=target_sr, 
                          channels=2, subtype=f"PCM_{target_bits}") as f:
            with sd.InputStream(device=device_name, channels=2, 
                               samplerate=target_sr, dtype="float32") as stream:
                import time
                time.sleep(0.1)
                while player.poll() is None:
                    data, overflow = stream.read(1024)
                    f.write(data)
                for _ in range(10):
                    data, _ = stream.read(1024, exception_on_overflow=False)
                    f.write(data)
    except Exception as e:
        status_callback(f"Loopback failed, falling back to direct conversion...")
        subprocess.run(["ffmpeg", "-y", "-i", input_mp3, "-ar", str(target_sr), "-ac", "2", output_wav], check=True)

def neural_scrub(input_wav, output_wav, bitrate, status_callback):
    status_callback(f"Neural scrubbing {os.path.basename(input_wav)}...")
    model = EncodecModel.encodec_model_48khz()
    model.set_target_bandwidth(float(bitrate))
    
    data, sr = sf.read(input_wav)
    wav = torch.from_numpy(data).float()
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)
    else:
        wav = wav.transpose(0, 1)
    
    wav = convert_audio(wav, sr, model.sample_rate, model.channels)
    
    with torch.no_grad():
        encoded_frames = model.encode(wav.unsqueeze(0))
        decoded_wav = model.decode(encoded_frames)
        
    out_data = decoded_wav.squeeze(0).transpose(0, 1).cpu().numpy()
    sf.write(output_wav, out_data, model.sample_rate, subtype="PCM_24")

# ─── GUI CLASS ───

class AudioScrubberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Scrubber Pro")
        self.root.geometry("600x450")
        
        self.files = []
        self.processing = False
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File Selection
        ttk.Label(main_frame, text="Audio Files:", font=('Helvetica', 10, 'bold')).pack(anchor=tk.W)
        self.file_list = tk.Listbox(main_frame, height=6)
        self.file_list.pack(fill=tk.X, pady=5)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Add MP3s", command=self.add_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear", command=self.clear_files).pack(side=tk.LEFT, padx=2)
        
        # Settings
        settings_frame = ttk.LabelFrame(main_frame, text=" Settings ", padding="10")
        settings_frame.pack(fill=tk.X, pady=15)
        
        ttk.Label(settings_frame, text="Virtual Device:").grid(row=0, column=0, sticky=tk.W)
        self.device_var = tk.StringVar(value="default")
        devices = [d['name'] for d in sd.query_devices() if d['max_input_channels'] > 0]
        self.device_combo = ttk.Combobox(settings_frame, textvariable=self.device_var, values=devices, width=40)
        self.device_combo.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(settings_frame, text="Neural Bitrate:").grid(row=1, column=0, sticky=tk.W)
        self.bitrate_var = tk.StringVar(value="12.0")
        ttk.Combobox(settings_frame, textvariable=self.bitrate_var, values=["1.5", "3.0", "6.0", "12.0", "24.0"], width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Progress
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, foreground="blue").pack(pady=5)
        
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(main_frame, text="START SCRUBBING", command=self.start_processing)
        self.start_btn.pack(pady=10)

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Audio Files", "*.mp3 *.wav")])
        for f in files:
            if f not in self.files:
                self.files.append(f)
                self.file_list.insert(tk.END, os.path.basename(f))

    def clear_files(self):
        self.files = []
        self.file_list.delete(0, tk.END)

    def update_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def start_processing(self):
        if not self.files:
            messagebox.showwarning("No Files", "Please add some audio files first.")
            return
        
        if self.processing: return
        
        self.processing = True
        self.start_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.process_loop, daemon=True).start()

    def process_loop(self):
        total = len(self.files)
        for i, f_path in enumerate(self.files):
            try:
                self.progress['value'] = (i / total) * 100
                temp = f_path.rsplit('.', 1)[0] + "_rerecord.wav"
                final = f_path.rsplit('.', 1)[0] + "_clean.wav"
                
                rerecord(f_path, temp, self.device_var.get(), self.update_status)
                neural_scrub(temp, final, self.bitrate_var.get(), self.update_status)
                
                if os.path.exists(temp):
                    os.remove(temp)
                    
            except Exception as e:
                self.update_status(f"Error processing {os.path.basename(f_path)}: {e}")
                continue
        
        self.progress['value'] = 100
        self.update_status("All files processed!")
        self.processing = False
        self.start_btn.config(state=tk.NORMAL)
        messagebox.showinfo("Done", "Processing complete!")

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioScrubberApp(root)
    root.mainloop()
