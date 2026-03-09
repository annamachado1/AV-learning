# --- Setup & imports ---
from psychopy import prefs  # set audio backend before importing sound
prefs.hardware['audioLib'] = ['pygame', 'sounddevice']
prefs.general['audioDevice'] = ['default']

import os
os.environ["QT_QPA_PLATFORM"] = "cocoa"  # macOS GUI fix (safe elsewhere too)

import random
import pandas as pd
import numpy as np
import traceback

from itertools import combinations
from psychopy import visual, core, event, sound

from psychopy import logging
logging.console.setLevel(logging.ERROR)  # suppresses certain warnings
import warnings
warnings.filterwarnings("ignore", message="elementwise comparison failed")

# === Collect participant ID and set up directories before anything else ===
def get_participant_id():
    participant_id = input("Enter Participant ID: ").strip()

    # Create participant data folder if it doesn't exist
    participant_folder = os.path.join("./participant_data", participant_id)
    if not os.path.exists(participant_folder):
        os.makedirs(participant_folder)
    else:
        # Always overwrite existing data
        for file in [f for f in os.listdir(participant_folder) if os.path.isfile(os.path.join(participant_folder, f))]:
            os.remove(os.path.join(participant_folder, file))

    return participant_id

# === Instruction helper ===
def show_instructions(text, key_list):
    """Display instructions and wait for a key in key_list. Returns the key pressed (or 's' if pressed)."""
    instr = visual.TextStim(win, text=text, color="lightgrey", height=0.06, wrapWidth=1.6)
    while True:
        instr.draw()
        win.flip()
        keys = event.waitKeys(keyList=key_list + ["escape", "s"])
        if "escape" in keys:
            win.close()
            core.quit()
        if "s" in keys:
            return "s"
        if keys:
            return keys[0]

# === Non-negative values for ISI and ITI helper function ===

# Make Gaussian Distrubution of Fixation Durations
mean_ITI = 0.5
sd_ITI = 0.2
n_ITI = 150

mean_ISI = 0.5
sd_ISI = 0.2
n_ISI = 150

def sample_non_negative_normal(mean, std, size):
    samples = np.random.normal(mean, std, size)
    while np.any(samples < 0):  # Re-sample until no negative values
        samples[samples < 0] = np.random.normal(mean, std, np.sum(samples < 0))
    return samples

interTrialPause = sample_non_negative_normal(mean_ITI, sd_ITI, n_ITI)
interStimulusPause = sample_non_negative_normal(mean_ISI, sd_ISI, n_ISI)

# === Save helpers ===
def save_free_pairings_to_excel(filename):
    """Save participant_data['free_pairings'] to ./participant_data/<ID>/<filename>"""
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("free_pairings", []))
    excel_filename = os.path.join(participant_folder, filename)
    df.to_excel(excel_filename, index=False)
    print(f"Free pairings data saved to {excel_filename}")

def save_crossmodal_with_feedback_to_excel():
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    excel_filename = os.path.join(participant_folder, "crossmodal_wf_log.xlsx")
    
    df = pd.DataFrame(participant_data.get("crossmodal_wf_log", []))
    pause_df = pd.DataFrame(participant_data.get("crossmodal_pause_durations", []))

    with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="trial_log", index=False)
        pause_df.to_excel(writer, sheet_name="pause_summary", index=False)

    print(f"Crossmodal with feedback data saved to {excel_filename}")

def save_unimodal_to_excel(matrix, trial_log, stimuli, duration, label, order):
    try:
        # --- paths ---
        participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
        os.makedirs(participant_folder, exist_ok=True)
        filename = os.path.join(participant_folder, f"Unimodal_{label}s_({order}).xlsx")

        # --- matrix → DataFrame (square, labels from stimuli) ---
        n = len(stimuli)
        matrix_df = pd.DataFrame(matrix, index=stimuli, columns=stimuli)

        # --- trial log mapping (indices → names OR pass-through if already names) ---
        def name_of(x):
            return stimuli[x] if isinstance(x, int) else x

        trial_rows = [[name_of(t[0]), name_of(t[1]), name_of(t[2]), name_of(res)]
                      for t, res in trial_log]

        trial_cols = [f"{label} 1", f"{label} 2", f"{label} 3", f"Chosen {label}"]
        trial_log_df = pd.DataFrame(trial_rows, columns=trial_cols)
        trial_log_df.index = range(1, len(trial_rows) + 1)
        trial_log_df.index.name = "Trial Number"

        # --- meta info at top of Trials sheet ---
        meta_df = pd.DataFrame({
            "Duration (s)": [duration],
            "Order": [order],
            "N stimuli": [n],
        })

        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            # Trials sheet: meta first, blank row, then table
            meta_df.to_excel(writer, sheet_name="Trials", index=False, startrow=0)
            trial_log_df.to_excel(writer, sheet_name="Trials", index=True, startrow=len(meta_df) + 2)

            # Matrix sheet
            matrix_df.to_excel(writer, sheet_name="Difference_Scores", index=True)

            # Stimuli sheet (for traceability)
            pd.DataFrame({"Stimulus": stimuli}).to_excel(writer, sheet_name="Stimuli", index=True)

        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Could not save matrix to Excel ({e}).")

import random
import numpy as np
from itertools import combinations

import random
import numpy as np
from itertools import combinations


def check_pair_graph_connected(trial_list, n_items):
    graph = {i: set() for i in range(n_items)}
    for a, b, c in trial_list:
        for i, j in [(a, b), (a, c), (b, c)]:
            graph[i].add(j)
            graph[j].add(i)

    visited = set()
    stack = [0]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        stack.extend(graph[node] - visited)

    return len(visited) == n_items


def summarize_triplet_design(triplets, n_items):
    pair_counts = {pair: 0 for pair in combinations(range(n_items), 2)}
    item_counts = np.zeros(n_items, dtype=int)

    for triplet in triplets:
        for i in triplet:
            item_counts[i] += 1
        for p in combinations(triplet, 2):
            pair_counts[p] += 1

    pair_vals = np.array(list(pair_counts.values()))
    summary = {
        "pair_counts": pair_counts,
        "item_counts": item_counts,
        "pair_min": int(pair_vals.min()),
        "pair_max": int(pair_vals.max()),
        "pair_mean": float(pair_vals.mean()),
        "pair_var": float(pair_vals.var()),
        "n_zero_pairs": int(np.sum(pair_vals == 0)),
        "item_min": int(item_counts.min()),
        "item_max": int(item_counts.max()),
        "item_mean": float(item_counts.mean()),
        "item_var": float(item_counts.var()),
        "connected": check_pair_graph_connected(triplets, n_items),
    }
    return summary


