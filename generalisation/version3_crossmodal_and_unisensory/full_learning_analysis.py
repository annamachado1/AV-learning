import os, re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import ttest_rel

# ------------ config ------------
DATA_DIR = Path("participant_data")   # base folder with participant subfolders
SND_RE = re.compile(r"sound[_-]?(\d+)", re.I)
SHP_RE = re.compile(r"shape[_-]?(\d+)", re.I)

def _snd_idx(x):
    m = SND_RE.search(str(x)); return int(m.group(1)) if m else np.nan
def _shp_idx(x):
    m = SHP_RE.search(str(x)); return int(m.group(1)) if m else np.nan

def load_pairings(path):
    df = pd.read_excel(path)
    if "tone_file" not in df.columns or "shape_file" not in df.columns:
        raise ValueError(f"{path} missing required columns")
    df["sound_index"] = df["tone_file"].apply(_snd_idx)
    df["shape_index"] = df["shape_file"].apply(_shp_idx)
    df["is_correct"] = (df["sound_index"] == df["shape_index"]).astype(int)
    df["abs_index_error"] = (df["sound_index"] - df["shape_index"]).abs()
    return df

def analyze_participant(pid_folder):
    pid = os.path.basename(pid_folder)
    f1 = Path(pid_folder) / "free_pairings_1.xlsx"
    f2 = Path(pid_folder) / "free_pairings_2.xlsx"
    if not (f1.exists() and f2.exists()):
        return None
    pre = load_pairings(f1)
    post = load_pairings(f2)
    return {
        "participant": pid,
        "acc_pre": pre["is_correct"].mean(),
        "acc_post": post["is_correct"].mean(),
        "dist_pre": pre["abs_index_error"].mean(),
        "dist_post": post["abs_index_error"].mean(),
    }

def main():
    summaries = []
    for sub in os.listdir(DATA_DIR):
        sub_path = DATA_DIR / sub
        if os.path.isdir(sub_path):
            res = analyze_participant(sub_path)
            if res: summaries.append(res)
    df = pd.DataFrame(summaries)
    if df.empty:
        print("No participants with both pairing files found."); return

    print("\nPer-participant summary:\n", df.round(3))

    # paired t-tests
    t_acc = ttest_rel(df["acc_pre"], df["acc_post"])
    t_dist = ttest_rel(df["dist_pre"], df["dist_post"])
    print(f"\nAccuracy pre={df['acc_pre'].mean():.3f}, post={df['acc_post'].mean():.3f}, t={t_acc.statistic:.2f}, p={t_acc.pvalue:.4g}")
    print(f"Distance pre={df['dist_pre'].mean():.2f}, post={df['dist_post'].mean():.2f}, t={t_dist.statistic:.2f}, p={t_dist.pvalue:.4g}")

    # plots
    fig, ax = plt.subplots(1,2, figsize=(9,4))
    # accuracy
    ax[0].bar([0,1],[df["acc_pre"].mean(), df["acc_post"].mean()],
              yerr=[df["acc_pre"].std()/np.sqrt(len(df)),
                    df["acc_post"].std()/np.sqrt(len(df))],
              capsize=5, alpha=0.8)
    ax[0].set_xticks([0,1]); ax[0].set_xticklabels(["Pre","Post"])
    ax[0].set_ylim(0,1.05)
    ax[0].set_ylabel("Accuracy")
    ax[0].set_title("Free pairings accuracy")

    # distance
    ax[1].bar([0,1],[df["dist_pre"].mean(), df["dist_post"].mean()],
              yerr=[df["dist_pre"].std()/np.sqrt(len(df)),
                    df["dist_post"].std()/np.sqrt(len(df))],
              capsize=5, alpha=0.8)
    ax[1].set_xticks([0,1]); ax[1].set_xticklabels(["Pre","Post"])
    ax[1].set_ylabel("Mean |index error|")
    ax[1].set_title("Free pairings distance (lower=better)")

    plt.tight_layout()
    out = DATA_DIR/"pairings_pre_post_summary.png"
    plt.savefig(out, dpi=150)
    print("Saved group summary plot →", out)

if __name__ == "__main__":
    main()
