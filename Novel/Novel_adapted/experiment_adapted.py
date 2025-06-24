import os
import random
random.seed(42)  # Added fixed seed for consistent random pairings
import pandas as pd
import csv
import time
from psychopy import visual, core, event, sound, prefs, gui
import numpy as np
import traceback

# Configure sound preferences
prefs.hardware['audioLib'] = ['pygame', 'sounddevice']
prefs.general['audioDevice'] = ['default']

# Set the path where images and sounds are stored
image_dir = "./generated_shapes2"  # CHANGED from "./generated_shapes"
audio_dir = "./generated_sounds"
colour_dir = "./generated_colours"
paired_sound_dir = "./paired_sounds"

# Use the same directories for test set as for main set
test_image_dir = image_dir
test_audio_dir = audio_dir

# Store participant data
participant_data = {
    "task order": "",
    "time on active task": 0,
    "click data": {},
    "block 2 correct": 0,
    "block 2 incorrect": 0,
    "reaction time": [],
    "block 2 log": [],
}

# Generate ordered list of paired stimuli (shape_01.png with sound_01.wav, etc.)
stimuli_pairs = [
    ("shape_01.png", "sound_04.wav"),
    ("shape_02.png", "sound_03.wav"),
    ("shape_03.png", "sound_06.wav"),
    ("shape_04.png", "sound_05.wav"),
    ("shape_05.png", "sound_01.wav"),
    ("shape_06.png", "sound_02.wav"),
]

# Test set pairings: use the same as stimuli_pairs
test_pairs = list(stimuli_pairs)

# Preload all sound objects for main and test sets
def preload_sounds(audio_dir):
    sound_dict = {}
    for fname in sorted([f for f in os.listdir(audio_dir) if f.startswith("sound_") and f.endswith(".wav")]):
        sound_dict[fname] = sound.Sound(os.path.join(audio_dir, fname))
    return sound_dict

main_sounds = preload_sounds(audio_dir)
test_sounds = preload_sounds(test_audio_dir)


# Define utility functions first
def get_participant_id():
    """Prompt for participant ID and handle existing data."""
    info = {"Participant ID": ""}
    dlg = gui.DlgFromDict(info, title="Participant Info")
    if not dlg.OK:
        core.quit()
    participant_id = info["Participant ID"]

    # Create participant data folder if it doesn't exist
    participant_folder = os.path.join("./participant_data2", participant_id)
    if not os.path.exists(participant_folder):
        os.makedirs(participant_folder)
    else:
        # Always overwrite existing data
        data_files = [f for f in os.listdir(participant_folder) if os.path.isfile(os.path.join(participant_folder, f))]
        for file in data_files:
            os.remove(os.path.join(participant_folder, file))

    return participant_id
    

def save_block1_crossmodal_to_excel():
    # Save block 1 data to Excel in the participant folder as block1_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data2", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("block1_crossmodal_log", []))
    excel_filename = os.path.join(participant_folder, "block1_crossmodal_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Block 1 data saved to {excel_filename}")

def save_block2_unimodal_to_excel():
    # Save block 2 data to Excel in the participant folder as block2_unimodal_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data2", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("block2_unimodal_log", []))
    excel_filename = os.path.join(participant_folder, "block2_unimodal_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Block 2 data saved to {excel_filename}")

def save_block3_test_to_excel():
    # Save block 3 data to Excel in the participant folder as block3_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data2", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("block3_test_log", []))
    excel_filename = os.path.join(participant_folder, "block3_test_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Block 3 data saved to {excel_filename}")

def show_instructions(text, key_list):
    """Display instructions and wait for a key in key_list. Returns the key pressed."""
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

# Define block functions next

# Block 1 - Crossmodal

