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

from psychopy import visual, core, event, sound

##### This version runs: Free Pairing (Block 1) -> Crossmodal w/ Feedback -> Free Pairing (Block 2) -> End Survey
##### Second free-pairing block uses a different intro text; the two free-pairing outputs save to different filenames.
##### Response keys in the crossmodal block are now: '1' (FIRST, left index finger) and '0' (SECOND, right index finger).


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


# === Save helpers (only the ones we actually use) ===
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
    df = pd.DataFrame(participant_data.get("crossmodal_wf_log", []))
    excel_filename = os.path.join(participant_folder, "crossmodal_wf_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Crossmodal with feedback data saved to {excel_filename}")


# === End-of-experiment survey ===
def run_end_survey():
    """Prompt participant for survey responses on the PsychoPy window and save to Excel."""
    survey_questions = [
        "Which features of the shapes did you focus on to help with learning?",
        "Which features of the sounds did you focus on to help with learning?",
        "Were certain shape–sound pairings easier to remember than others? Why?",
        "Did you use any specific strategies to remember the pairings?",
        "Did you notice any patterns in the stimuli that helped you?",
        "How confident were you in your answers during the test block? Why?",
        "Did your strategy change across the blocks? If so, how and why?",
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
def free_pairings_block(intro_text):
    """
    Shows shapes on the top row and musical notes on the bottom row.
    Participant clicks a note to play it, then clicks a shape to pair them.
    Saves into participant_data['free_pairings'].
    """
    global participant_data
    participant_data["free_pairings"] = []

    # Use shape_01.png–shape_10.png and sound_01.wav–sound_10.wav
    shape_files = [f"shape_{i:02d}.png" for i in range(1, 11)]
    tone_files = [f"sound_{i:02d}.wav" for i in range(1, 11)]

    # Randomize the order of shapes and tones for display only
    random.shuffle(shape_files)
    random.shuffle(tone_files)

    # Evenly space shapes and tones
    num_pairs = len(shape_files)
    shape_positions = np.linspace(-0.9, 0.9, num_pairs)
    tone_positions = np.linspace(-0.9, 0.9, num_pairs)

    shapes = []
    tones = []
    tone_sounds = {}

    for i, filename in enumerate(shape_files):
        stim = visual.ImageStim(
            win,
            image=os.path.join(image_dir, filename),
            pos=(shape_positions[i], 0.5),
            size=(0.15, 0.25)
        )
        shapes.append({"stim": stim, "file": filename})

    for i, filename in enumerate(tone_files):
        stim = visual.ImageStim(
            win,
            image="musical_note.png",  # icon for all tones
            pos=(tone_positions[i], -0.5),
            size=(0.1, 0.1)
        )
        tones.append({"stim": stim, "file": filename})
        tone_sounds[filename] = main_sounds[filename]

    mouse = event.Mouse(visible=True)
    selected_tone = None

    # Intro instructions
    instr_result = show_instructions(intro_text, ["space"])
    if instr_result == "s":
        return "skip"

    while True:
        for shape in shapes:
            shape["stim"].draw()
        for tone in tones:
            tone["stim"].draw()

        if all("paired_shape" in t for t in tones):
            ready_msg = visual.TextStim(
                win,
                text="All sounds paired – press SPACEBAR to continue",
                color="lightgrey",
                height=0.05,
                pos=(0, -0.85)
            )
            ready_msg.draw()

        win.flip()

        buttons = mouse.getPressed()
        if buttons[0]:
            core.wait(0.05)
            tone_clicked = next((t for t in tones if t["stim"].contains(mouse)), None)

            if tone_clicked is not None:
                tone_sounds[tone_clicked["file"]].play()
                selected_tone = tone_clicked
            elif selected_tone is not None:
                for shape in shapes:
                    if shape["stim"].contains(mouse):
                        new_pos = (shape["stim"].pos[0], shape["stim"].pos[1] - 0.3)
                        selected_tone["stim"].pos = new_pos
                        selected_tone["paired_shape"] = shape["file"]
                        selected_tone["new_pos"] = new_pos
                        selected_tone = None
                        break
            while any(mouse.getPressed()):
                core.wait(0.01)

        keys = event.getKeys(keyList=["escape", "space", "s"])
        if "escape" in keys:
            win.close(); core.quit()
        elif "s" in keys:
            return "skip"
        elif "space" in keys and all("paired_shape" in t for t in tones):
            break

    # Record pairings
    for tone in tones:
        if "paired_shape" in tone:
            sound_index = int(tone["file"].split('_')[1].split('.')[0])
            shape_index = int(next(s["file"] for s in shapes if s["file"] == tone["paired_shape"]).split('_')[1].split('.')[0])
            participant_data["free_pairings"].append({
                "tone_file": tone["file"],
                "shape_file": tone["paired_shape"],
                "sound_index": sound_index,
                "shape_index": shape_index,
                "tone_pos": tone["new_pos"],
                "shape_pos": next(s["stim"].pos for s in shapes if s["file"] == tone["paired_shape"])
            })

    print("Pairings recorded:", participant_data["free_pairings"])
    win.flip()
    return 'done'


# === Crossmodal with feedback ===
def crossmodal_with_feedback():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["crossmodal_wf_log"] = []
    event.clearEvents()

    print("Starting Crossmodal with feedback...")

    instruction_result = show_instructions(
        "INSTRUCTIONS – Crossmodal Block with Feedback\n\n"
        "In this block, you’ll see a SHAPE and hear a SOUND together.\n\n"
        "The same shape will be presented twice, each time with a different sound.\n"
        "Only ONE of the shape-sound pairs is correct.\n\n"
        "Press ‘1’ with your LEFT index finger if the FIRST pair is correct.\n"
        "Press ‘0’ with your RIGHT index finger if the SECOND pair is correct.\n\n"
        "You’ll get FEEDBACK after each response.\n\n"
        "Press SPACEBAR to begin.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"
    if instruction_result != "space":
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
            # 7 of each order, and 1 extra randomly to total 15
            for _ in range(TRIALS_PER_PAIR // 2):
                # Congruent first
                incorrect_tone = random.choice(available_tones)
                crossmodal_trials.append((img_file, audio_file, [audio_file, incorrect_tone]))
                # Congruent second
                incorrect_tone = random.choice(available_tones)
                crossmodal_trials.append((img_file, audio_file, [incorrect_tone, audio_file]))
            if TRIALS_PER_PAIR % 2 != 0:
                if random.random() < 0.5:
                    incorrect_tone = random.choice(available_tones)
                    crossmodal_trials.append((img_file, audio_file, [audio_file, incorrect_tone]))
                else:
                    incorrect_tone = random.choice(available_tones)
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

        for trial_index, (img_file, audio_file, tones) in enumerate(crossmodal_trials):
            event.clearEvents()
            if "escape" in event.getKeys(keyList=["escape"]):
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                return "skip"

            trial_clock = core.Clock()
            image_path = os.path.join(image_dir, img_file)

            # 1) shape + sound 1 (left)
            img_stim_left.image = image_path
            img_stim_left.draw()
            win.flip()
            main_sounds[tones[0]].stop()
            main_sounds[tones[0]].play()
            core.wait(STIMULUS_DURATION)

            # 2) fixation
            fixation.pos = (0, 0)
            fixation.draw()
            win.flip()
            core.wait(FIXATION_DURATION)

            # 3) shape + sound 2 (right)
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

            response = None
            while trial_clock.getTime() < 4:
                keys = event.getKeys(keyList=["1", "0", "escape", "s"])
                if "escape" in keys:
                    win.close(); core.quit()
                elif "s" in keys:
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
            core.wait(0.5)  # feedback duration

            participant_data["crossmodal_wf_log"].append({
                "trial_index": trial_index,
                "trial_type": "shape+2sounds",
                "stimulus": img_file,
                "audio": audio_file,
                "tones_order": tones,
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time,
            })

        end_msg = visual.TextStim(
            win,
            text="You have completed this block.\n\nPress SPACEBAR to continue.",
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
result = free_pairings_block(intro_text_block1)
if result == "skip":
    win.close(); core.quit()
save_free_pairings_to_excel("free_pairings_block1.xlsx")

# Crossmodal with Feedback (keys: 1 = FIRST, 0 = SECOND; use left/right index fingers)
result = crossmodal_with_feedback()
if result == "skip":
    win.close(); core.quit()
save_crossmodal_with_feedback_to_excel()

# Free Pairing — Block 2 (non-redundant intro text)
intro_text_block2 = (
    "Next, you’ll complete another free-pairing block.\n\n"
    "Click a musical note to hear its sound,\n"
    "then click the shape you think goes best with that sound.\n\n"
    "Press SPACEBAR to continue."
)
result = free_pairings_block(intro_text_block2)
if result == "skip":
    win.close(); core.quit()
save_free_pairings_to_excel("free_pairings_block2.xlsx")

# End Survey
run_end_survey()

# Save again (redundant but safe)
save_crossmodal_with_feedback_to_excel()

# Cleanup
win.close()
core.quit()
