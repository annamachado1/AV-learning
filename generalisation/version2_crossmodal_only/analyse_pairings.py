import re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ----------------- config -----------------
PARTICIPANT_ID = "4"  # change if needed
BASE = Path("participant_data") / PARTICIPANT_ID
FP1 = BASE / "free_pairings_1.xlsx"   # BEFORE
FP2 = BASE / "free_pairings_2.xlsx"   # AFTER
OUT = BASE / "pairings_before_after_dashboard.png"

SND_RE = re.compile(r"sound[_\-]?(\d+)", re.I)
SHP_RE = re.compile(r"shape[_\-]?(\d+)", re.I)

# ----------------- helpers -----------------
def _snd_idx(x):
    m = SND_RE.search(str(x)); return int(m.group(1)) if m else np.nan
def _shp_idx(x):
    m = SHP_RE.search(str(x)); return int(m.group(1)) if m else np.nan

def load_pairings(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    # expected columns: tone_file, shape_file (your saving code uses these)
    if "tone_file" not in df.columns or "shape_file" not in df.columns:
        raise ValueError(f"{path.name} must have 'tone_file' and 'shape_file' columns.")
    df["sound_index"] = df["tone_file"].apply(_snd_idx).astype(int)
    df["shape_index"] = df["shape_file"].apply(_shp_idx).astype(int)
    df["is_correct"] = (df["sound_index"] == df["shape_index"]).astype(int)
    df["abs_index_error"] = (df["sound_index"] - df["shape_index"]).abs()
    return df[["tone_file","shape_file","sound_index","shape_index","is_correct","abs_index_error"]]

def build_matrix(df, N=None):
    if N is None:
        N = max(df["sound_index"].max(), df["shape_index"].max())
    mat = np.zeros((N, N), dtype=int)
    for _, r in df.iterrows():
        si, vi = int(r["sound_index"])-1, int(r["shape_index"])-1
        if 0 <= si < N and 0 <= vi < N:
            mat[si, vi] += 1
    return mat

# ----------------- main plotting -----------------
def main():
    df1 = load_pairings(FP1)  # before
    df2 = load_pairings(FP2)  # after
    N = max(df1["sound_index"].max(), df2["sound_index"].max(),
            df1["shape_index"].max(), df2["shape_index"].max())

    M1 = build_matrix(df1, N)
    M2 = build_matrix(df2, N)

    acc1 = df1["is_correct"].mean()
    acc2 = df2["is_correct"].mean()
    d1 = df1["abs_index_error"].to_numpy()
    d2 = df2["abs_index_error"].to_numpy()

    # ---- figure layout: 2x2 ----
    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.0], width_ratios=[1, 1], hspace=0.25, wspace=0.25)

    # Panel A: Heatmap BEFORE
    axA = fig.add_subplot(gs[0, 0])
    im1 = axA.imshow(M1, origin="lower", aspect="auto")
    axA.set_title(f"A. Mapping matrix (Before) — acc={acc1:.2f}")
    axA.set_xlabel("Shape index"); axA.set_ylabel("Sound index")
    axA.set_xticks(range(N)); axA.set_xticklabels([f"{i}" for i in range(1, N+1)], rotation=0, fontsize=8)
    axA.set_yticks(range(N)); axA.set_yticklabels([f"{i}" for i in range(1, N+1)], fontsize=8)
    # diagonal guide
    axA.plot(range(N), range(N), color="white", lw=1, alpha=0.7)
    cbar1 = fig.colorbar(im1, ax=axA, fraction=0.046, pad=0.04)
    cbar1.set_label("count")

    # Panel B: Heatmap AFTER
    axB = fig.add_subplot(gs[0, 1])
    im2 = axB.imshow(M2, origin="lower", aspect="auto")
    axB.set_title(f"B. Mapping matrix (After) — acc={acc2:.2f}")
    axB.set_xlabel("Shape index"); axB.set_ylabel("Sound index")
    axB.set_xticks(range(N)); axB.set_xticklabels([f"{i}" for i in range(1, N+1)], rotation=0, fontsize=8)
    axB.set_yticks(range(N)); axB.set_yticklabels([f"{i}" for i in range(1, N+1)], fontsize=8)
    axB.plot(range(N), range(N), color="white", lw=1, alpha=0.7)
    cbar2 = fig.colorbar(im2, ax=axB, fraction=0.046, pad=0.04)
    cbar2.set_label("count")

    # Panel C: Dot plot (what they paired & how close), Before vs After
    axC = fig.add_subplot(gs[1, 0])
    axC.plot([0.5, N+0.5], [0.5, N+0.5], "k--", lw=1, alpha=0.7, label="x=y (correct)")
    # jitter points slightly in y so overlaps are visible
    jitter = 0.08
    y1 = df1["sound_index"].to_numpy().astype(float) + (np.random.rand(len(df1))-0.5)*2*jitter
    y2 = df2["sound_index"].to_numpy().astype(float) + (np.random.rand(len(df2))-0.5)*2*jitter
    axC.scatter(df1["shape_index"], y1, s=30, alpha=0.6, label="Before", marker="o")
    axC.scatter(df2["shape_index"], y2, s=30, alpha=0.6, label="After", marker="^")
    axC.set_xlim(0.5, N+0.5); axC.set_ylim(0.5, N+0.5)
    axC.set_xlabel("Chosen shape index"); axC.set_ylabel("Sound index")
    axC.set_title("C. Pair choices vs identity (distance = |shape−sound|)")
    axC.legend()

    # Panel D: Distance distribution & accuracy bars
    axD = fig.add_subplot(gs[1, 1])
    # histogram overlays of |index error|
    bins = np.arange(-0.5, N+0.5, 1)
    axD.hist(d1, bins=bins, alpha=0.5, label=f"Before (mean={np.mean(d1):.2f})")
    axD.hist(d2, bins=bins, alpha=0.5, label=f"After (mean={np.mean(d2):.2f})")
    axD.set_xlabel("|index error| (perceptual distance)"); axD.set_ylabel("count")
    axD.set_title("D. Distance distribution (lower is better)")
    axD.legend(loc="upper left")
    # small twin axis bars for accuracy
    axD2 = axD.twinx()
    axD2.bar([N-2, N-1], [acc1, acc2], width=0.7, alpha=0.6)
    axD2.set_ylim(0, 1.05); axD2.set_ylabel("accuracy")
    axD2.set_yticks([0,0.5,1.0])

    plt.tight_layout()
    fig.savefig(OUT, dpi=150)
    plt.close(fig)
    print(f"Saved: {OUT}")

if __name__ == "__main__":
    main()
