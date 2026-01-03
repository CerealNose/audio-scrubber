# Audio Scrubber

Audio Scrubber is a Python-based utility that automates the process of "scrubbing" audio files using a two-step pipeline:
1. **Virtual Loopback Re-recording**: Bypasses digital protections or artifacts by re-recording the audio through a virtual software "analog hole".
2. **Neural Codec Scrubbing**: Uses Facebook's **EnCodec** (a state-of-the-art neural audio codec) to compress and reconstruct the audio, effectively "cleaning" it through a neural bottleneck.

## Features
- **Automated Pipeline**: Drop your MP3s in and get clean WAVs out.
- **High Fidelity**: Uses 24-bit PCM for re-recording and high-bandwidth EnCodec (12kbps) for neural scrubbing.
- **Cross-Platform Ready**: Designed to work on Windows (VB-Audio Virtual Cable) and macOS (BlackHole).

## Installation

### 1. Install System Dependencies
- **FFmpeg**: Required for audio playback and conversion.
- **PortAudio**: Required for the `sounddevice` library.
- **Virtual Audio Cable**:
  - **Windows**: Install [VB-Audio Virtual Cable](https://vb-audio.com/Cable/).
  - **macOS**: Install [BlackHole](https://existential.audio/blackhole/).

### 2. Install Python Dependencies
```bash
pip install soundfile sounddevice numpy encodec torch torchaudio
```

## Usage

### Basic Usage
Run the script and provide the path to your MP3 files:
```bash
python audio_scrubber.py song1.mp3 song2.mp3
```

### Batch Processing
If no files are provided, the script will automatically process all `.mp3` files in the current directory:
```bash
python audio_scrubber.py
```

## Configuration
You can set the `VIRTUAL_DEVICE` environment variable to match your virtual cable's name:
- **Windows**: `set VIRTUAL_DEVICE="CABLE Output (VB-Audio Virtual Cable)"`
- **macOS**: `export VIRTUAL_DEVICE="BlackHole 2ch"`

## Technical Details
- **Re-recording**: Uses `ffmpeg` to pipe audio into a `sounddevice` input stream.
- **Neural Scrub**: Uses the `encodec_model_48khz` model with a target bandwidth of 12kbps.
- **Output**: Generates `_clean.wav` files in the same directory as the source.

## Troubleshooting
- **Device Not Found**: Ensure your virtual audio cable is installed and set as the default output device or correctly named in the script/environment.
- **Quality Issues**: You can adjust the `CODEC_BITRATE` in the script (options: 1.5, 3, 6, 12, 24 kbps).