def block1_crossmodal():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["block1_crossmodal_log"] = []
    event.clearEvents()

    print("Starting Block 1 Crossmodal...")

    instruction_result = show_instructions(
        "Block 1 Task Instructions: \n\n"
        "You will be presented with a shape and two sounds.\n"
        "Press '1' if the first sound matches the shape, '2' if the second sound matches the shape. \n"
        "You will receive feedback after each response.\n\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"
    if instruction_result != "space":
        print("Block 1 Crossmodal skipped.")
        return "skip"

    try:
        print("Entering trial loop for Block 1 Crossmodal...")
        local_stimuli = list(stimuli_pairs)
        random.shuffle(local_stimuli)
        crossmodal_trials = local_stimuli * 33  # 6 pairs × 33 = 198 trials
        random.shuffle(crossmodal_trials)

        correct_feedback = visual.ImageStim(win, image="green_tick.png", size=(0.2, 0.2), pos=(0, 0))
        incorrect_feedback = visual.ImageStim(win, image="red_cross.png", size=(0.2, 0.2), pos=(0, 0))

        total_trials = len(crossmodal_trials)
        progress_value = 0.0
        bar_width = 0.5
        bar_height = 0.07
        bar_y = -0.7
        left_edge = -bar_width / 2.0

        progress_bg = visual.ShapeStim(
            win,
            vertices=[(left_edge, bar_y - bar_height / 2),
                      (left_edge + bar_width, bar_y - bar_height / 2),
                      (left_edge + bar_width, bar_y + bar_height / 2),
                      (left_edge, bar_y + bar_height / 2)],
            fillColor='darkgrey',
            lineColor='white',
            closeShape=True
        )

        def create_progress_bar(p_value):
            x1 = left_edge
            x2 = left_edge + (p_value * bar_width)
            fillColor = 'blue'
            vertices = [(x1, bar_y - bar_height / 2),
                        (x2, bar_y - bar_height / 2),
                        (x2, bar_y + bar_height / 2),
                        (x1, bar_y + bar_height / 2)]
            return visual.ShapeStim(
                win,
                vertices=vertices,
                fillColor=fillColor,
                lineColor=None,
                closeShape=True
            )

        progress_bar = create_progress_bar(progress_value)

        TRIALS_BEFORE_BREAK = 33
        total_trials = len(crossmodal_trials)

        fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
        prompt_sound2 = visual.TextStim(win, text="Press 1 if FIRST sound matches; 2 if SECOND sound matches.",
                                        color="white", height=0.05, pos=(0, 0))
        img_stim = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0, 0))

        for trial_index, (img_file, audio_file) in enumerate(crossmodal_trials):
            event.clearEvents()
            if "escape" in event.getKeys():
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                return "skip"

            trial_clock = core.Clock()
            image_path = os.path.join(image_dir, img_file)
            available_tones = [snd for snd in [pair[1] for pair in stimuli_pairs] if snd != audio_file]
            incorrect_tone = random.choice(available_tones)
            tones = [audio_file, incorrect_tone]
            random.shuffle(tones)

            # --- Fixation before first stimulus ---
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(0.5)
            # -------------------------------------

            # Show the same image twice, each for 1.5s, with each tone
            for i in range(2):
                img_stim.image = image_path
                img_stim.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                tone = main_sounds[tones[i]]  # Use preloaded sound
                tone.play()
                core.wait(1.0)
                if i == 0:
                    fixation.draw()
                    progress_bg.draw()
                    progress_bar.draw()
                    win.flip()
                    core.wait(0.5)
                else:
                    core.wait(0.5)

            prompt_sound2.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip(); trial_clock.reset()

            response = None
            while trial_clock.getTime() < 5:
                keys = event.getKeys(keyList=["1", "2", "escape", "s"])
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
            correct_answer = "1" if tones[0] == correct_sound else "2"

            participant_data["reaction time"].append(reaction_time)
            if response == correct_answer:
                participant_data["block 1 correct"] += 1
                correct_feedback.draw()
            else:
                participant_data["block 1 incorrect"] += 1
                incorrect_feedback.draw()
            win.flip()
            core.wait(1.0)

            progress_value += 1.0 / total_trials
            progress_bar = create_progress_bar(progress_value)

            try:
                participant_data["block1_crossmodal_log"].append({
                    "trial_index": trial_index,
                    "trial_type": "shape+2sounds",
                    "stimulus": img_file,
                    "audio": audio_file,
                    "tones_order": tones,
                    "correct_answer": correct_answer,
                    "response": response,
                    "reaction_time": reaction_time,
                    "pairings": list(stimuli_pairs),
                    "order": tones,
                })
            except Exception as log_err:
                print(f"Logging error at trial {trial_index}:")
                print("tones =", tones)
                print("correct_answer =", correct_answer)
                print("response =", response)
                traceback.print_exc()
                core.quit()

            event.clearEvents()

            if (trial_index + 1) % TRIALS_BEFORE_BREAK == 0 and (trial_index + 1) < total_trials:
                break_msg = visual.TextStim(
                    win,
                    text=(f"You may take a short break.\n\n"
                          "Press SPACEBAR when you are ready to continue."),
                    color="lightgrey", height=0.06, pos=(0, 0)
                )
                break_msg.draw()
                win.flip()
                keys = event.waitKeys(keyList=["space", "s"])
                if "s" in keys:
                    return "skip"
                progress_bar = create_progress_bar(progress_value)

        end_msg = visual.TextStim(
            win,
            text="You have completed Block 1.\n\nPress SPACEBAR to continue.",
            color="lightgrey", height=0.06, pos=(0, 0)
        )
        end_msg.draw()
        win.flip()
        keys = event.waitKeys(keyList=["space", "s"])
        if "s" in keys:
            return "skip"

        print("Block 1 completed successfully.")
        return "done"

    except Exception as e:
        print("Error during block 1 crossmodal:")
        traceback.print_exc()
        core.quit()

