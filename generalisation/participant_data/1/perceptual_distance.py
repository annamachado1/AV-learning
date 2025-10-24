import os
import re
import ast
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

# =========================
# Configuration
# =========================
BASE_DIR = "."  # Use current directory as base
WF_FILE = "crossmodal_wf_log.xlsx"
NF_FILE = "crossmodal_nf_log.xlsx"

# Column names we expect (case-insensitive)
COL_TRIAL_TYPE = "trial_type"
COL_CORRECT = "correct_answer"
COL_RESPONSE = "response"
# a column that contains the 2 sounds shown on the trial (['sound_06.wav','sound_03.wav'])
CANDIDATE_SOUNDS_LIST_COLS = ["order", "tones_order", "tones", "audio_pair", "sounds"]

# how to parse sound ids like 'sound_06.wav' -> 6
SOUND_ID_PATTERN = re.compile(r"sound[_\-]?(\d+)", re.IGNORECASE)

# plotting
RANDOM_SEED = 7
SAVE_PREFIX = "p1_audio_distance"
DPI = 150

# =========================
# Helpers
# =========================
def _lower_map(df):
    """Return a mapping from lowercase->original column name."""
    return {c.lower(): c for c in df.columns}

def _find_sounds_list_column(df):
    cols_map = _lower_map(df)
    # direct candidates
    for c in CANDIDATE_SOUNDS_LIST_COLS:
        if c in cols_map:
            return cols_map[c]
    # heuristic: look for a column full of list-like strings that contain 'sound'
    for orig in df.columns:
        s = df[orig]
        if s.dtype == object:
            # peek some non-null entries
            sample = s.dropna().astype(str).head(8).tolist()
            if any("sound" in x.lower() and x.strip().startswith("[") for x in sample):
                return orig
    raise ValueError(
        f"Could not find a column with the two sounds per trial. "
        f"Tried {CANDIDATE_SOUNDS_LIST_COLS} and a heuristic."
    )

def _parse_sound_list(cell):
    """cell like "['sound_06.wav','sound_03.wav']" -> ['sound_06.wav','sound_03.wav']"""
    if isinstance(cell, list):
        return cell
    try:
        return ast.literal_eval(cell)
    except Exception:
        # fall back: split rudimentarily
        s = str(cell)
        s = s.strip("[]")
        parts = [p.strip().strip("'\"") for p in s.split(",")]
        return [p for p in parts if p]

def _sound_index(name):
    """Extract integer index from a sound filename/label."""
    m = SOUND_ID_PATTERN.search(str(name))
    if not m:
        return np.nan
    return int(m.group(1))

def load_and_annotate(path, schedule_label):
    """Load one file (WF or NF), compute is_correct, extract two sounds, compute distance."""
    df = pd.read_excel(path)
    cmap = _lower_map(df)

    # normalize names for correctness columns
    if COL_CORRECT not in cmap or COL_RESPONSE not in cmap:
        raise ValueError(
            f"{path} must include '{COL_CORRECT}' and '{COL_RESPONSE}' (case-insensitive). "
            f"Found columns: {list(df.columns)}"
        )

    correct_col = cmap[COL_CORRECT]
    response_col = cmap[COL_RESPONSE]
    df["is_correct"] = (pd.to_numeric(df[correct_col], errors="coerce")
                        == pd.to_numeric(df[response_col], errors="coerce")).astype(int)

    # find and parse the sounds list column
    sounds_col = _find_sounds_list_column(df)
    pair_lists = df[sounds_col].apply(_parse_sound_list)

    # expect exactly 2 sounds per trial
    sound_a, sound_b = [], []
    bad_rows = 0
    for lst in pair_lists:
        if not isinstance(lst, (list, tuple)) or len(lst) < 2:
            sound_a.append(np.nan); sound_b.append(np.nan); bad_rows += 1
        else:
            sound_a.append(lst[0])
            sound_b.append(lst[1])
    if bad_rows:
        print(f"WARNING: {bad_rows} rows in {os.path.basename(path)} did not have two sounds.")

    df["sound_A"] = sound_a
    df["sound_B"] = sound_b
    df["sound_A_idx"] = df["sound_A"].apply(_sound_index)
    df["sound_B_idx"] = df["sound_B"].apply(_sound_index)
    df["audio_distance"] = (df["sound_A_idx"] - df["sound_B_idx"]).abs()

    # keep only rows with valid distance
    df = df.dropna(subset=["audio_distance"]).copy()
    df["audio_distance"] = df["audio_distance"].astype(int)

    # schedule
    df["schedule"] = schedule_label
    return df

def grouped_accuracy(df, by=["audio_distance", "schedule"]):
    g = (df.groupby(by)["is_correct"]
           .agg(["mean", "count"])
           .reset_index()
           .rename(columns={"mean": "accuracy", "count": "n"}))
    # simple normal-approx 95% CI for visualization
    p = g["accuracy"].to_numpy()
    n = g["n"].to_numpy()
    se = np.sqrt(p * (1 - p) / np.clip(n, 1, None))
    g["ci95"] = 1.96 * se
    return g

def spearman_line(df, label):
    if df["audio_distance"].nunique() < 2:
        return f"{label}: not enough distance variation."
    rho, p = spearmanr(df["audio_distance"], df["is_correct"])
    return f"{label}: Spearman rho={rho:.3f}, p={p:.4f}, n={len(df)}"

