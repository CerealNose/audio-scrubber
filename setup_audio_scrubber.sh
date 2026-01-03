#!/bin/bash
echo "Setting up Audio Scrubber..."
sudo apt-get update
sudo apt-get install -y libportaudio2 ffmpeg
pip3 install soundfile sounddevice numpy encodec torch torchaudio
echo "Setup complete. You can now run the app using: python3 audio_scrubber.py [your_mp3_files]"
