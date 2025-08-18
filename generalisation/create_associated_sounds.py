import numpy as np
from scipy.io.wavfile import write
from scipy.signal import butter, sosfilt, welch
import os, pandas as pd

# ----------------- GLOBALS -----------------
np.random.seed(42)  # Set random seed for reproducibility

SR = 44100
DUR = 1.2
F0 = 130.81
N_HARM = 12
OUT_DIR = "generated_associated_sounds"
VOLUME = 0.9
T = np.linspace(0, DUR, int(SR * DUR), endpoint=False)

# ADSR envelope settings
ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL = 0.015, 0.04, 0.85, 0.10

# -------------- FUNCTIONS ------------------
def adsr(t, a, d, s, r):
    a_len, d_len, r_len = int(a*SR), int(d*SR), int(r*SR)
    env = np.ones_like(t) * s
    env[:a_len] = np.linspace(0, 1, a_len, endpoint=False)
    env[a_len:a_len+d_len] = np.linspace(1, s, d_len, endpoint=False)
    env[-r_len:] *= np.linspace(1, 0, r_len)
    return env

def synth_signal_custom_amplitudes(harm_amps, f0, t):
    sig = np.zeros_like(t)
    for h, amp in enumerate(harm_amps, start=1):
        sig += amp * np.sin(2 * np.pi * f0 * h * t)
    return sig

def apply_formant_filter(signal, sr, formants, bandwidths=None):
    sos = []
    for idx, f in enumerate(formants):
        bw = bandwidths[idx] if bandwidths else 100
        low = (f - bw/2) / (sr/2)
        high = (f + bw/2) / (sr/2)
        sos.extend(butter(N=2, Wn=[low, high], btype='bandpass', output='sos'))
    return sosfilt(sos, signal)

def spectral_centroid(x, sr):
    f, Pxx = welch(x, sr, nperseg=4096)
    return np.sum(f * Pxx) / np.sum(Pxx)

# -------------- FORMANT & TIMBRE PROFILES --------------
formant_profiles = [
    {"label": f"formant_{i+1}", "formants": [300 + i * 100, 800 + i * 200]} for i in range(10)
]

timbre_profiles = [
    {"label": f"timbre_{i+1}", "amps": [1.0 / (h + i * 0.1) for h in range(1, 13)]} for i in range(10)
]

assert len(formant_profiles) == len(timbre_profiles) == 10, "Need 10 formant/timbre pairs"

# ---------------- SYNTHESIS LOOP ----------------
os.makedirs(OUT_DIR, exist_ok=True)
log = []

for idx, (formant, timbre) in enumerate(zip(formant_profiles, timbre_profiles), start=1):
    amps = timbre["amps"]
    t_label = timbre["label"]
    f_label = formant["label"]
    formants = formant["formants"]

    sig = synth_signal_custom_amplitudes(amps, F0, T)
    sig = apply_formant_filter(sig, SR, formants)
    sig *= adsr(T, ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL)
    sig /= np.max(np.abs(sig)) / VOLUME
    wav = np.int16(sig * 32767)

    fname = f"associated_sound_{idx:02d}.wav"
    write(os.path.join(OUT_DIR, fname), SR, wav)
    print("Saved", fname)

    log.append({
        "file": fname,
        "F0_Hz": F0,
        "harmonics": N_HARM,
        "timbre_label": t_label,
        "formant_label": f_label,
        "formants": formants,
        "amps": amps,
        "spectral_centroid_Hz": float(spectral_centroid(sig, SR))
    })

# ---------------- LOGGING ----------------
df = pd.DataFrame(log)
df.to_csv(os.path.join(OUT_DIR, "log.csv"), index=False)
df.to_excel(os.path.join(OUT_DIR, "log.xlsx"), index=False)  # Save as Excel spreadsheet

print(f"\nFinished – {len(log)} incremental formant+timbre variants saved in '{OUT_DIR}'")