def design_score(triplets, n_items, target_pair_count, target_item_count):
    """
    Lower is better.
    Strongly penalizes:
    - missing pairs
    - uneven item counts
    - uneven pair counts
    - disconnected pair graph
    """
    summary = summarize_triplet_design(triplets, n_items)
    pair_vals = np.array(list(summary["pair_counts"].values()))
    item_vals = summary["item_counts"]

    # Main penalties
    zero_pair_penalty = 5000 * summary["n_zero_pairs"]
    disconnected_penalty = 100000 if not summary["connected"] else 0

    # Strong push toward equal coverage
    pair_balance_penalty = np.sum((pair_vals - target_pair_count) ** 2)
    item_balance_penalty = np.sum((item_vals - target_item_count) ** 2)

    # Additional spread penalties
    pair_range_penalty = 200 * (summary["pair_max"] - summary["pair_min"])
    item_range_penalty = 500 * (summary["item_max"] - summary["item_min"])

    return (
        disconnected_penalty
        + zero_pair_penalty
        + pair_balance_penalty
        + 5 * item_balance_penalty
        + pair_range_penalty
        + item_range_penalty
    )


def generate_stronger_triplets(n_items=10, n_trials=60, seed=12345, n_restarts=200, n_swap_iters=5000):
    """
    Stronger triplet generator using:
    1. random initialization
    2. local search by swap improvement

    Returns:
        best_triplets, best_pair_counts, best_item_counts
    """
    rng = random.Random(seed)
    all_triplets = list(combinations(range(n_items), 3))

    if n_trials > len(all_triplets):
        raise ValueError(f"n_trials={n_trials} exceeds total possible unique triplets={len(all_triplets)}")

    n_pairs = n_items * (n_items - 1) // 2
    target_pair_count = (3 * n_trials) / n_pairs   # for 10 items, 60 trials -> 4
    target_item_count = (3 * n_trials) / n_items   # for 10 items, 60 trials -> 18

    best_triplets = None
    best_score = float("inf")

    for restart in range(n_restarts):
        # Random initial subset
        current = rng.sample(all_triplets, n_trials)
        current_set = set(current)
        current_score = design_score(current, n_items, target_pair_count, target_item_count)

        # Local improvement by swaps
        for _ in range(n_swap_iters):
            out_triplet = rng.choice(current)
            in_triplet = rng.choice(all_triplets)

            if in_triplet in current_set:
                continue

            trial_candidate = current.copy()
            idx = trial_candidate.index(out_triplet)
            trial_candidate[idx] = in_triplet

            candidate_score = design_score(trial_candidate, n_items, target_pair_count, target_item_count)

            if candidate_score < current_score:
                current = trial_candidate
                current_set.remove(out_triplet)
                current_set.add(in_triplet)
                current_score = candidate_score

                # Early exit if already very good
                summary = summarize_triplet_design(current, n_items)
                if (
                    summary["connected"]
                    and summary["n_zero_pairs"] == 0
                    and summary["item_max"] - summary["item_min"] <= 1
                    and summary["pair_max"] - summary["pair_min"] <= 1
                ):
                    break

        if current_score < best_score:
            best_score = current_score
            best_triplets = current.copy()

            summary = summarize_triplet_design(best_triplets, n_items)
            print(
                f"[restart {restart+1}] "
                f"score={best_score:.1f} | "
                f"pair range={summary['pair_min']}-{summary['pair_max']} | "
                f"zero pairs={summary['n_zero_pairs']} | "
                f"item range={summary['item_min']}-{summary['item_max']} | "
                f"connected={summary['connected']}"
            )

            # Stop if nearly ideal
            if (
                summary["connected"]
                and summary["n_zero_pairs"] == 0
                and summary["item_max"] - summary["item_min"] <= 1
                and summary["pair_max"] - summary["pair_min"] <= 1
            ):
                break

    best_summary = summarize_triplet_design(best_triplets, n_items)
    return best_triplets, best_summary["pair_counts"], best_summary["item_counts"]

FIXED_SHAPE_TRIPLETS, shape_pair_counts, shape_item_counts = generate_stronger_triplets(
    n_items=10,
    n_trials=60,
    seed=12345,
    n_restarts=200,
    n_swap_iters=5000
)

FIXED_SOUND_TRIPLETS, sound_pair_counts, sound_item_counts = generate_stronger_triplets(
    n_items=10,
    n_trials=60,
    seed=54321,
    n_restarts=200,
    n_swap_iters=5000
)

print("Shape graph connected:", check_pair_graph_connected(FIXED_SHAPE_TRIPLETS, 10))
print("Sound graph connected:", check_pair_graph_connected(FIXED_SOUND_TRIPLETS, 10))
print("Shape pair count range:", min(shape_pair_counts.values()), max(shape_pair_counts.values()))
print("Sound pair count range:", min(sound_pair_counts.values()), max(sound_pair_counts.values()))
print("Shape item counts:", shape_item_counts)
print("Sound item counts:", sound_item_counts)

def print_design_summary(name, triplets, n_items=10):
    summary = summarize_triplet_design(triplets, n_items)
    print(f"\n{name}")
    print("-" * len(name))
    print("Connected:", summary["connected"])
    print("Zero-covered pairs:", summary["n_zero_pairs"])
    print("Pair count range:", summary["pair_min"], summary["pair_max"])
    print("Pair mean/var:", round(summary["pair_mean"], 3), round(summary["pair_var"], 3))
    print("Item count range:", summary["item_min"], summary["item_max"])
    print("Item mean/var:", round(summary["item_mean"], 3), round(summary["item_var"], 3))
    print("Item counts:", summary["item_counts"])

print_design_summary("SHAPES", FIXED_SHAPE_TRIPLETS, 10)
print_design_summary("SOUNDS", FIXED_SOUND_TRIPLETS, 10)

