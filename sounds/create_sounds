"""
harmonics_only_sounds.py

Makes 6 sounds that differ ONLY in how many harmonics they contain.
Pitch (F0), tilt, length, envelope, and volume are identical for every sound.
The tilt is set low (1.0) so that every added harmonic is loud enough to hear.

Needs only: numpy
(No scipy, no pandas, no numpy.random, no numpy.fft -- these use compiled
files that your computer's security policy blocks.)
Run:        python harmonics_only_sounds.py
"""
import csv
import json
import os
import wave

import numpy as np

# ---------------- settings --------------------------------------------------
SR = 44_100                  # samples per second
DUR = 1.2                    # seconds
F0 = 188.0                   # Hz, the SAME for all 6 sounds (change if you like)
TILT_VALUE = 1.0             # SAME for all 6 sounds (lower = harmonics stay louder)
HARMONICS = [1, 2, 4, 8, 16, 32]     # the ONLY thing that changes between sounds (each doubles)
ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL = 0.015, 0.04, 0.85, 0.10
VOLUME = 0.9
OUT_DIR = "generated_sounds"


# ---------------- helper functions ------------------------------------------
def adsr(t, a, d, s, r):
    """Volume envelope: quick rise, small dip, steady hold, fade out."""
    a_len, d_len, r_len = int(a * SR), int(d * SR), int(r * SR)
    env = np.ones_like(t) * s
    env[:a_len] = np.linspace(0, 1, a_len, endpoint=False)
    env[a_len:a_len + d_len] = np.linspace(1, s, d_len, endpoint=False)
    env[-r_len:] *= np.linspace(1, 0, r_len)
    return env


def synth_signal(n_harm, beta, f0, t):
    """Add up sine waves at f0, 2*f0, 3*f0 ... each quieter by 1 / h**beta."""
    sig = np.zeros_like(t)
    for h in range(1, n_harm + 1):
        sig += (1 / (h ** beta)) * np.sin(2 * np.pi * f0 * h * t)
    return sig


def spectral_centroid(n_harm, beta, f0):
    """
    Average pitch of the sound, weighted by power (the 'brightness').
    Worked out directly from the harmonics' strengths, so no FFT is needed.
    """
    h = np.arange(1, n_harm + 1)
    power = (1 / h ** beta) ** 2
    return float(np.sum(f0 * h * power) / np.sum(power))


def save_wav(path, samples_int16):
    """Write a mono 16-bit WAV file using Python's built-in wave module."""
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(samples_int16.astype("<i2").tobytes())


# ---------------- synthesis --------------------------------------------------
os.makedirs(OUT_DIR, exist_ok=True)
t = np.linspace(0, DUR, int(SR * DUR), endpoint=False)
envelope = adsr(t, ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL)

log = []
for number, n_h in enumerate(HARMONICS, start=1):
    sig = synth_signal(n_h, TILT_VALUE, F0, t)
    sig *= envelope
    sig /= np.max(np.abs(sig)) / VOLUME
    wav = np.int16(sig * 32767)

    fname = f"sound_{number:02d}.wav"
    save_wav(os.path.join(OUT_DIR, fname), wav)
    print("Saved", fname, f"({n_h} harmonics)")

    log.append({
        "file": fname,
        "F0_Hz": float(F0),
        "harmonics": int(n_h),
        "beta_tilt": TILT_VALUE,
        "spectral_centroid_Hz": round(spectral_centroid(n_h, TILT_VALUE, F0), 3),
    })

# ---------------- feature log -------------------------------------------------
with open(os.path.join(OUT_DIR, "sound_feature_log.csv"), "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(log[0].keys()))
    writer.writeheader()
    writer.writerows(log)
with open(os.path.join(OUT_DIR, "sound_feature_log.json"), "w") as f:
    json.dump(log, f, indent=2)

print(f"\nFinished - {len(HARMONICS)} sounds saved in", OUT_DIR)
