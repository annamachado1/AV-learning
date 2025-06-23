import numpy as np
from scipy.io.wavfile import write
from scipy.signal import welch
import pandas as pd, os, json

# ---------------- GLOBALS -----------------------------------
SR = 44_100
DUR = 1.2
F0 = 196              # Fixed pitch
N_HARM = 12           # Fixed harmonic count
OUT_DIR = "tilt_inharm_sounds"
VOLUME = 0.9
T = np.linspace(0, DUR, int(SR * DUR), endpoint=False)

# ADSR envelope parameters
ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL = 0.015, 0.04, 0.85, 0.10

# Spectral tilt (beta) and inharmonicity values (paired)
TILT_VALUES = [0.3, 1.0, 1.3, 1.7, 2.1, 2.5]
INHARM_VALUES = [0.00, 0.01, 0.02, 0.03, 0.04, 0.05]

# ---------------- UTILS -------------------------------------
def adsr(t, a, d, s, r):
    a_len, d_len, r_len = int(a*SR), int(d*SR), int(r*SR)
    env = np.ones_like(t) * s
    env[:a_len] = np.linspace(0, 1, a_len, endpoint=False)
    env[a_len:a_len+d_len] = np.linspace(1, s, d_len, endpoint=False)
    env[-r_len:] *= np.linspace(1, 0, r_len)
    return env

def synth_signal_tilt_inharm(n_harm, beta, f0, inharm, t):
    sig = np.zeros_like(t)
    for h in range(1, n_harm+1):
        freq = f0 * h * (1 + inharm)
        amp = 1 / (h ** beta)
        sig += amp * np.sin(2 * np.pi * freq * t)
    return sig

def spectral_centroid(x, sr):
    f, Pxx = welch(x, sr, nperseg=4096)
    return np.sum(f * Pxx) / np.sum(Pxx)

# ---------------- SYNTHESIS LOOP ----------------------------
os.makedirs(OUT_DIR, exist_ok=True)
log = []

for idx, (beta, inh) in enumerate(zip(TILT_VALUES, INHARM_VALUES), start=1):
    sig = synth_signal_tilt_inharm(N_HARM, beta, F0, inh, T)
    sig *= adsr(T, ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL)
    sig /= np.max(np.abs(sig)) / VOLUME
    wav = np.int16(sig * 32767)

    fname = f"tilt_inharm_{idx:02d}.wav"
    write(os.path.join(OUT_DIR, fname), SR, wav)
    print("Saved", fname)

    log.append({
        "file": fname,
        "F0_Hz": F0,
        "harmonics": N_HARM,
        "spectral_tilt_beta": beta,
        "inharmonicity": inh,
        "spectral_centroid_Hz": float(spectral_centroid(sig, SR))
    })

# ---------------- LOGGING ------------------------------------
pd.DataFrame(log).to_csv(os.path.join(OUT_DIR, "tilt_inharm_.csv"), index=False)
with open(os.path.join(OUT_DIR, "tilt_inharm_log.json"), "w") as f:
    json.dump(log, f, indent=2)

print(f"\nFinished – {len(log)} sounds saved in '{OUT_DIR}'")
