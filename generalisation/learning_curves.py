import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import ttest_rel

# ========== Configuration ==========
BIN_SIZE = 10

# ========== Functions ==========

def load_accuracy_from_file(filepath, bin_size=BIN_SIZE, condition_filter=None):
    df = pd.read_excel(filepath)

    if condition_filter:
        df = df[df["trial_type"].str.lower() == condition_filter.lower()]

    correct = pd.to_numeric(df['correct_answer'], errors='coerce')
    response = pd.to_numeric(df['response'], errors='coerce')
    is_correct = (correct == response).astype(int)

    binned_accuracy = [
        is_correct[i:i+bin_size].mean()
        for i in range(0, len(is_correct), bin_size)
    ]
    return np.array(binned_accuracy), is_correct.mean()

def plot_with_stats(y1, y2, label1, label2, title, save_path):
    min_len = min(len(y1), len(y2))
    y1 = y1[:min_len]
    y2 = y2[:min_len]
    x = np.arange(1, min_len + 1)

    t_stat, p_value = ttest_rel(y1, y2)

    plt.figure(figsize=(8, 6))
    plt.plot(x, y1, label=label1, color='steelblue', marker='o')
    plt.plot(x, y2, label=label2, color='darkorange', marker='o')
    plt.xlabel('Trial Bin')
    plt.ylabel('Accuracy')
    plt.title(f"{title}\nPaired t-test p = {p_value:.3f}")
    plt.ylim(0, 1.05)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def get_comparisons_for_participant(folder_files):
    if "baseline_uni_log.xlsx" in folder_files:
        return [
            ("baseline_uni_log.xlsx", "unimodal_nf_log.xlsx", "1 - Baseline vs Unimodal-NF"),
            ("crossmodal_wf_log.xlsx", "crossmodal_nf_log.xlsx", "2 - Crossmodal-WF vs Crossmodal-NF"),
            ("crossmodal_nf_log.xlsx", "unimodal_nf_log.xlsx", "3 - Crossmodal-NF to Unimodal-NF"),
        ]
    elif "baseline_cross_log.xlsx" in folder_files:
        return [
            ("baseline_cross_log.xlsx", "crossmodal_nf_log.xlsx", "1 - Baseline vs Crossmodal-NF"),
            ("unimodal_wf_log.xlsx", "unimodal_nf_log.xlsx", "2 - Unimodal-WF vs Unimodal-NF"),
            ("unimodal_nf_log.xlsx", "crossmodal_nf_log.xlsx", "3 - Unimodal-NF to Crossmodal-NF"),
        ]
    else:
        return []

# ========== Main Routine ==========

def run_for_all_participants():
    base_dir = os.path.join(os.getcwd(), "participant_data")
    participants = [p for p in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, p))]

    for participant in participants:
        part_path = os.path.join(base_dir, participant)
        print(f"\n=== Processing {participant} ===")

        folder_files = os.listdir(part_path)
        comparisons = get_comparisons_for_participant(folder_files)

        if not comparisons:
            print("⚠️  Could not determine participant design (missing baseline files). Skipping.")
            continue

        for file1, file2, title in comparisons:
            path1 = os.path.join(part_path, file1)
            path2 = os.path.join(part_path, file2)

            if os.path.exists(path1) and os.path.exists(path2):
                # Standard comparison (all trials)
                acc1, mean1 = load_accuracy_from_file(path1)
                acc2, mean2 = load_accuracy_from_file(path2)

                print(f"{file1} mean accuracy: {mean1:.3f}")
                print(f"{file2} mean accuracy: {mean2:.3f}")

                save_name = title.replace(" ", "_").replace("-", "").replace("/", "") + ".png"
                save_path = os.path.join(part_path, save_name)
                plot_with_stats(acc1, acc2, file1.replace(".xlsx", ""), file2.replace(".xlsx", ""), title, save_path)

                # If comparing to 'unimodal_nf_log.xlsx', also split into auditory/visual
                if file2 == "unimodal_nf_log.xlsx":
                    for modality in ["auditory", "visual"]:
                        acc2_mod, mean2_mod = load_accuracy_from_file(path2, condition_filter=modality)
                        acc1_mod, mean1_mod = load_accuracy_from_file(path1)

                        print(f"{file2} ({modality}) mean accuracy: {mean2_mod:.3f}")

                        mod_title = f"{title} - {modality.capitalize()} Only"
                        mod_save = mod_title.replace(" ", "_").replace("-", "").replace("/", "") + ".png"
                        mod_save_path = os.path.join(part_path, mod_save)

                        plot_with_stats(acc1_mod, acc2_mod, file1.replace(".xlsx", ""), f"{file2.replace('.xlsx','')}_{modality}", mod_title, mod_save_path)

            else:
                print(f"⚠️  Missing file(s) for {title}:")
                if not os.path.exists(path1): print(f" - {file1} not found")
                if not os.path.exists(path2): print(f" - {file2} not found")

if __name__ == "__main__":
    run_for_all_participants()