# =========================
# Main
# =========================
def main():
    print("=== Participant 1: Accuracy vs Audio Pairing Perceptual Distance ===")
    wf_path = os.path.join(BASE_DIR, WF_FILE)
    nf_path = os.path.join(BASE_DIR, NF_FILE)

    if not os.path.exists(wf_path) or not os.path.exists(nf_path):
        raise FileNotFoundError(f"Expected both files:\n - {wf_path}\n - {nf_path}")

    wf = load_and_annotate(wf_path, "WF")
    nf = load_and_annotate(nf_path, "NF")
    df = pd.concat([wf, nf], ignore_index=True)

    # Save tidy trials table
    keep_cols = ["schedule", "is_correct", "audio_distance",
                 "sound_A", "sound_B", "sound_A_idx", "sound_B_idx"]
    out_csv = os.path.join(BASE_DIR, f"{SAVE_PREFIX}_trials.csv")
    df[keep_cols].to_csv(out_csv, index=False)
    print(f"Saved trials table -> {out_csv}")

    # ----- Stats
    print("\n--- Spearman correlations (distance vs accuracy) ---")
    print(spearman_line(df, "Combined WF+NF"))
    print(spearman_line(wf, "WF only"))
    print(spearman_line(nf, "NF only"))

    # ----- Accuracy by distance (bars with CIs), combined and split
    acc_combined = grouped_accuracy(df, by=["audio_distance"])
    acc_split = grouped_accuracy(df, by=["audio_distance", "schedule"])

    acc_combined_path = os.path.join(BASE_DIR, f"{SAVE_PREFIX}_accuracy_by_distance_combined.csv")
    acc_split_path = os.path.join(BASE_DIR, f"{SAVE_PREFIX}_accuracy_by_distance_split.csv")
    acc_combined.to_csv(acc_combined_path, index=False)
    acc_split.to_csv(acc_split_path, index=False)
    print(f"Saved summaries -> {acc_combined_path}, {acc_split_path}")

    # ----- Plots
    # 1) Combined bar plot with 95% CI
    plt.figure(figsize=(8, 6))
    x = acc_combined["audio_distance"].to_numpy()
    y = acc_combined["accuracy"].to_numpy()
    yerr = acc_combined["ci95"].to_numpy()
    plt.bar(x, y, yerr=yerr, alpha=0.8, capsize=4)
    plt.ylim(0, 1.05)
    plt.xlabel("Audio perceptual distance |i - j| (sound_i vs sound_j)")
    plt.ylabel("Accuracy")
    plt.title("Participant 1: Accuracy vs Audio Distance (WF + NF)")
    plt.grid(axis="y", alpha=0.3)
    pth = os.path.join(BASE_DIR, f"{SAVE_PREFIX}_bar_combined.png")
    plt.tight_layout(); plt.savefig(pth, dpi=DPI); plt.close()

    # 2) Line plot split by WF/NF
    plt.figure(figsize=(8, 6))
    for sched, g in acc_split.groupby("schedule"):
        plt.plot(g["audio_distance"], g["accuracy"], marker="o", linewidth=2, label=sched)
        # add CIs as thin error bars
        plt.errorbar(g["audio_distance"], g["accuracy"], yerr=g["ci95"], fmt="none", capsize=3, alpha=0.7)
    plt.ylim(0, 1.05)
    plt.xlabel("Audio perceptual distance |i - j| (sound_i vs sound_j)")
    plt.ylabel("Accuracy")
    plt.title("Participant 1: Accuracy vs Audio Distance (WF vs NF)")
    plt.grid(True, alpha=0.3)
    plt.legend(title="Schedule")
    pth = os.path.join(BASE_DIR, f"{SAVE_PREFIX}_line_WF_vs_NF.png")
    plt.tight_layout(); plt.savefig(pth, dpi=DPI); plt.close()

    # 3) Scatter of per-trial accuracy (jittered) vs distance
    rng = np.random.default_rng(RANDOM_SEED)
    plt.figure(figsize=(8, 6))
    x = df["audio_distance"].to_numpy()
    y = df["is_correct"].astype(float).to_numpy()
    y_j = y + (rng.random(len(y)) - 0.5) * 0.06
    plt.scatter(x, y_j, alpha=0.5, s=20)
    plt.yticks([0, 1], ["Incorrect", "Correct"])
    plt.ylim(-0.15, 1.15)
    plt.xlabel("Audio perceptual distance |i - j|")
    plt.ylabel("Accuracy (jittered)")
    plt.title("Participant 1: Per-trial Accuracy vs Audio Distance (WF + NF)")
    plt.grid(True, alpha=0.3)
    pth = os.path.join(BASE_DIR, f"{SAVE_PREFIX}_scatter_trials.png")
    plt.tight_layout(); plt.savefig(pth, dpi=DPI); plt.close()

    print("\nSaved figures:")
    print(f" - {os.path.join(BASE_DIR, f'{SAVE_PREFIX}_bar_combined.png')}")
    print(f" - {os.path.join(BASE_DIR, f'{SAVE_PREFIX}_line_WF_vs_NF.png')}")
    print(f" - {os.path.join(BASE_DIR, f'{SAVE_PREFIX}_scatter_trials.png')}")
    print("\nDone.")

if __name__ == "__main__":
    main()
