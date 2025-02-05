import numpy as np
import scipy.io.wavfile as wav
import os

# Sampling rate and duration settings
SAMPLE_RATE = 44100  
DURATION = 5  # seconds

# Generate 10 unique frequencies spaced between 100 Hz and 1000 Hz
FREQUENCIES = np.linspace(100, 1000, 10)

def generate_sine_wave(frequency):
    """Generate a pure sine wave at a given frequency."""
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), endpoint=False)
    wave = np.sin(2 * np.pi * frequency * t)

    # Apply an envelope (fade in and fade out)
    envelope = np.linspace(0, 1, int(SAMPLE_RATE * 0.1))  # 0.1 sec fade-in
    wave[:len(envelope)] *= envelope
    wave[-len(envelope):] *= envelope[::-1]  # Fade-out

    return wave

def save_tones_with_unique_frequencies():
    """Generate and save 10 sine waves with completely unique frequencies."""
    if not os.path.exists("generated_tones"):
        os.makedirs("generated_tones")

    for i, frequency in enumerate(FREQUENCIES):
        wave = generate_sine_wave(frequency)
        filename = f"generated_tones/tone_{i+1:02d}.wav"
        wave = np.int16(wave * 32767)  # Convert to 16-bit PCM
        wav.write(filename, SAMPLE_RATE, wave)
        print(f"Saved: {filename}")

# Run the script to generate 10 unique frequency tones
save_tones_with_unique_frequencies()
