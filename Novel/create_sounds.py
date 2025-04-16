import numpy as np
import scipy.io.wavfile as wav
import os
import pandas as pd

def generate_sine_wave(freq, amplitude, duration, fs):
    """Generate a sine wave at given frequency and amplitude."""
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    return amplitude * np.sin(2 * np.pi * freq * t)

def main():
    # Parameters
    fs = 44100            # Sampling frequency (Hz)
    duration = 1.0        # Duration in seconds
    num_tones = 10        # Number of tones to generate
    freq_start = 100      # Start frequency (Hz)
    freq_end = 1000       # End frequency (Hz)
    amp_start = 0.1       # Start amplitude (normalized)
    amp_end = 0.9         # End amplitude (normalized)

    # Output directory
    output_dir = "generated_sounds"
    os.makedirs(output_dir, exist_ok=True)

    # Linear spacing of frequency and amplitude
    freqs = np.linspace(freq_start, freq_end, num_tones)
    amps = np.linspace(amp_start, amp_end, num_tones)

    # Store metadata
    metadata = []

    for i in range(num_tones):
        freq = freqs[i]
        amp = amps[i]
        tone = generate_sine_wave(freq, amp, duration, fs)
        tone = np.int16(tone * 32767)  # Convert to 16-bit PCM format

        filename = f"sound_{i+1:02d}.wav"
        wav_path = os.path.join(output_dir, filename)
        wav.write(wav_path, fs, tone)

        print(f"Saved {filename} | Frequency: {freq:.1f} Hz | Amplitude: {amp:.2f}")
        metadata.append({
            "Sound": i+1,
            "Frequency_Hz": freq,
            "Amplitude": amp,
            "Filename": filename
        })

    # Save metadata
    df = pd.DataFrame(metadata)
    df.to_excel(os.path.join(output_dir, "sound_metadata.xlsx"), index=False)
    print("\nSaved tone metadata to 'sound_metadata.xlsx'.")

if __name__ == "__main__":
    main()