# Block 2 - Unimodal

def block2_unimodal():
    global participant_data
    participant_data["block2_unimodal_log"] = []
    event.clearEvents()

    print("Starting Block 2 Unimodal...")

    instruction_result = show_instructions(
        "Block 2 Task Instructions: \n\n"
        "You will complete two types of trials:\n"
        "1. Visual only: You will see a shape and a colour presented side by side.\n"
        "2. Auditory only: You will hear two sounds in sequence.\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"
    if instruction_result != "space":
        print("Block 2 Unimodal skipped.")
        return "skip"

    # Prepare trial lists
    shapes = [f"shape_{i:02d}.png" for i in range(1, 7)]
    colours = [f"colour_{i:02d}.png" for i in range(1, 7)]
    sounds = [f"sound_{i:02d}.wav" for i in range(1, 7)]
    paired_sounds = [f"paired_{i:02d}.wav" for i in range(1, 7)]

    # Visual only trials: pair each shape with a colour (1:1 mapping)
    visual_trials = list(zip(shapes, colours))
    # Auditory only trials: pair each sound with a paired sound (1:1 mapping)
    auditory_trials = list(zip(sounds, paired_sounds))

    # Combine and randomize trial order
    unimodal_trials = []
    for v, a in zip(visual_trials, auditory_trials):
        unimodal_trials.append(("visual", v[0], v[1]))
        unimodal_trials.append(("auditory", a[0], a[1]))
    random.shuffle(unimodal_trials)
    unimodal_trials = unimodal_trials * 33  # 6 pairs × 2 × 33 = 396 trials
    random.shuffle(unimodal_trials)

    total_trials = len(unimodal_trials)
    progress_value = 0.0
    bar_width = 0.5
    bar_height = 0.07
    bar_y = -0.7
    left_edge = -bar_width / 2.0

    progress_bg = visual.ShapeStim(
        win,
        vertices=[(left_edge, bar_y - bar_height / 2),
                  (left_edge + bar_width, bar_y - bar_height / 2),
                  (left_edge + bar_width, bar_y + bar_height / 2),
                  (left_edge, bar_y + bar_height / 2)],
        fillColor='darkgrey',
        lineColor='white',
        closeShape=True
    )

    def create_progress_bar(p_value):
        x1 = left_edge
        x2 = left_edge + (p_value * bar_width)
        fillColor = 'blue'
        vertices = [(x1, bar_y - bar_height / 2),
                    (x2, bar_y - bar_height / 2),
                    (x2, bar_y + bar_height / 2),
                    (x1, bar_y + bar_height / 2)]
        return visual.ShapeStim(
            win,
            vertices=vertices,
            fillColor=fillColor,
            lineColor=None,
            closeShape=True
        )

    progress_bar = create_progress_bar(progress_value)

    fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))

    for trial_index, trial in enumerate(unimodal_trials):
        event.clearEvents()
        if "escape" in event.getKeys():
            win.close()
            core.quit()
        if "s" in event.getKeys(keyList=["s"]):
            return "skip"

        trial_type = trial[0]
        trial_clock = core.Clock()

        # --- Fixation before stimulus ---
        fixation.draw()
        progress_bg.draw()
        progress_bar.draw()
        win.flip()
        core.wait(0.5)

        if trial_type == "visual":
            shape_file, colour_file = trial[1], trial[2]
            shape_img = visual.ImageStim(win, image=os.path.join(image_dir, shape_file), size=(0.3, 0.4), pos=(-0.3, 0))
            colour_img = visual.ImageStim(win, image=os.path.join(colour_dir, colour_file), size=(0.3, 0.4), pos=(0.3, 0))
            shape_img.draw()
            colour_img.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(1.5)
            response = "NA"
            reaction_time = "NA"
        elif trial_type == "auditory":
            sound_file, paired_file = trial[1], trial[2]
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            main_sounds[sound_file].play()
            core.wait(1.0)
            core.wait(0.5)
            paired_sound = sound.Sound(os.path.join(paired_sound_dir, paired_file))
            paired_sound.play()
            core.wait(1.0)
            response = "NA"
            reaction_time = "NA"

        progress_value += 1.0 / total_trials
        progress_bar = create_progress_bar(progress_value)

        participant_data["block2_unimodal_log"].append({
            "trial_index": trial_index,
            "trial_type": trial_type,
            "stimulus": trial[1],
            "paired": trial[2],
            "response": response,
            "reaction_time": reaction_time,
        })

        event.clearEvents()

        if (trial_index + 1) % 33 == 0 and (trial_index + 1) < total_trials:
            break_msg = visual.TextStim(
                win,
                text=(f"You may take a short break.\n\n"
                      "Press SPACEBAR when you are ready to continue."),
                color="lightgrey", height=0.06, pos=(0, 0)
            )
            break_msg.draw()
            win.flip()
            keys = event.waitKeys(keyList=["space", "s"])
            if "s" in keys:
                return "skip"
            progress_bar = create_progress_bar(progress_value)

    end_msg = visual.TextStim(
        win,
        text="You have completed Block 2.\n\nPress SPACEBAR to continue.",
        color="lightgrey", height=0.06, pos=(0, 0)
    )
    end_msg.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "s"])
    if "s" in keys:
        return "skip"

    print("Block 2 completed successfully.")
    return "done"

