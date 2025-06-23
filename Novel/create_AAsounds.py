import numpy as np
from scipy.io.wavfile import write
from scipy.signal import welch, butter, sosfilt
import pandas as pd, os, json

# ---------------- GLOBALS -----------------------------------
SR = 44_100
DUR = 1.2
F0 = 196              # Fixed pitch
N_HARM = 12           # Fixed harmonic count
OUT_DIR = "formant_timbre_sounds"
VOLUME = 0.9
T = np.linspace(0, DUR, int(SR * DUR), endpoint=False)

# ADSR envelope parameters
ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL = 0.015, 0.04, 0.85, 0.10

# ---------------- UTILS -------------------------------------
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

def spectral_centroid(x, sr):
    f, Pxx = welch(x, sr, nperseg=4096)
    return np.sum(f * Pxx) / np.sum(Pxx)

# In apply_formant_filter, lower bandwidth for high formants:
def apply_formant_filter(signal, sr, formants, bandwidths=None):
    sos = []
    for idx, f in enumerate(formants):
        bw = bandwidths[idx] if bandwidths else 100
        low = (f - bw/2) / (sr/2)
        high = (f + bw/2) / (sr/2)
        sos.extend(butter(N=2, Wn=[low, high], btype='bandpass', output='sos'))
    return sosfilt(sos, signal)

# ---------------- FORMANT & TIMBRE PROFILES -----------------
formant_profiles = [
    {"label": "a_like", "formants": [700, 1100]},
    {"label": "e_like", "formants": [500, 1900]},
    {"label": "i_like", "formants": [250, 1800]},
    #{"label": "i_like", "formants": [250, 1800], "bandwidths": [100, 80]},  # narrower second formant
    {"label": "o_like", "formants": [400, 800]},
    {"label": "u_like", "formants": [350, 600]},
    {"label": "nasal",  "formants": [250, 1000, 1800]}
    #{"label": "nasal",  "formants": [300, 1000, 2200], "bandwidths": [100, 100, 70]},  # taper off high formant
]

timbre_profiles = [
    {"label": "flat", "amps": [1.0] * N_HARM},
    {"label": "bright", "amps": [1.0, 0.9, 0.8, 0.6, 0.4, 0.3, 0.2, 0.15, 0.1, 0.08, 0.06, 0.05]},
    {"label": "dark", "amps": np.linspace(1.0, 0.05, N_HARM).tolist()},
    {"label": "bell", "amps": [0.1, 1.0, 0.6, 0.4, 0.3] + [0.1] * 7},
    {"label": "hollow", "amps": [1.0 if h % 2 == 1 else 0.0 for h in range(1, N_HARM + 1)]},
    {"label": "odd_decay", "amps": [1.0 / h if h % 2 == 1 else 0.0 for h in range(1, N_HARM + 1)]}
]

assert len(formant_profiles) == len(timbre_profiles), "Formant and timbre profiles must match one-to-one."

# ---------------- SYNTHESIS LOOP ----------------------------
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

    fname = f"sound_{idx:02d}_{f_label}_{t_label}.wav"
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

# ---------------- LOGGING ------------------------------------
pd.DataFrame(log).to_csv(os.path.join(OUT_DIR, "formant_timbre_log.csv"), index=False)
with open(os.path.join(OUT_DIR, "formant_timbre_log.json"), "w") as f:
    json.dump(log, f, indent=2)

print(f"\nFinished – {len(log)} formant+timbre variants saved in '{OUT_DIR}'")
