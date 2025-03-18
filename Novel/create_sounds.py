import numpy as np
import scipy.signal as signal
import scipy.io.wavfile as wav
import os

def generate_white_noise(duration=3, fs=10000):  # Changed duration from 0.3 to 3
    """Generate a segment of white noise."""
    return np.random.uniform(-1, 1, int(fs * duration))

def instantaneous_frequency_dilation(noise, fs, entropy_levels):
    """Apply frequency dilation by filtering and resampling noise."""
    distinct_sounds = []
    for entropy in entropy_levels:
        filter_order = max(int(50 / entropy), 5)  # Increased filter order for better distinction
        cutoff = max(min(int(fs * entropy * 0.8), fs // 2 - 1), 1)  # Adjusted scaling for better spacing
        b = signal.firwin(filter_order, cutoff / (fs / 2), window='hamming', pass_zero=True)
        filtered_noise = signal.lfilter(b, 1, noise)
        resampled_noise = signal.resample(filtered_noise, len(noise))
        distinct_sounds.append(resampled_noise)
    return distinct_sounds

def time_dilation(noise, fs, entropy_levels):
    """Apply time dilation by truncating and resampling noise."""
    distinct_sounds = []
    for entropy in entropy_levels:
        truncated_duration = max(int(len(noise) * entropy * 0.8), 1)  # Adjusted scaling for better distinction
        truncated_noise = noise[:truncated_duration]
        resampled_noise = signal.resample(truncated_noise, len(noise))
        distinct_sounds.append(resampled_noise)
    return distinct_sounds

def save_wav(filename, data, fs=10000):
    """Save sound as a WAV file."""
    wav.write(filename, fs, np.int16(data * 32767))

def main():
    fs = 10000  # Sampling frequency
    output_dir = "generated_sounds"
    os.makedirs(output_dir, exist_ok=True)
    
    entropy_levels = np.linspace(0.05, 0.9, 5)  # Increased range for more variation
    
    noise = generate_white_noise(fs=fs)
    fd_sounds = instantaneous_frequency_dilation(noise, fs, entropy_levels)
    td_sounds = time_dilation(noise, fs, entropy_levels)
    
    for i, (fd_sound, td_sound) in enumerate(zip(fd_sounds, td_sounds)):
        save_wav(os.path.join(output_dir, f"fd_sound_{i+1}.wav"), fd_sound, fs)
        save_wav(os.path.join(output_dir, f"td_sound_{i+1}.wav"), td_sound, fs)
    
    print("Generated 10 distinct novel sounds (5 FD and 5 TD) in the 'generated_sounds' folder.")

if __name__ == "__main__":
    main()