# Block 3 - Testing block

def block3_testing():
    global participant_data
    participant_data["block3_test_log"] = []

    instruction_result = show_instructions(
        "Block 3 Task Instructions: \n\n"
        "xxx"
        "You will NOT receive feedback after each response.\n\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"

    try:
        crossmodal_trials = test_pairs * 33 
        random.shuffle(crossmodal_trials)

        total_trials = len(crossmodal_trials)
        progress_value = 0.0
        bar_width = 0.5
        bar_height = 0.07
        bar_y = -0.7
        left_edge = -bar_width / 2.0

        def create_progress_bar(p_value):
            x1 = left_edge
            x2 = left_edge + (p_value * bar_width)
            fillColor = 'blue'
            vertices = [(x1, bar_y - bar_height / 2),
                        (x2, bar_y - bar_height / 2),
                        (x2, bar_y + bar_height / 2),
                        (x1, bar_y + bar_height / 2)]
            return visual.ShapeStim(
                win,
                vertices=vertices,
                fillColor=fillColor,
                lineColor=None,
                closeShape=True
            )

        progress_bg = visual.ShapeStim(
            win,
            vertices=[(left_edge, bar_y - bar_height / 2),
                      (left_edge + bar_width, bar_y - bar_height / 2),
                      (left_edge + bar_width, bar_y + bar_height / 2),
                      (left_edge, bar_y + bar_height / 2)],
            fillColor='darkgrey',
            lineColor='white',
            closeShape=True
        )
        progress_bar = create_progress_bar(progress_value)

        fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
        prompt_sound2 = visual.TextStim(win, text="Press 1 if FIRST sound matches; 2 if SECOND sound matches.",
                                        color="white", height=0.05, pos=(0, 0))
        img_stim = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0, 0))

        for trial_index, (img_file, audio_file) in enumerate(crossmodal_trials):  # Renamed here
            if "escape" in event.getKeys():
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                return "skip"

            trial_clock = core.Clock()
            # Only shape+2sounds condition
            image_path = os.path.join(test_image_dir, img_file)
            available_tones = [snd for snd in [pair[1] for pair in test_pairs] if snd != audio_file]
            incorrect_tone = random.choice(available_tones)
            tones = [audio_file, incorrect_tone]
            random.shuffle(tones)

            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(0.5)

            for i in range(2):
                img_stim.image = image_path
                img_stim.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                tone = test_sounds[tones[i]]
                tone.play()
                core.wait(1.0)
                if i == 0:
                    fixation.draw()
                    progress_bg.draw()
                    progress_bar.draw()
                    win.flip()
                    core.wait(0.5)
                else:
                    core.wait(0.5)

            prompt_sound2.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            trial_clock.reset()

            response = None
            while trial_clock.getTime() < 5:
                keys = event.getKeys(keyList=["1", "2", "escape", "s"])
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
            correct_sound = dict(test_pairs).get(img_file)
            correct_answer = "1" if tones[0] == correct_sound else "2"

            participant_data["reaction time"].append(reaction_time)
            trial_data = {
                "trial_index": trial_index,
                "trial_type": "shape+2sounds",
                "stimulus": img_file,
                "audio": audio_file,
                "tones_order": tones,
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time,
                "pairings": list(test_pairs),
                "order": tones,
            }
            participant_data["block4_log"].append(trial_data)

            progress_value += 1.0 / total_trials
            progress_bar = create_progress_bar(progress_value)

            if (trial_index + 1) % 33 == 0 and (trial_index + 1) < total_trials:
                break_msg = visual.TextStim(
                    win,
                    text="You may take a short break.\n\nPress SPACEBAR to continue.",
                    color="lightgrey", height=0.06, pos=(0, 0))
                break_msg.draw()
                win.flip()
                keys = event.waitKeys(keyList=["space", "s"])
                if "s" in keys:
                    return "skip"
                progress_bar = create_progress_bar(progress_value)

        end_msg = visual.TextStim(
            win,
            text="You have completed the experiment.\n\nPress SPACEBAR to continue.",
            color="lightgrey", height=0.06, pos=(0, 0)
        )
        end_msg.draw()
        win.flip()
        keys = event.waitKeys(keyList=["space", "s"])
        if "s" in keys:
            return "skip"

        print("Block 3 completed successfully.")
        return "done"

    except Exception as e:
        print("Error during Block 3:")
        traceback.print_exc()
        core.quit()


