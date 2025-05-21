# harmonic_layers_and_f0_TESTSET.py
import numpy as np
from scipy.io.wavfile import write
from scipy.signal import welch
import pandas as pd, os, json

# ---------------- GLOBAL CONSTANTS -----------------------------------------
SR   = 44_100
DUR  = 1.2
# F0_VALUES = [138, 155, 170, 185, 207, 233, 255, 275, 310, 345, 370, 400]  # shifted, mid-range
F0_START = 135  # offset by +5 from create_sounds.py
F0_STEP = 10.545454545454545
HARM_START = 23  # offset by -1 from create_sounds.py
HARM_STEP = -2
F0_VALUES = [round(F0_START + i * F0_STEP, 2) for i in range(12)]
N_HARM_LAYERS = [HARM_START + i * HARM_STEP for i in range(12)]
TILT_VALUE = 3.5
assert len(F0_VALUES) == len(N_HARM_LAYERS), "Mismatch in tone count!"

OUT_DIR = "generated_sounds_testset"
ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL = 0.015, 0.04, 0.85, 0.10
VOLUME = 0.9

# ---------------- helper functions -----------------------------------------
def adsr(t, a, d, s, r):
    a_len, d_len, r_len = int(a*SR), int(d*SR), int(r*SR)
    env = np.ones_like(t) * s
    env[:a_len] = np.linspace(0, 1, a_len, endpoint=False)
    env[a_len:a_len+d_len] = np.linspace(1, s, d_len, endpoint=False)
    env[-r_len:] *= np.linspace(1, 0, r_len)
    return env

def synth_signal(n_harm, beta, f0, t):
    sig = np.zeros_like(t)
    for h in range(1, n_harm+1):
        sig += (1 / (h**beta)) * np.sin(2*np.pi*f0*h*t)
    return sig

def spectral_centroid(x, sr):
    f, Pxx = welch(x, sr, nperseg=4096)
    return np.sum(f * Pxx) / np.sum(Pxx)

# ---------------- synthesis -------------------------------------------------
os.makedirs(OUT_DIR, exist_ok=True)
t = np.linspace(0, DUR, int(SR*DUR), endpoint=False)

log = []
for idx, (f0, n_h) in enumerate(zip(F0_VALUES, N_HARM_LAYERS), 1):
    sig = synth_signal(n_h, TILT_VALUE, f0, t)
    sig *= adsr(t, ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL)
    sig /= np.max(np.abs(sig)) / VOLUME
    wav = np.int16(sig * 32767)

    fname = f"sound_{idx:02d}.wav"
    write(os.path.join(OUT_DIR, fname), SR, wav)
    print("Saved", fname)

    log.append({
        "file": fname,
        "F0_Hz": f0,
        "harmonics": n_h,
        "beta_tilt": TILT_VALUE,
        "spectral_centroid_Hz": float(spectral_centroid(sig, SR))
    })

# ---------------- feature log ----------------------------------------------
pd.DataFrame(log).to_csv(os.path.join(OUT_DIR, "tone_feature_log.csv"), index=False)
with open(os.path.join(OUT_DIR, "tone_feature_log.json"), "w") as f:
    json.dump(log, f, indent=2)

print("\nFinished – 12 testset tones with new F0 and harmonics saved in", OUT_DIR)
