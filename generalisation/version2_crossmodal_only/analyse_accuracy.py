import os, re, math, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ========== CONFIG ==========
PARTICIPANT_ID = "3"   # change as needed
BIN_SIZE = 10
BASE = Path("participant_data") / PARTICIPANT_ID

FP1 = BASE / "free_pairings_1.xlsx"   # first pairing
FP2 = BASE / "free_pairings_2.xlsx"   # second pairing
CROSSMODAL = BASE / "crossmodal_wf_log.xlsx"

SND_RE = re.compile(r"sound[_\-]?(\d+)", re.I)

# ========== HELPERS ==========
def _snd_idx(x):
    m = SND_RE.search(str(x))
    return int(m.group(1)) if m else np.nan

def ci95(k,n):
    if n<=0: return (np.nan,np.nan)
    p=k/n; se=math.sqrt(p*(1-p)/n)
    return (p-1.96*se, p+1.96*se)

def bin_series(vals, bin_size):
    edges = list(range(0, len(vals), bin_size)) + [len(vals)]
    centers, means = [], []
    for i in range(len(edges)-1):
        sl = vals[edges[i]:edges[i+1]]
        if sl.size:
            centers.append((edges[i]+edges[i+1])/2)
            means.append(np.nanmean(sl))
    return np.array(centers), np.array(means)

def load_free_pairings(path):
    df = pd.read_excel(path)
    df["sound_index"] = df["tone_file"].apply(_snd_idx)
    df["shape_index"] = df["shape_file"].str.extract(r"(\d+)").astype(int)
    df["is_correct"] = (df["sound_index"] == df["shape_index"]).astype(int)
    return df

def load_crossmodal(path):
    df = pd.read_excel(path)
    import ast
    def parse(cell):
        if isinstance(cell, list): return cell
        return ast.literal_eval(str(cell))
    tones = df["tones_order"].apply(parse)
    df["toneA"] = tones.apply(lambda x: x[0])
    df["toneB"] = tones.apply(lambda x: x[1])
    df["audio_distance"] = [_snd_idx(a)-_snd_idx(b) for a,b in zip(df["toneA"],df["toneB"])]
    df["audio_distance"] = df["audio_distance"].abs()
    df["is_correct"] = (pd.to_numeric(df["correct_answer"], errors="coerce") ==
                        pd.to_numeric(df["response"], errors="coerce")).astype(int)
    df["t"] = np.arange(1,len(df)+1)
    return df

# ========== MAIN ==========
def main():
    BASE.mkdir(parents=True, exist_ok=True)

    # --- 1. Learning curve ---
    dfc = load_crossmodal(CROSSMODAL)
    centers, means = bin_series(dfc["is_correct"].to_numpy(), BIN_SIZE)
    plt.figure(figsize=(7,4))
    plt.plot(dfc["t"], dfc["is_correct"], ".", alpha=0.3, label="trials")
    plt.plot(centers, means, "-o", lw=2, label=f"bin={BIN_SIZE}")
    plt.ylim(-0.05,1.05); plt.xlabel("Trial"); plt.ylabel("Accuracy")
    plt.title("Crossmodal block: learning curve")
    plt.grid(True, alpha=0.3); plt.legend(); plt.tight_layout()
    plt.savefig(BASE/"fig1_crossmodal_learning_curve.png", dpi=150); plt.close()

    # --- 2. Free pairings before vs after ---
    df1, df2 = load_free_pairings(FP1), load_free_pairings(FP2)
    acc1, acc2 = df1["is_correct"].mean(), df2["is_correct"].mean()
    plt.figure(figsize=(5,4))
    plt.bar([0,1],[acc1,acc2], tick_label=["Pairing 1","Pairing 2"], alpha=0.8)
    plt.ylim(0,1.05); plt.ylabel("Accuracy")
    plt.title("Free pairings: before vs after")
    plt.grid(axis="y", alpha=0.3); plt.tight_layout()
    plt.savefig(BASE/"fig2_free_pairings_before_after.png", dpi=150); plt.close()

    # --- 3. Crossmodal accuracy by sound distance ---
    g = dfc.groupby("audio_distance")["is_correct"].agg(["mean","count"]).reset_index()
    x, y, n = g["audio_distance"], g["mean"], g["count"]
    yerr = []
    for m, k in zip(y,n):
        lo,hi = ci95(int(round(m*k)), k)
        yerr.append([m-lo, hi-m])
    yerr = np.array(yerr).T
    plt.figure(figsize=(6,4))
    plt.bar(x,y,yerr=yerr,capsize=3,alpha=0.8)
    plt.ylim(0,1.05); plt.xlabel("Audio distance |i-j|"); plt.ylabel("Accuracy")
    plt.title("Crossmodal block: accuracy by audio distance")
    plt.grid(axis="y", alpha=0.3); plt.tight_layout()
    plt.savefig(BASE/"fig3_crossmodal_accuracy_by_distance.png", dpi=150); plt.close()

    print("Saved three figures in", BASE)

if __name__=="__main__":
    main()