# Define the main menu function before it is called
def main_menu():
    """Display the main menu and return the user's choice."""
    instructions_text = (
        "Press 2 for Active Test\n\n"
    )
    # Allow only key "2" here (no space)
    return show_instructions(instructions_text, ["2"])

# Define the end screen function before it is called
def show_end_screen():
    """Display the end screen."""
    end_message = visual.TextStim(
        win,
        text="End of the experiment. Thank you for participating! Press SPACEBAR to exit.",
        color="lightgrey",
        height=0.06,
        pos=(0, 0)
    )
    end_message.draw()
    win.flip()
    event.waitKeys(keyList=["space"])  # Wait for spacebar to exit


# === Main experiment flow ===
participant_id = get_participant_id()  # new: get participant id at start
participant_data["participant_id"] = participant_id

try:
    win = visual.Window(fullscr=True, color="gray", units="norm", allowGUI=True)
except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()

# --- Enforce workflow order ---

# Block 1: Crossmodal (was block2_active)
result = block1_crossmodal()
if result == "skip":
    # Skip to block 4
    block4_testing()
    participant_data["block_completed"] = True
    result = "done"
    save_block4_to_excel()
    if result == "done":
        show_end_screen()
    save_block2_to_excel()
    save_block4_to_excel()
    win.close()
    core.quit()
participant_data["block_completed"] = True
save_block1_crossmodal_to_excel()

# Block 2: Unimodal
result = block2_unimodal()
if result == "skip":
    # Skip to block 4
    block4_testing()
    participant_data["block_completed"] = True
    result = "done"
    save_block4_to_excel()
    if result == "done":
        show_end_screen()
    save_block2_unimodal_to_excel()
    save_block4_to_excel()
    win.close()
    core.quit()
participant_data["block_completed"] = True
save_block2_unimodal_to_excel()

# Block 3: Testing block
result = block3_testing()
if result == "skip":
    show_end_screen()
    save_block2_unimodal_to_excel()
    save_block3_test_to_excel()
    win.close()
    core.quit()
participant_data["block_completed"] = True
result = "done"
save_block3_test_to_excel()

# --- End workflow ---

# Ensure the experiment does not terminate prematurely
if result == "done":
    show_end_screen()

# Save data after each block
save_block2_unimodal_to_excel()
save_block3_test_to_excel()


# Cleanup
win.close()
core.quit()