# === End-of-experiment survey ===
def run_end_survey():
    """Prompt participant for survey responses on the PsychoPy window and save to Excel."""
    survey_questions = [
        "Which features of the shapes did you focus on to help with learning?",
        "Which features of the sounds did you focus on to help with learning?",
        "Were certain shape–sound pairings easier to remember than others? Why?",
        "Did you use any specific strategies to remember the pairings?",
        "Did you notice any patterns in the stimuli that helped you?",
        "How confident were you in your answers during the test section? Why?",
        "Did your strategy change across the sections? If so, how and why?",
        "What did you find most challenging about the task?",
        "Did you rely more on intuition or logic when making your choices?",
        "Did you imagine any associations (e.g., stories, categories) to help remember the pairs?",
        "Any additional comments about how you approached the task?",
    ]
    responses = []
    instr = visual.TextStim(
        win,
        text="End Survey\n\nType your answer and press ENTER to continue.\n(Use BACKSPACE to edit)",
        color="lightgrey",
        height=0.06,
        wrapWidth=1.6,
        pos=(0, 0.7)
    )
    question_stim = visual.TextStim(win, text="", color="white", height=0.055, wrapWidth=1.6, pos=(0, 0.3))
    answer_stim = visual.TextStim(win, text="", color="yellow", height=0.055, wrapWidth=1.6, pos=(0, -0.2))

    for q in survey_questions:
        answer = ""
        question_stim.text = q
        while True:
            instr.draw()
            question_stim.draw()
            answer_stim.text = answer + "|"
            answer_stim.draw()
            win.flip()
            keys = event.waitKeys()
            commit = False
            for key in keys:
                if key == "return":
                    responses.append(answer)
                    commit = True
                    break
                elif key == "backspace":
                    answer = answer[:-1]
                elif key == "space":
                    answer += " "
                elif key == "escape":
                    win.close()
                    core.quit()
                elif len(key) == 1:
                    answer += key
            if commit:
                break

    # Save responses to Excel
    try:
        df = pd.DataFrame({"question": survey_questions, "response": responses})
        participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
        os.makedirs(participant_folder, exist_ok=True)
        excel_path = os.path.join(participant_folder, "end_survey.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"Survey responses saved to {excel_path}")
    except Exception as e:
        print(f"Could not save survey to Excel: {e}")

# === Advanced end of survey experiment ===
def run_end_survey_adv():    
    survey_questions = [
        "Which features of the shapes did you focus on to help with learning?",
        "Which features of the sounds did you focus on to help with learning?",
        "Were certain shape–sound pairings easier to remember than others? Why?",
        "Did you use any specific strategies to remember the pairings?",
        "Did you notice any patterns in the stimuli that helped you?",
        "How confident were you in your answers during the testing section? Why?",
        "Did your strategy change across the sections? If so, how and why?",
        "What did you find most challenging about the task?",
        "Did you rely more on intuition or logic when making your choices?",
        "Did you imagine any associations (e.g., stories, categories) to help remember the pairs?",
    ]
    
    title = visual.TextStim(win, text="End of Experiment Survey", pos=(0, 0.65), height=0.1, bold=True)
    qnum = visual.TextStim(win, text="", pos=(0, 0.52), height=0.06, color="#000000")
    qtext = visual.TextStim(win, text="", pos=(0, 0.40), height=0.08, wrapWidth=1.6)
    
    # TextBox2 may not be available in older PsychoPy versions; fall back to the simple text survey
    try:
        textbox = visual.TextBox2(
            win,
            text="",
            pos=(0, -0.2),
            units="norm",
            size=(1.6, 0.65),
            letterHeight=0.07,
            editable=True,
            color='black',
            )
    except Exception as e:
        print(f"TextBox2 failed to initialize ({e}); falling back to basic end-survey.")
        return run_end_survey()
    
    tb_border = visual.Rect(
        win, units="norm",
        width=1.6, height=0.65, pos=(0, -0.2),
        lineColor='white', lineWidth=2, fillColor="#C2C2C2"
        )

    # Buttons
    def button(label, center_pos):
        padding = (0.08, 0.035)
        w, h = padding[0] * 2.4, padding[1] * 2.4
        rect = visual.Rect(win, width=w, height=h, pos=center_pos, fillColor="#4C7BF1", lineColor=None, opacity=1)
        text = visual.TextStim(win, text=label, pos=center_pos, height=0.06, color="white")
        return rect, text
    
    # Makes the buttons
    back_rect, back_text = button("Back", (-0.15, -0.65))
    next_rect, next_text = button("Next", (0.15, -0.65))
    finish_rect, finish_text = button("Finish", (0.15, -0.65))
    esc_text = visual.TextStim(win, text="Press Esc to cancel", pos=(0, -0.82), height=0.06, color="white")

    mouse = event.Mouse(win=win)
    responses = ["" for _ in survey_questions]
    idx = 0
    nQ = len(survey_questions)

    # Restore text when moving between questions
    def load_q(i):
        qnum.text = f"Question {i+1} of {nQ}"
        qtext.text = survey_questions[i]
        textbox.editable = False
        textbox.setText(responses[i] or "")
        textbox.editable = True

    load_q(idx)

    while True:
        # --- Draw frame ---
        title.draw()
        qnum.draw()
        qtext.draw()
        tb_border.draw()
        textbox.draw()
        esc_text.draw()

        # draw correct buttons depending on position
        if idx > 0:
            back_rect.draw(); back_text.draw()
        if idx < nQ - 1:
            next_rect.draw(); next_text.draw()
        else:
            finish_rect.draw(); finish_text.draw()

        win.flip()
        
        if len(textbox.text) > 480:
            textbox.setText(textbox.text[:480])

        # Handle mouse clicks
        if mouse.getPressed()[0]:
            mpos = mouse.getPos()
            clicked = False

            # Back
            if idx > 0:
                if (abs(mpos[0] - back_rect.pos[0]) <= back_rect.width/2) and (abs(mpos[1] - back_rect.pos[1]) <= back_rect.height/2):
                    responses[idx] = textbox.text
                    idx -= 1
                    load_q(idx)
                    clicked = True

            # Next / Finish
            target_rect = next_rect if idx < nQ - 1 else finish_rect
            if (abs(mpos[0] - target_rect.pos[0]) <= target_rect.width/2) and (abs(mpos[1] - target_rect.pos[1]) <= target_rect.height/2):
                responses[idx] = textbox.text
                if idx < nQ - 1:
                    idx += 1
                    load_q(idx)
                else:
                    break
                clicked = True

            # Anti-sticky click: wait for release
            if clicked:
                while mouse.getPressed()[0]:
                    win.flip()

        # Handle keys
        keys = event.getKeys(modifiers=True, timeStamped=False)
        
        for k in keys:
            if isinstance(k, tuple):
                key, mods = k
            else:
                key, mods = k, []

            # Quit
            if key == "escape":
                if key == "escape":
                    textbox.editable = False
                    core.quit()
    # Finished
    textbox.editable = False
    try:
        df = pd.DataFrame({"question": survey_questions, "response": responses})
        participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
        os.makedirs(participant_folder, exist_ok=True)
        excel_path = os.path.join(participant_folder, "end_survey.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"Survey responses saved to {excel_path}")
    except Exception as e:
        print(f"Could not save survey to Excel: {e}")

# === Presentation timing constants ===
STIMULUS_DURATION = 1.0  # seconds, all shapes and sounds
FIXATION_DURATION = 0.5  # seconds, all fixations

# === Stimulus pair definitions ===
stimuli_pairs = [
    ("shape_01.png", "sound_01.wav"),
    ("shape_02.png", "sound_02.wav"),
    ("shape_03.png", "sound_03.wav"),
    ("shape_04.png", "sound_04.wav"),
    ("shape_05.png", "sound_05.wav"),
    ("shape_06.png", "sound_06.wav"),
    ("shape_07.png", "sound_07.wav"),
    ("shape_08.png", "sound_08.wav"),
    ("shape_09.png", "sound_09.wav"),
    ("shape_10.png", "sound_10.wav"),
]

# === Preload all sound objects ===
def preload_sounds(audio_dir):
    sound_dict = {}
    for fname in sorted([f for f in os.listdir(audio_dir) if f.startswith("sound_") and f.endswith(".wav")]):
        sound_dict[fname] = sound.Sound(os.path.join(audio_dir, fname))
    return sound_dict

# === Free-pairing block (parameterized) ===
def free_pairings_block(intro_text, version):
    """
    Shows shapes on the top row and musical notes on the bottom row.
    Participant clicks a note to play it, then clicks a shape to pair them.
    Saves into participant_data['free_pairings'].
    """
    global participant_data
    participant_data["free_pairings"] = []

    # Use shape_01.png–shape_10.png and sound_01.wav–sound_10.wav
    shape_files = [f"shape_{i:02d}.png" for i in range(1, 11)]
    total_shape_files = shape_files

    tone_files = [f"sound_{i:02d}.wav" for i in range(1, 11)]

    # Randomize the order of shapes and tones for display only
    random.shuffle(total_shape_files)
    random.shuffle(tone_files)

    # Evenly space shapes and tones
    numshapes = len(total_shape_files)
    if version == "First":
        shapesrow1 = np.linspace(-0.9, 0.9, min(numshapes, 10))
        shapesrow2 = np.array([])  # no second row
    else:
        if numshapes % 2 == 0:
            shapesrow1 = np.linspace(-0.7, 0.7, numshapes // 2)
            shapesrow2 = np.linspace(-0.7, 0.7, numshapes // 2)
        else:
            shapesrow1 = np.linspace(-0.7, 0.7, (numshapes + 1) // 2)
            shapesrow2 = np.linspace(-0.7, 0.7, numshapes // 2)
    
    tone_positions = np.linspace(-0.9, 0.9, len(tone_files))

    shapes = []
    tones = []
    tone_sounds = {}
    
    if version == "First":
        RAISE_DY    = 0.07  # Distance to raise the tones by
        UNDER_SHAPE_DY = 0.30   # Distance under the shape to place the tone once paired   
    else:
        RAISE_DY    = 0.04 
        UNDER_SHAPE_DY = 0.22

    ANIM_ALPHA  = 0.35  # Speed value for movement animation

    for i, filename in enumerate(total_shape_files):
        if version == "First":
            pos = (shapesrow1[i], 0.4)
        else:
            if i < len(shapesrow1):
                pos = (shapesrow1[i], 0.6)
            else:
                pos = (shapesrow2[i - len(shapesrow1)], 0.1)

        stim = visual.ImageStim(
            win,
            image=os.path.join(image_dir, filename),
            pos=pos,
            size=(0.15, 0.25)
        )
        shapes.append({"stim": stim, "file": filename})

    for i, filename in enumerate(tone_files):
        home_pos = (tone_positions[i], -0.5)
        stim = visual.ImageStim(
            win,
            image="musical_note.png",  # icon for all tones
            pos=(tone_positions[i], -0.5),
            size=(0.1, 0.1)
        )
        tones.append({"stim": stim,
                      "file": filename,
                      "home_pos": home_pos,
                      "target_pos": home_pos,     # animate toward this position every frame
                      "paired_shape": None,       # file name of shape if paired
                      "pressed": False,           # Is the tone pressed
                      "times_clicked": 0
                      })
        tone_sounds[filename] = main_sounds[filename]

    def paired_pos(tone):
        # Base position for a paired tone
        shp_file = tone.get("paired_shape")
        if not shp_file:
            return tone["home_pos"]
        sx, sy = shape_by_file[shp_file]["stim"].pos
        return (sx, sy - UNDER_SHAPE_DY)

    def update_target(tone):
        # Set position to animate towards

        if tone["pressed"]: # if pressed and paired, raise, if unpaired, lower
            if tone["paired_shape"] is None:
                bx, by = tone["home_pos"]
                tone["target_pos"] = (bx, by + RAISE_DY)
            else:
                bx, by = paired_pos(tone)
                tone["target_pos"] = (bx, by - RAISE_DY)
        else:
            if tone["paired_shape"] is None: # if unpaired, go home, if paired, go under shape
                tone["target_pos"] = tone["home_pos"]
            else:
                tone["target_pos"] = paired_pos(tone)

    def set_pressed(tone, value: bool):
        tone["pressed"] = bool(value)
        update_target(tone)

    def move_tone_under_shape(tone, shape):
        # Pair and place under shape (not pressed)
        tone["paired_shape"] = shape["file"]
        set_pressed(tone, False)

    def send_home(tone):
        # Unpair and go home (not pressed)
        tone["paired_shape"] = None
        set_pressed(tone, False)

    mouse = event.Mouse(visible=True)
    selected_tone = None
    mouse_was_pressed = False

    shape_pairings = {}  # pairing states
    tone_by_file = {t["file"]: t for t in tones}
    shape_by_file = {s["file"]: s for s in shapes}

    # Intro instructions
    instr_result = show_instructions(intro_text, ["space"])
    if instr_result == "s":
        return "skip"

    while True:

        for t in tones: # Animate shape movement
            update_target(t)
            x, y = t["stim"].pos
            tx, ty = t["target_pos"]
            if (abs(tx - x) > 1e-4) or (abs(ty - y) > 1e-4):
                t["stim"].pos = (x + ANIM_ALPHA * (tx - x),
                                y + ANIM_ALPHA * (ty - y))

        for shape in shapes: # draw shapes and sounds
            shape["stim"].draw()
        for tone in tones:
            tone["stim"].draw()

        if all(tone["paired_shape"] is not None for tone in tones): # if all tones are paired, allow participant to move on
            ready_msg = visual.TextStim(
                win,
                text="All sounds paired – press SPACEBAR to continue",
                color="lightgrey",
                height=0.05,
                pos=(0, -0.85)
            )
            ready_msg.draw()

        win.flip()
        
        mouse_pressed, _, _ = mouse.getPressed()
        clicked_now = mouse_pressed and not mouse_was_pressed
        
        if clicked_now:
            tone_clicked = next((t for t in tones if t["stim"].contains(mouse)), None)

            if tone_clicked is not None:
                for t in tones: # stop any sounds and play the clicked tone
                    tone_sounds[t["file"]].stop()
                tone_sounds[tone_clicked["file"]].play()
                tone_clicked["times_clicked"] += 1

                for t in tones: # unpress all other tones
                    if t is tone_clicked:
                        continue
                    set_pressed(t, False)

                set_pressed(tone_clicked, True) # press clicked tone
                selected_tone = tone_clicked # Update the selected tone

            elif selected_tone is not None:
                # Check if a shape was clicked
                clicked_shape = next((s for s in shapes if s["stim"].contains(mouse)), None)

                if clicked_shape is not None:
                    shape_file = clicked_shape["file"]
                    tone_file  = selected_tone["file"]

                    # if shape already had a tone, send that old tone home
                    if shape_file in shape_pairings:
                        old_tone_file = shape_pairings[shape_file]
                        old_tone = tone_by_file[old_tone_file]
                        send_home(old_tone)
                        del shape_pairings[shape_file]

                    # if shape already has a tone, send old tone back home
                    for shp, tfile in list(shape_pairings.items()):
                        if tfile == tone_file:
                            del shape_pairings[shp]
                            break

                    # move selected tone under shape
                    move_tone_under_shape(selected_tone, clicked_shape)
                    shape_pairings[shape_file] = tone_file
            
                    selected_tone = None

                elif selected_tone is not None:
                    set_pressed(selected_tone, False)
                    selected_tone = None

        mouse_was_pressed = mouse_pressed

        keys = event.getKeys(keyList=["escape", "space", "s"])
        if "escape" in keys:
            win.close(); core.quit()
        elif "s" in keys:
            return "skip"
        elif "space" in keys and all(tone["paired_shape"] is not None for tone in tones):
            break

    # Record pairings
    for tone in tones:
        if "paired_shape" in tone:
            sound_index = int(tone["file"].split('_')[1].split('.')[0])            
            shape_label = tone["paired_shape"].split('_')[1].split('.')[0]
            shape_index = float(shape_label.replace('p', '.'))
            participant_data["free_pairings"].append({
                "tone_file": tone["file"],
                "shape_file": tone["paired_shape"],
                "sound_index": sound_index,
                "shape_index": shape_index,
                "tone_pos": tone["home_pos"],
                "shape_pos": next(s["stim"].pos for s in shapes if s["file"] == tone["paired_shape"]),
                "Times_Tone_Clicked": tone["times_clicked"]
            })

    print("Pairings recorded:", participant_data["free_pairings"])
    win.flip()
    return 'done'

# === Helper function for caluclating difficylty of a crossmodal trial ===
def crossWF_calc_trial_diff(sound1,sound2):
    idx1 = int(sound1.split('_')[1].split('.')[0])
    idx2 = int(sound2.split('_')[1].split('.')[0])
    difficulty = 9 - abs(idx1 - idx2)
    return difficulty

# === Helper function for making crossmodal with feedback trials ===
def crossWF_pick_incorrect_tone(correct_tone, available_tones, current_diff, trial_num):
    attempts = 0
    while attempts < 30: # avoid infinite loops
        attempts += 1
        candidate = random.choice(available_tones)
        trial_diff = crossWF_calc_trial_diff(correct_tone, candidate)
        if ((current_diff + trial_diff) / trial_num) < 5 and ((current_diff + trial_diff) / trial_num) > 3:
            return candidate, trial_diff
    return candidate, trial_diff

# === Crossmodal with feedback ===
def crossmodal_with_feedback():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["crossmodal_wf_log"] = []
    participant_data["crossmodal_pause_durations"] = []
    event.clearEvents()

    print("Starting Crossmodal with feedback...")

    instruction_result = show_instructions(
        "INSTRUCTIONS – Learning Task\n\n"
        "In this section, you’ll see a SHAPE and hear a SOUND together.\n\n"
        "The same shape will be presented twice, each time with a different sound.\n"
        "Press ‘1’ with your LEFT index finger if the FIRST pair is correct.\n"
        "Press ‘0’ with your RIGHT index finger if the SECOND pair is correct.\n\n"
        "You’ll get FEEDBACK after each response.\n\n"
        "The correct pairings have been pre-assigned and are NOT based on the pairings you made previously.\n\n"
        "Please focus on learning the correct pairings.\n\n"
        "Try to respond as accurately and quickly as possible.\n\n"
        "Press SPACEBAR to begin.",
        ["space"]
    )
    if instruction_result == "s":
        print("Crossmodal with feedback skipped.")
        return "skip"

    try:
        print("Entering trial loop for Crossmodal with feedback...")
        local_stimuli = list(stimuli_pairs)
        crossmodal_trials = []

        # For each pair, create (approximately) balanced congruent-first vs congruent-second
        TRIALS_PER_PAIR = 15
        all_tones = [pair[1] for pair in stimuli_pairs]

        for img_file, audio_file in local_stimuli:
            available_tones = [snd for snd in all_tones if snd != audio_file]
            total_diff = 0
            # 7 of each order, and 1 extra randomly to total 15
            for i in range(TRIALS_PER_PAIR // 2):
                # Congruent first
                incorrect_tone, trial_diff = crossWF_pick_incorrect_tone(audio_file, available_tones, total_diff, ((i+1)*2)-1)
                total_diff += trial_diff
                crossmodal_trials.append((img_file, audio_file, [audio_file, incorrect_tone]))
                # Congruent second
                incorrect_tone, trial_diff = crossWF_pick_incorrect_tone(audio_file, available_tones, total_diff, (i+1)*2)
                total_diff += trial_diff
                crossmodal_trials.append((img_file, audio_file, [incorrect_tone, audio_file]))
            if TRIALS_PER_PAIR % 2 != 0:
                if random.random() < 0.5:
                    incorrect_tone, trial_diff = crossWF_pick_incorrect_tone(audio_file, available_tones, total_diff, TRIALS_PER_PAIR)
                    total_diff += trial_diff
                    crossmodal_trials.append((img_file, audio_file, [audio_file, incorrect_tone]))
                else:
                    incorrect_tone, trial_diff = crossWF_pick_incorrect_tone(audio_file, available_tones, total_diff, TRIALS_PER_PAIR)
                    total_diff += trial_diff
                    crossmodal_trials.append((img_file, audio_file, [incorrect_tone, audio_file]))

        random.shuffle(crossmodal_trials)

        correct_feedback = visual.ImageStim(win, image="green_tick.png", size=(0.2, 0.2), pos=(0, 0))
        incorrect_feedback = visual.ImageStim(win, image="red_cross.png", size=(0.2, 0.2), pos=(0, 0))

        fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
        prompt_sound2 = visual.TextStim(
            win,
            text="Press 1 (LEFT index) if FIRST pair is correct;\nPress 0 (RIGHT index) if SECOND pair is correct.",
            color="white", height=0.05, pos=(0, 0)
        )

        img_stim_left = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(-0.5, 0))
        img_stim_right = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0.5, 0))

        # Make the progress bar
        cx, cy = 0, -0.6
        finalwidth = 1.4
        left = cx - (finalwidth / 2)
        progress_bar = visual.Rect(
            win,
            width=0, height=0.05,  # start at 0%
            pos=(cx, cy),
            lineColor="white", fillColor="white",
            autoDraw=False, name="progressbar"
        )

        # Stimulus parameters
        STIMULUS_DURATION = 1.0  # Keep it as 1.0s for crossmodal block

        # Generate non-negative Gaussian jitters centered at 500 ms
        interTrialPause = sample_non_negative_normal(mean_ITI, sd_ITI, len(crossmodal_trials))
        interStimulusPause = sample_non_negative_normal(mean_ISI, sd_ISI, len(crossmodal_trials))

        # Record distribute information
        participant_data["crossmodal_pause_durations"].append({
            "interStimulusPause_mean": float(np.mean(interStimulusPause)),
            "interStimulusPause_std": float(np.std(interStimulusPause, ddof=0)),
            "interStimulusPause_min": float(np.min(interStimulusPause)),
            "interStimulusPause_max": float(np.max(interStimulusPause)),

            "interTrialPause_mean": float(np.mean(interTrialPause)),
            "interTrialPause_std": float(np.std(interTrialPause, ddof=0)),
            "interTrialPause_min": float(np.min(interTrialPause)),
            "interTrialPause_max": float(np.max(interTrialPause)),
        })

        for trial_index, (img_file, audio_file, tones) in enumerate(crossmodal_trials):
            event.clearEvents()
            if "escape" in event.getKeys(keyList=["escape"]):
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                return "skip"

            trial_clock = core.Clock()
            image_path = os.path.join(image_dir, img_file)
            trial_difficulty = crossWF_calc_trial_diff(tones[0], tones[1])

            # Update progress bar
            progress = trial_index / float((TRIALS_PER_PAIR * 10) - 1)  # progress fraction (0–1)
            width = finalwidth * progress
            progress_bar.width = width
            progress_bar.pos = (left + width/2,cy)
            progress_bar.autoDraw = True
            win.flip()

            # 1) Inter-Trial jitter (0.5s mean)
            win.flip()
            core.wait(interTrialPause[trial_index])

            # 2) shape + sound 1 (left) (0.5s)
            img_stim_left.image = image_path
            img_stim_left.draw()
            win.flip()
            main_sounds[tones[0]].stop()
            main_sounds[tones[0]].play()
            core.wait(STIMULUS_DURATION)

            # 3) fixation (0.5s)
            fixation.pos = (0, 0)
            fixation.draw()
            win.flip()
            core.wait(FIXATION_DURATION)

            # 4) Inter-Stimulus jitter (0.5s mean)
            win.flip()
            core.wait(interStimulusPause[trial_index])

            # 5) shape + sound 2 (right) (0.5s)
            img_stim_right.image = image_path
            img_stim_right.draw()
            win.flip()
            main_sounds[tones[1]].stop()
            main_sounds[tones[1]].play()
            core.wait(STIMULUS_DURATION)

            # Response
            event.clearEvents()
            prompt_sound2.draw()
            win.flip()
            trial_clock.reset()

            # Feedback Duration is 0.5s, handled below
            response = None
            
            while trial_clock.getTime() < 4:
                keys = event.getKeys(keyList=["1", "0", "escape", "s"])
                if "escape" in keys:
                    win.close(); core.quit()
                elif "s" in keys:
                    progress_bar.autoDraw = False
                    win.flip()
                    return "skip"
                elif keys:
                    response = keys[0]
                    break
                core.wait(0.01)

            if response is None:
                response = "NA"
            reaction_time = round(trial_clock.getTime(), 3)

            correct_sound = dict(stimuli_pairs).get(img_file)
            correct_answer = "1" if tones[0] == correct_sound else "0"

            participant_data["reaction time"].append(reaction_time)
            if response == correct_answer:
                participant_data["crossmodal with feedback correct"] += 1
                correct_feedback.draw()
            else:
                participant_data["crossmodal with feedback incorrect"] += 1
                incorrect_feedback.draw()
            win.flip()
            
            core.wait(0.5) # FEEDBACK DURATION (0.5s)

            # Record trial data
            participant_data["crossmodal_wf_log"].append({
                "trial_index": trial_index,
                "trial_type": "shape+2sounds",
                "stimulus": img_file,
                "audio": audio_file,
                "tones_order": tones,
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time,
                "trial_difficulty": trial_difficulty,
                "interStimulusPause": float(interStimulusPause[trial_index]),
                "interTrialPause": float(interTrialPause[trial_index])
            })

        progress_bar.autoDraw = False
        end_msg = visual.TextStim(
            win,
            text="You have completed this section.\n\nPress SPACEBAR to continue.",
            color="lightgrey", height=0.06, pos=(0, 0)
        )
        end_msg.draw()
        win.flip()
        event.waitKeys(keyList=["space"])

        print("Crossmodal with feedback completed successfully.")
        return "done"

    except Exception as e:
        print("Error during crossmodal with feedback:")
        traceback.print_exc()
        core.quit()

# === Triplets block == 
# the main fucnction calls the two triplets blocks in an order based on participant ID
def unisensory_triplets_block(version):
    try:
        participant_num = int(participant_id[-1])  # Sort participants in half by ID
    except ValueError:
        print("Participant ID not valid, randomizing block order")
        participant_num = random.randint(0, 9)

    unimodal_timer = core.Clock()

    if participant_num % 2 == 0:
        result = triplets_block_shapes()
        if result == "skip":
            print("Triplets block shapes skipped")
        else:
            diffcounts_shapes, trial_log1, stimuli = result
            duration = unimodal_timer.getTime()
            save_unimodal_to_excel(diffcounts_shapes, trial_log1, stimuli, duration, "Shape", f"First_{version}")

        unimodal_timer.reset()
        result = triplets_block_sounds()
        if result == "skip":
            print("Triplets block sounds skipped")
        else:
            diffcounts_sounds, trial_log2, stimuli = result
            duration = unimodal_timer.getTime()
            save_unimodal_to_excel(diffcounts_sounds, trial_log2, stimuli, duration, "Tone", f"Second_{version}")

    else:
        result = triplets_block_sounds()
        if result == "skip":
            print("Triplets block sounds skipped")
        else:
            diffcounts_sounds, trial_log2, stimuli = result
            duration = unimodal_timer.getTime()
            save_unimodal_to_excel(diffcounts_sounds, trial_log2, stimuli, duration, "Tone", f"First_{version}")

        unimodal_timer.reset()
        result = triplets_block_shapes()
        if result == "skip":
            print("Triplets block shapes skipped")
        else:
            diffcounts_shapes, trial_log1, stimuli = result
            duration = unimodal_timer.getTime()
            save_unimodal_to_excel(diffcounts_shapes, trial_log1, stimuli, duration, "Shape", f"Second_{version}")

def triplets_block_shapes():
    # Setup
    img_stim_left = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(-0.5, 0))
    img_stim_center = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0, 0))
    img_stim_right = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0.5, 0))
    mouse = event.Mouse(win=win)

    # Fixed canonical mapping: index 0 -> shape_01.png, ..., index 9 -> shape_10.png
    all_shapes = [f"shape_{i:02d}.png" for i in range(1, 11)]
    numshapes = len(all_shapes)
    image_path_list = [os.path.join(image_dir, img_file) for img_file in all_shapes]

    diff_cts = np.zeros((numshapes, numshapes), dtype=int)

    instructions = visual.TextStim(
        win,
        text="Which one is the odd one out?",
        pos=(0, 0.55),
        height=0.08,
        color="lightgray",
        wrapWidth=1.4,
        alignText="center",
    )

    # Same fixed 60 triplets for everyone, shuffled fresh each run
    trial_list = FIXED_SHAPE_TRIPLETS.copy()
    random.shuffle(trial_list)
    numtrials = len(trial_list)
    trial_log = []

    print(f"Shape triplets shown: {numtrials}")
    print(f"Shape graph connected: {check_pair_graph_connected(FIXED_SHAPE_TRIPLETS, numshapes)}")

    instr_result = show_instructions(
        "INSTRUCTIONS\n\n"
        "In this section you will be presented with three shapes.\n"
        "Click on the shape you think is the odd one out.\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instr_result == "s":
        return "skip"

    # Progress bar
    cx, cy = 0, -0.6
    finalwidth = 1.4
    left = cx - (finalwidth / 2)
    progress_bar = visual.Rect(
        win,
        width=0.001,
        height=0.05,
        pos=(cx, cy),
        lineColor="white",
        fillColor="white",
        autoDraw=False,
        name="progress_bar"
    )

    for trial_idx, base_trial in enumerate(trial_list):
        event.clearEvents()
        if "escape" in event.getKeys(keyList=["escape"]):
            win.close()
            core.quit()
        if "s" in event.getKeys(keyList=["s"]):
            progress_bar.autoDraw = False
            instructions.autoDraw = False
            img_stim_left.autoDraw = False
            img_stim_center.autoDraw = False
            img_stim_right.autoDraw = False
            win.flip()
            return "skip"

        # Randomize only the left/center/right presentation order within this trial
        presented_trial = list(base_trial)
        random.shuffle(presented_trial)
        presented_trial = tuple(presented_trial)

        instructions.draw()
        instructions.autoDraw = True

        img_stim_left.image = image_path_list[presented_trial[0]]
        img_stim_center.image = image_path_list[presented_trial[1]]
        img_stim_right.image = image_path_list[presented_trial[2]]
        img_stim_left.autoDraw = True
        img_stim_center.autoDraw = True
        img_stim_right.autoDraw = True
        win.flip()

        progress = trial_idx / float(numtrials - 1)
        width = finalwidth * progress
        progress_bar.width = width
        progress_bar.pos = (left + width / 2, cy)
        progress_bar.autoDraw = True
        win.flip()

        trial_clock = core.Clock()
        mouse.clickReset()
        prev_buttons = mouse.getPressed()
        clicked_index = None

        while trial_clock.getTime() < 5:
            keys = event.getKeys(keyList=["escape", "s"])
            if "escape" in keys:
                win.close()
                core.quit()
            if "s" in keys:
                progress_bar.autoDraw = False
                instructions.autoDraw = False
                img_stim_left.autoDraw = False
                img_stim_center.autoDraw = False
                img_stim_right.autoDraw = False
                win.flip()
                return "skip"

            buttons = mouse.getPressed()
            if any(buttons) and not any(prev_buttons):
                if img_stim_left.contains(mouse):
                    clicked_index = presented_trial[0]
                elif img_stim_center.contains(mouse):
                    clicked_index = presented_trial[1]
                elif img_stim_right.contains(mouse):
                    clicked_index = presented_trial[2]

                if clicked_index is not None:
                    ordered = []
                    for stim_idx in presented_trial:
                        if stim_idx == clicked_index:
                            ordered.insert(0, stim_idx)
                        else:
                            ordered.append(stim_idx)

                    # Chosen odd-one-out is treated as more dissimilar
                    diff_cts[ordered[0], ordered[1]] += 1
                    diff_cts[ordered[1], ordered[0]] += 1
                    diff_cts[ordered[0], ordered[2]] += 1
                    diff_cts[ordered[2], ordered[0]] += 1

                    # Non-chosen pair treated as relatively similar
                    diff_cts[ordered[1], ordered[2]] -= 1
                    diff_cts[ordered[2], ordered[1]] -= 1

                    trial_log.append([presented_trial, ordered[0]])
                    break

            prev_buttons = buttons
            core.wait(0.01)

    progress_bar.autoDraw = False
    instructions.autoDraw = False
    img_stim_left.autoDraw = False
    img_stim_center.autoDraw = False
    img_stim_right.autoDraw = False

    end_msg = visual.TextStim(
        win,
        text="You have completed this section.\n\nPress SPACEBAR to continue.",
        color="lightgrey",
        height=0.06,
        pos=(0, 0)
    )
    end_msg.draw()
    win.flip()
    event.waitKeys(keyList=["space"])

    return diff_cts, trial_log, all_shapes


def triplets_block_sounds():
    all_sounds = [pair[1] for pair in stimuli_pairs]
    numsounds = len(all_sounds)
    diff_cts = np.zeros((numsounds, numsounds), dtype=int)

    trial_list = FIXED_SOUND_TRIPLETS.copy()
    random.shuffle(trial_list)
    numtrials = len(trial_list)
    trial_log = []

    print(f"Sound triplets shown: {numtrials}")
    print(f"Sound graph connected: {check_pair_graph_connected(FIXED_SOUND_TRIPLETS, numsounds)}")

    STIMULUS_DURATION_UNISENSORY = 0.8

    instr_result = show_instructions(
        "INSTRUCTIONS\n\n"
        "You will hear three sounds.\n"
        "Click the sound that you think is the odd one out.\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instr_result == "s":
        return "skip"

    def note_left():
        return visual.ImageStim(
            win,
            image="musical_note.png",
            pos=(-0.5, 0),
            size=(0.18, 0.18),
            name="note_left"
        )

    def note_center():
        return visual.ImageStim(
            win,
            image="musical_note.png",
            pos=(0.0, 0),
            size=(0.18, 0.18),
            name="note_center"
        )

    def note_right():
        return visual.ImageStim(
            win,
            image="musical_note.png",
            pos=(0.5, 0),
            size=(0.18, 0.18),
            name="note_right"
        )

    note1 = note_left()
    note2 = note_center()
    note3 = note_right()
    notes = [note1, note2, note3]

    def button(label, center_pos, color):
        padding = (0.14, 0.05)
        w, h = padding[0] * 2.4, padding[1] * 2.4
        rect = visual.Rect(win, width=w, height=h, pos=center_pos, fillColor=color, lineColor=None, opacity=1)
        text = visual.TextStim(win, text=label, pos=center_pos, height=0.06, color="white")
        return rect, text

    rone_rect, rone_text = button("Replay", (-0.5, -0.3), "#4C7BF1")
    rtwo_rect, rtwo_text = button("Replay", (0, -0.3), "#4C7BF1")
    rthree_rect, rthree_text = button("Replay", (0.5, -0.3), "#4C7BF1")

    instructions = visual.TextStim(
        win,
        text="Which one is the odd one out?",
        pos=(0, 0.55),
        height=0.08,
        color="lightgray",
        wrapWidth=1.4,
        alignText="center",
    )

    cx, cy = 0, -0.6
    finalwidth = 1.4
    left = cx - (finalwidth / 2)
    progress_bar = visual.Rect(
        win,
        width=0.001,
        height=0.05,
        pos=(cx, cy),
        lineColor="white",
        fillColor="white",
        name="progressbar"
    )

    mouse = event.Mouse(win=win)

    for trial_idx, base_trial in enumerate(trial_list):
        event.clearEvents()
        mouse.clickReset()

        if "escape" in event.getKeys(keyList=["escape"]):
            win.close()
            core.quit()
        if "s" in event.getKeys(keyList=["s"]):
            return "skip"

        # Randomize only the presentation order within this triplet
        presented_trial = list(base_trial)
        random.shuffle(presented_trial)
        presented_trial = tuple(presented_trial)

        for n in notes:
            n.draw()
            n.autoDraw = True

        progress = trial_idx / float(numtrials - 1)
        width = finalwidth * progress
        progress_bar.width = width
        progress_bar.pos = (left + width / 2, cy)
        progress_bar.autoDraw = True
        win.flip()

        instructions.draw()
        instructions.autoDraw = True

        main_sounds[all_sounds[presented_trial[0]]].stop()
        main_sounds[all_sounds[presented_trial[0]]].play()
        highlight = highlight_note(notes[0])
        highlight.draw()
        notes[0].draw()
        win.flip()
        core.wait(STIMULUS_DURATION_UNISENSORY + 0.4)

        main_sounds[all_sounds[presented_trial[1]]].stop()
        main_sounds[all_sounds[presented_trial[1]]].play()
        highlight = highlight_note(notes[1])
        highlight.draw()
        notes[1].draw()
        win.flip()
        core.wait(STIMULUS_DURATION_UNISENSORY + 0.4)

        main_sounds[all_sounds[presented_trial[2]]].stop()
        main_sounds[all_sounds[presented_trial[2]]].play()
        highlight = highlight_note(notes[2])
        highlight.draw()
        notes[2].draw()
        win.flip()
        core.wait(STIMULUS_DURATION_UNISENSORY + 0.4)

        clicked = False
        was_down = False
        canreplay1 = True
        canreplay2 = True
        canreplay3 = True

        while not clicked:
            if "escape" in event.getKeys(keyList=["escape"]):
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                for n in notes:
                    n.autoDraw = False
                instructions.autoDraw = False
                progress_bar.autoDraw = False
                win.flip()
                return "skip"

            rone_rect.fillColor = "#4C7BF1" if canreplay1 else "#565656"
            rtwo_rect.fillColor = "#4C7BF1" if canreplay2 else "#565656"
            rthree_rect.fillColor = "#4C7BF1" if canreplay3 else "#565656"

            rone_rect.draw(); rone_text.draw()
            rtwo_rect.draw(); rtwo_text.draw()
            rthree_rect.draw(); rthree_text.draw()
            win.flip()

            is_down = mouse.getPressed()[0] == 1

            if is_down and not was_down:
                if notes[0].contains(mouse):
                    result = [presented_trial[0], presented_trial[1], presented_trial[2]]
                    clicked = True
                elif notes[1].contains(mouse):
                    result = [presented_trial[1], presented_trial[0], presented_trial[2]]
                    clicked = True
                elif notes[2].contains(mouse):
                    result = [presented_trial[2], presented_trial[0], presented_trial[1]]
                    clicked = True

                elif (abs(mouse.getPos()[0] - rone_rect.pos[0]) <= rone_rect.width / 2 and
                      abs(mouse.getPos()[1] - rone_rect.pos[1]) <= rone_rect.height / 2):
                    if canreplay1:
                        main_sounds[all_sounds[presented_trial[0]]].stop()
                        main_sounds[all_sounds[presented_trial[0]]].play()
                        highlight = highlight_note(notes[0])
                        highlight.draw()
                        win.flip()
                        core.wait(STIMULUS_DURATION_UNISENSORY)
                        canreplay1 = False

                elif (abs(mouse.getPos()[0] - rtwo_rect.pos[0]) <= rtwo_rect.width / 2 and
                      abs(mouse.getPos()[1] - rtwo_rect.pos[1]) <= rtwo_rect.height / 2):
                    if canreplay2:
                        main_sounds[all_sounds[presented_trial[1]]].stop()
                        main_sounds[all_sounds[presented_trial[1]]].play()
                        highlight = highlight_note(notes[1])
                        highlight.draw()
                        win.flip()
                        core.wait(STIMULUS_DURATION_UNISENSORY)
                        canreplay2 = False

                elif (abs(mouse.getPos()[0] - rthree_rect.pos[0]) <= rthree_rect.width / 2 and
                      abs(mouse.getPos()[1] - rthree_rect.pos[1]) <= rthree_rect.height / 2):
                    if canreplay3:
                        main_sounds[all_sounds[presented_trial[2]]].stop()
                        main_sounds[all_sounds[presented_trial[2]]].play()
                        highlight = highlight_note(notes[2])
                        highlight.draw()
                        win.flip()
                        core.wait(STIMULUS_DURATION_UNISENSORY)
                        canreplay3 = False

                if clicked:
                    diff_cts[result[0], result[1]] += 1
                    diff_cts[result[1], result[0]] += 1
                    diff_cts[result[0], result[2]] += 1
                    diff_cts[result[2], result[0]] += 1

                    diff_cts[result[1], result[2]] -= 1
                    diff_cts[result[2], result[1]] -= 1

                    trial_log.append([presented_trial, result[0]])
                    core.wait(0.2)

            was_down = is_down

        win.flip()
        core.wait(0.5)

    for n in notes:
        n.autoDraw = False
    instructions.autoDraw = False
    progress_bar.autoDraw = False

    end_msg = visual.TextStim(
        win,
        text="You have completed this section.\n\nPress SPACEBAR to continue.",
        color="lightgrey",
        height=0.06,
        pos=(0, 0)
    )
    end_msg.draw()
    win.flip()
    event.waitKeys(keyList=["space"])

    return diff_cts, trial_log, all_sounds

# === Helper function to highlight a note stimulus ===
def highlight_note(note_stim, on=True, color='red', scale=1.15):
    w, h = note_stim.size
    return visual.Rect(
        win,
        width=w * scale,
        height=h * scale,
        lineColor=color if on else None,
        lineWidth=3 if on else 0,
        fillColor=None,
        pos=note_stim.pos,
    )

# === Always collect participant ID and set up paths before anything else ===
participant_id = get_participant_id()
participant_data = {
    "participant_id": participant_id,
    "task order": "",
    "crossmodal with feedback correct": 0,
    "crossmodal with feedback incorrect": 0,
    "reaction time": [],
    "crossmodal_wf_log": [],
    "free_pairings": [],
}

# Set image/audio directories (adjust as needed for your experiment)
image_dir = "./generated_shapes"
audio_dir = "./generated_sounds"

# === Create PsychoPy window early so it's available for all functions ===
try:
    win = visual.Window(fullscr=True, color="gray", units="norm", allowGUI=True)
except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()


# === Preload audio ===
main_sounds = preload_sounds(audio_dir)

# === Experiment flow ===

# Free Pairing — Block 1 (welcome text)
intro_text_block1 = (
    "Welcome to the experiment!\n\n"
    "On the next screen, you’ll see a list of shapes and a list of sounds.\n"
    "Click a musical note to hear its sound,\n"
    "then click the shape you think goes best with that sound.\n\n"
    "Press SPACEBAR to continue."
)
result = free_pairings_block(intro_text_block1, "First")
if result == "skip":
    print("Free pairings block 1 skipped.")
save_free_pairings_to_excel("free_pairings_block1.xlsx")

# Unisensory Block
unisensory_triplets_block("Pre-Crossmodal")

# Crossmodal with Feedback (keys: 1 = FIRST, 0 = SECOND; use left/right index fingers)
result = crossmodal_with_feedback()
if result == "skip":
    print("Crossmodal with feedback skipped.")
save_crossmodal_with_feedback_to_excel()

# Unisensory Block
unisensory_triplets_block("Post-Crossmodal")

# Free Pairing — Block 2 (non-redundant intro text)
intro_text_block2 = (
    "In this section, you will try to remember the pairings you learned earlier.\n\n"
    "Click a musical note to hear its sound,\n"
    "then click the shape you think is correctly paired with that sound based on what you have learned.\n\n"
    "Press SPACEBAR to continue."
)
result = free_pairings_block(intro_text_block2, "Second")
if result == "skip":
    print("Free pairings block 2 skipped.")
save_free_pairings_to_excel("free_pairings_block2.xlsx")

# End Survey
run_end_survey_adv()

# Save again (redundant but safe)
save_crossmodal_with_feedback_to_excel()

# Cleanup
win.close()
core.quit()