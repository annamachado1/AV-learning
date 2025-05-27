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
image_dir = "./generated_shapes"
audio_dir = "./generated_sounds"

# NEW: Set paths for the testsets for block 2
test_image_dir = "./generated_shapes_testset"
test_audio_dir = "./generated_sounds_testset"

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
shape_files_main = [f"shape_{i:02d}.png" for i in range(1, 7)]
sound_files_main = [f"sound_{i:02d}.wav" for i in range(1, 7)]
stimuli_pairs = list(zip(shape_files_main, sound_files_main))

# Test set pairings
test_shape_files = [f"shape_{i:02d}.png" for i in range(1, 7)]
test_sound_files = [f"sound_{i:02d}.wav" for i in range(1, 7)]
test_pairs = list(zip(test_shape_files, test_sound_files))


for shp, snd in stimuli_pairs:
    n_shape = int(shp.split('_')[1].split('.')[0])
    n_sound = int(snd.split('_')[1].split('.')[0])
    assert n_shape == n_sound, f"Mapping error: {shp} vs {snd}"

# Remove undefined all_trials shuffle
# random.shuffle(all_trials)  # <-- REMOVE THIS LINE

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
    participant_folder = os.path.join("./participant_data", participant_id)
    if not os.path.exists(participant_folder):
        os.makedirs(participant_folder)
    else:
        # Always overwrite existing data
        data_files = [f for f in os.listdir(participant_folder) if os.path.isfile(os.path.join(participant_folder, f))]
        for file in data_files:
            os.remove(os.path.join(participant_folder, file))

    return participant_id
    

def save_block2_to_excel():
    # Save block 2 data to Excel in the participant folder as block2_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("block2_log", []))
    excel_filename = os.path.join(participant_folder, "block2_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Block 2 data saved to {excel_filename}")

def save_block4_to_excel():
    # Save block 4 data to Excel in the participant folder as block4_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("block4_log", []))
    excel_filename = os.path.join(participant_folder, "block4_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Block 4 data saved to {excel_filename}")

# Save_free_pairings_to_excel function
def save_free_pairings_to_excel():
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("free_pairings", []))
    excel_filename = os.path.join(participant_folder, "block1_free_pairings.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Free pairings saved to {excel_filename}")

# Save_free_pairings_test_to_excel function
def save_free_pairings_test_to_excel():
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("free_pairings_test", []))
    excel_filename = os.path.join(participant_folder, "block3_free_pairings.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Test free pairings saved to {excel_filename}")

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
def block1_free_pairings_train():
    global participant_data
    participant_data["free_pairings"] = []

    # Use shape_01.png–shape_06.png and sound_01.wav–sound_06.wav, paired by index
    shape_files = [f"shape_{i:02d}.png" for i in range(1, 7)]
    tone_files = [f"sound_{i:02d}.wav" for i in range(1, 7)]

    # Randomize the order of shapes and tones for display only
    random.shuffle(shape_files)
    random.shuffle(tone_files)

    # Dynamically calculate positions to evenly space shapes and tones
    num_pairs = len(shape_files)
    shape_positions = np.linspace(-0.9, 0.9, num_pairs)  # Adjusted for 6 pairs
    tone_positions = np.linspace(-0.9, 0.9, num_pairs)

    shapes = []
    tones = []
    tone_sounds = {}

    for i, filename in enumerate(shape_files):
        stim = visual.ImageStim(win, image=os.path.join(image_dir, filename), pos=(shape_positions[i], 0.5), size=(0.15, 0.25))
        shapes.append({"stim": stim, "file": filename})

    for i, filename in enumerate(tone_files):
        stim = visual.ImageStim(win, image="musical_note.png", pos=(tone_positions[i], -0.5), size=(0.1, 0.1))
        tones.append({"stim": stim, "file": filename})
        tone_sounds[filename] = main_sounds[filename]  # Use preloaded sound

    # Use a variable to keep track of the currently selected tone (if any)
    selected_tone = None
    mouse = event.Mouse(visible=True)

    instr_result = show_instructions(
        "Welcome to the experiment!\n\n"
        "On the next screen, you’ll see a list of shapes and a list of sounds.\n"
        "Click a musical note to hear its sound,\n"
        "then click the shape you think goes best with that sound.\n\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instr_result == "s":
        return "skip"


    while True:  # fixed indentation level
        # ───── draw shapes & tones ────────────────────────────��─────────
        for shape in shapes:
            shape["stim"].draw()
        for tone in tones:
            tone["stim"].draw()

        # if all tones are already paired, show a “continue” prompt
        if all("paired_shape" in t for t in tones):
            ready_msg = visual.TextStim(
                win,
                text="All sounds paired – press SPACEBAR to continue",
                color="lightgrey", height=0.05, pos=(0, -0.85)
            )
            ready_msg.draw()

        win.flip()

        # ───── handle mouse clicks ─────────────────────────────────────
        buttons = mouse.getPressed()
        if buttons[0]:
            core.wait(0.05)  # debounce
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

        # ───── handle keyboard ───────────���─────────────────────────────
        keys = event.getKeys(keyList=["escape", "space", "s"])
        if "escape" in keys:
            win.close(); core.quit()
        elif "s" in keys:
            return "skip"
        elif "space" in keys and all("paired_shape" in t for t in tones):
            break


    # Save pairings based on tones that were paired
    for tone in tones:
        if "paired_shape" in tone:
            # Extract numeric indices from tone and shape filenames
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
    
    save_free_pairings_to_excel()
    
    # Clear the screen so that the main menu appears on a separate screen
    win.clearBuffer()
    win.flip()
    
    return 'done'

# First block: Passive viewing of shapes and sounds

def block2_passive():
    instructions_text = (
        "Passive Learning Block\n\n"
        "In this part of the experiment you will simply WATCH and LISTEN.\n\n"
        "• On each trial you will see one shape and hear one sound presented together.\n"
        "• These shape–sound pairs have been PRE-ASSIGNED and may be different from the pairs you chose earlier.\n"
        "• Your task is to pay close attention and try to REMEMBER which sound goes with which shape, "
        "but do NOT press any keys.\n"
        "• Each shape will appear several times, giving you multiple chances to learn.\n\n"
        "There will be a short breaks throughout.\n\n"
        "Press SPACEBAR when you are ready to begin."
    )
    instr_result = show_instructions(instructions_text, ["space"])
    if instr_result == "s":
        return "skip"

    # ─── prepare trial list ──────────��──────────────────────────────────
    if participant_data.get("stimuli_pairs"):
        trials = [(p["shape_file"], p["tone_file"])
                  for p in participant_data["stimuli_pairs"]]
    else:
        trials = list(stimuli_pairs)
    trials *= 33  # 6 pairs × 33 = 198 trials
    random.shuffle(trials)

    TRIALS_BEFORE_BREAK = 33  # Optional: break every 33 trials
    total_trials = len(trials)
    fixation = visual.TextStim(win, text="+", color="lightgrey",
                               height=0.1, pos=(0, 0))

    # --- Progress bar setup (copied from block_one_active) ---
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
    # ---------------------------------------------------------

    # Create reusable ImageStim and TextStim objects
    stim_img = visual.ImageStim(win, image=None, size=(0.25, 0.35), pos=(0, 0))
    fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
    break_msg = visual.TextStim(
        win,
        text=(f"You may take a short break.\n\n"
              "Press SPACEBAR when you are ready to continue."),
        color="lightgrey", height=0.06, pos=(0, -0.85)
    )
    end_msg = visual.TextStim(
        win,
        text="You have completed the Passive Learning Block.\n\nPress SPACEBAR to continue.",
        color="lightgrey", height=0.06, pos=(0, 0)
    )

    # ─── single loop with periodic breaks ──────────────────────────────
    idx = 0
    while idx < len(trials):
        img_file, audio_file = trials[idx]
        idx += 1

        if "escape" in event.getKeys():
            win.close()
            core.quit()
        if "s" in event.getKeys(keyList=["s"]):
            return "skip"

        # fixation
        fixation.draw()
        progress_bg.draw()
        progress_bar.draw()
        win.flip()
        core.wait(0.5)

        # stimulus presentation
        img_path = os.path.join(image_dir, img_file)
        wav_path = os.path.join(audio_dir, audio_file)
        if (os.path.exists(img_path) and os.path.exists(wav_path)):
            stim_img.image = img_path
            stim_img.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            stim_sound = main_sounds[audio_file]  # Use preloaded sound
            stim_sound.play()
            core.wait(1.0)

        # --- Update progress bar ---
        progress_value += 1.0 / total_trials
        progress_bar = create_progress_bar(progress_value)
        # --------------------------

        if idx % TRIALS_BEFORE_BREAK == 0 and idx < total_trials:
            break_msg.draw()

            win.flip()
            keys = event.waitKeys(keyList=["space", "s"])
            if "s" in keys:
                return "skip"
            # After the break, update the progress bar again
            progress_bar = create_progress_bar(progress_value)

    end_msg.draw()
    progress_bg.draw()
    progress_bar.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "s"])
    if "s" in keys:
        return "skip"

    participant_data["block2_passive_completed"] = True
    return "done"

def block2_active():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["block2_log"] = []
    event.clearEvents()

    print("Starting Block 2 Active...")

    instruction_result = show_instructions(
        "Matching Task Instructions: \n\n"
        "You will either:\n"
        "1. see one shape and hear two different sounds (shape+2sounds trial) or\n"
        "2. hear one sound and see two different shapes (sound+2shapes trial).\n\n"
        "For shape+2sounds trials, press '1' if the first sound matches the shape, '2' if the second sound matches. \n"
        "For sound+2shapes trials, press '1' if the first shape matches the sound, '2' if the second shape matches.\n\n"
        "You will receive feedback after each trial.\n\n"
        "These shape–sound pairs have been PRE-ASSIGNED and may be different from the pairs you chose earlier.\n"
        "Please wait until prompted to give your response.\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"
    if instruction_result != "space":
        print("Block 2 Active skipped.")
        return "skip"

    try:
        print("Entering trial loop for Block 2 Active...")
        # Use every other pair for active trials
        local_stimuli = list(stimuli_pairs)
        random.shuffle(local_stimuli)
        active_trials = local_stimuli * 33  # 6 pairs × 33 = 198 trials
        random.shuffle(active_trials)

        # Load feedback images
        correct_feedback = visual.ImageStim(win, image="green_tick.png", size=(0.2, 0.2), pos=(0, 0))
        incorrect_feedback = visual.ImageStim(win, image="red_cross.png", size=(0.2, 0.2), pos=(0, 0))

        # Progress bar setup
        total_trials = len(active_trials)
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

        TRIALS_BEFORE_BREAK = 33  # Optional: break every 33 trials
        total_trials = len(active_trials)

        # Create reusable TextStim and ImageStim objects
        fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
        prompt_shape2 = visual.TextStim(win, text="Press 1 if FIRST shape matches; 2 if SECOND shape matches.",
                                        color="white", height=0.05, pos=(0, 0))
        prompt_sound2 = visual.TextStim(win, text="Press 1 if FIRST sound matches; 2 if SECOND sound matches.",
                                        color="white", height=0.05, pos=(0, 0))
        img_stim = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0, 0))

        for trial_index, (img_file, audio_file) in enumerate(active_trials):
            event.clearEvents()
            if "escape" in event.getKeys():
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                return "skip"

            trial_clock = core.Clock()
            trial_type = random.choice(["sound+2shapes", "shape+2sounds"])
            tones = None
            correct_answer = None
            response = None

            # Draw progress bar
            progress_bg.draw()
            progress_bar.draw()

            # Get true pairings from stimuli_pairs
            correct_pair = (img_file, audio_file)
            correct_sound = dict(stimuli_pairs).get(img_file)
            correct_shape = {v: k for k, v in stimuli_pairs}.get(audio_file)

            if trial_type == "sound+2shapes":
                available_images = [pair[0] for pair in stimuli_pairs if pair[0] != img_file]
                distractor = random.choice(available_images)
                images = [img_file, distractor]
                random.shuffle(images)

                # --- Fixation before first stimulus ---
                fixation.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                core.wait(0.5)
                # -------------------------------------

                img_stim.image = os.path.join(image_dir, images[0])
                img_stim.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                tone1 = main_sounds[audio_file]  # Use preloaded sound
                tone1.play()
                core.wait(1.0)

                # Insert 0.5s fixation cross between presentations
                fixation.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                core.wait(0.5)

                img_stim.image = os.path.join(image_dir, images[1])
                img_stim.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                tone2 = main_sounds[audio_file]  # Use preloaded sound
                tone2.play()
                core.wait(1.0)

                prompt_shape2.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                trial_clock.reset()
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
                # Use correct_shape logic
                if images[0] == correct_shape:
                    correct_answer = "1"
                else:
                    correct_answer = "2"


            elif trial_type == "shape+2sounds":
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
                        # Insert 0.5s fixation cross between presentations
                        fixation.draw()
                        progress_bg.draw()
                        progress_bar.draw()
                        win.flip()
                        core.wait(0.5)
                    else:
                        core.wait(0.5)  # 1.0s tone + 0.5s silence = 1.5s per image-tone

                prompt_sound2.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip(); trial_clock.reset()

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
                # Use correct_sound logic
                if tones[0] == correct_sound:
                    correct_answer = "1"
                else:
                    correct_answer = "2"
                


            participant_data["reaction time"].append(reaction_time)
            if response == correct_answer:
                participant_data["block 2 correct"] += 1
                # Show correct feedback
                correct_feedback.draw()
            else:
                participant_data["block 2 incorrect"] += 1
                # Show incorrect feedback
                incorrect_feedback.draw()
            win.flip()
            core.wait(1.0)  # Display feedback for 1 second

            # Update progress bar
            progress_value += 1.0 / total_trials
            progress_bar = create_progress_bar(progress_value)

            # Safe logging block
            try:
                participant_data["block2_log"].append({
                    "trial_index": trial_index,
                    "trial_type": trial_type,
                    "stimulus": img_file,
                    "audio": audio_file,
                    "tones_order": tones if trial_type == "shape+2sounds" else "N/A",
                    "correct_answer": correct_answer,
                    "response": response,
                    "reaction_time": reaction_time,
                    "pairings": list(stimuli_pairs),
                    "order": tones if trial_type == "shape+2sounds" else images if trial_type == "sound+2shapes" else "N/A",
                })
            except Exception as log_err:
                print(f"Logging error at trial {trial_index}:")
                print("tones =", tones)
                print("correct_answer =", correct_answer)
                print("response =", response)
                traceback.print_exc()
                core.quit()

            event.clearEvents()

            # Show break message after every TRIALS_BEFORE_BREAK trials
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
                # After the break, update the progress bar again
                progress_bar = create_progress_bar(progress_value)

        # Show a message at the end of the block
        end_msg = visual.TextStim(
            win,
            text="You have completed the Active Learning Block.\n\nPress SPACEBAR to continue.",
            color="lightgrey", height=0.06, pos=(0, 0)
        )
        end_msg.draw()
        win.flip()
        keys = event.waitKeys(keyList=["space", "s"])
        if "s" in keys:
            return "skip"

        print("Block 1 Active completed successfully.")
        return "done"

    except Exception as e:
        print("Error during active test:")
        traceback.print_exc()
        core.quit()

# Remove nested block4_testing definition
def block4_testing():
    global participant_data
    participant_data["block4_log"] = []

    instruction_result = show_instructions(
        "Final Matching Task Instructions: \n\n"
        "You will either:\n"
        "1. see one shape and hear two different sounds (shape+2sounds trial) or\n"
        "2. hear one sound and see two different shapes (sound+2shapes trial).\n\n"
        "For shape+2sounds trials, press '1' if the first sound matches the shape, '2' if the second sound matches. \n"
        "For sound+2shapes trials, press '1' if the first shape matches the sound, '2' if the second shape matches.\n\n"
        "Please wait until prompted to press the keys.\n"
        "You will NOT receive feedback after each trial.\n\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"

    try:
        active_trials = test_pairs * 33
        random.shuffle(active_trials)

        # Setup progress bar
        total_trials = len(active_trials)
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

        # Reusable stimuli
        fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
        prompt_shape2 = visual.TextStim(win, text="Press 1 if FIRST shape matches; 2 if SECOND shape matches.",
                                        color="white", height=0.05, pos=(0, 0))
        prompt_sound2 = visual.TextStim(win, text="Press 1 if FIRST sound matches; 2 if SECOND sound matches.",
                                        color="white", height=0.05, pos=(0, 0))
        img_stim = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0, 0))

        for trial_index, (img_file, audio_file) in enumerate(active_trials):
            if "escape" in event.getKeys():
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                return "skip"

            trial_clock = core.Clock()
            trial_type = random.choice(["sound+2shapes", "shape+2sounds"])
            tones = None
            correct_answer = None
            response = None

            correct_sound = dict(test_pairs).get(img_file)
            correct_shape = {v: k for k, v in test_pairs}.get(audio_file)

            # Shape+2sounds
            if trial_type == "shape+2sounds":
                image_path = os.path.join(test_image_dir, img_file)
                available_tones = [snd for snd in test_sound_files if snd != audio_file]
                incorrect_tone = random.choice(available_tones)
                tones = [audio_file, incorrect_tone]
                random.shuffle(tones)

                for i in range(2):
                    fixation.draw()
                    progress_bg.draw()
                    progress_bar.draw()
                    win.flip()
                    core.wait(0.5)

                    img_stim.image = image_path
                    img_stim.draw()
                    progress_bg.draw()
                    progress_bar.draw()
                    win.flip()
                    core.wait(0.5)

                    test_sounds[tones[i]].play()
                    core.wait(1.0)

                prompt_sound2.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                trial_clock.reset()

                #while trial_clock.getTime() < 5:
                    #keys = event.getKeys(keyList=["1", "2", "escape", "s"])
                    #if "escape" in keys:
                        #win.close(); core.quit()
                    #elif "s" in keys:
                        #return "skip"
                    #elif keys:
                        #response = keys[0]
                        #break
                    #core.wait(0.01)  # Wait for 0.01 seconds before checking response
                timer = core.Clock()
                while timer.getTime() < 5:
                    keys = event.getKeys(keyList=["1", "2", "escape", "s"])
                    if "escape" in keys:
                        win.close(); core.quit()
                    elif "s" in keys:
                        return "skip"
                    elif keys:
                        response = keys[0]
                        break
                    core.wait(0.01)
                    #win.flip()  # <--- safely redraw to keep the OS happy

                if response is None:
                    response = "NA"

                reaction_time = round(trial_clock.getTime(), 3)
                correct_answer = "1" if tones[0] == correct_sound else "2"

            # Sound+2shapes
            elif trial_type == "sound+2shapes":
                available_images = [shp for shp in test_shape_files if shp != img_file]
                distractor = random.choice(available_images)
                images = [img_file, distractor]
                random.shuffle(images)

                for i in range(2):
                    fixation.draw()
                    progress_bg.draw()
                    progress_bar.draw()
                    win.flip()
                    core.wait(0.5)

                    img_stim.image = os.path.join(test_image_dir, images[i])
                    img_stim.draw()
                    progress_bg.draw()
                    progress_bar.draw()
                    win.flip()
                    core.wait(0.5)

                    test_sounds[audio_file].play()
                    core.wait(1.0)

                prompt_shape2.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                trial_clock.reset()

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
                correct_answer = "1" if images[0] == correct_shape else "2"

            # Log results
            participant_data["reaction time"].append(reaction_time)
            trial_data = {
                "trial_index": trial_index,
                "trial_type": trial_type,
                "stimulus": img_file,
                "audio": audio_file,
                "tones_order": tones if trial_type == "shape+2sounds" else "N/A",
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time,
                "pairings": list(test_pairs),
                "order": tones if trial_type == "shape+2sounds" else images if trial_type == "sound+2shapes" else "N/A",
            }
            participant_data["block4_log"].append(trial_data)

            # Update progress bar
            progress_value += 1.0 / total_trials
            progress_bar = create_progress_bar(progress_value)

            # Break every N trials
            if (trial_index + 1) % 33 == 0 and (trial_index + 1) < total_trials:
                break_msg = visual.TextStim(win, text="You may take a short break.\n\nPress SPACEBAR to continue.",
                                            color="lightgrey", height=0.06, pos=(0, 0))
                break_msg.draw()
                win.flip()
                keys = event.waitKeys(keyList=["space", "s"])
                if "s" in keys:
                    return "skip"
                progress_bar = create_progress_bar(progress_value)

        # End of block
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

        print("Block 4 completed successfully.")
        return "done"

    except Exception as e:
        print("Error during Block 4:")
        traceback.print_exc()
        core.quit()


def block_two_subtrial():
    # Use shape_01.png–shape_06.png and sound_01.wav–sound_06.wav from test set, paired by index
    shape_files = [f"shape_{i:02d}.png" for i in range(1, 7)]
    audio_files = [f"sound_{i:02d}.wav" for i in range(1, 7)]
    test_pairs = list(zip(shape_files, audio_files))
    return test_pairs * 33  # 6 pairs × 33 = 198 trials

def block_two_subblock(subblock, trials):
    global participant_data

    # Dynamically calculate positions for test shapes
    num_pairs = 6  # Fixed to 6 pairs
    shape_positions = np.linspace(-0.9, 0.9, num_pairs)  # Adjusted for 6 pairs

    total_trials = len(trials)
    progress_value = 0.0

    bar_width = 0.5
    bar_height = 0.07
    bar_y = -0.7
    left_edge = -bar_width / 2.0

    y1_bg = bar_y - bar_height / 2
    y2_bg = bar_y + bar_height / 2

    progress_bg = visual.ShapeStim(
        win,
        vertices=[(left_edge, y1_bg),
                  (left_edge + bar_width, y1_bg),
                  (left_edge + bar_width, y2_bg),
                  (left_edge, y2_bg)],
        fillColor='darkgrey',
        lineColor='white',
        closeShape=True
    )

    def create_progress_bar(p_value):
        # p_value represents the fraction of bar_width to fill.
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

    # NEW: For distractor selections, load available testset files when needed.
    test_shape_files = [f"shape_{i:02d}.png" for i in range(1, 7)]

    # Create reusable ImageStim and TextStim objects
    img_stim = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0, 0))
    fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
    response_prompt_shape = visual.TextStim(
        win,
        text="Press 1 if the FIRST shape matches.\nPress 2 if the SECOND shape matches.",
        color="lightgrey", height=0.05, pos=(0, 0)
    )
    response_prompt_sound = visual.TextStim(
        win,
        text="Press 1 if the FIRST sound matches.\nPress 2 if the SECOND sound matches.",
        color="lightgrey", height=0.05, pos=(0, 0)
    )

    test_shape_files = [f"shape_{i:02d}.png" for i in range(1, 7)]
    test_audio_files = [f"sound_{i:02d}.wav" for i in range(1, 7)]
    test_pairs = list(zip(test_shape_files, test_audio_files))
    test_shape_to_sound = dict(test_pairs)
    test_sound_to_shape = {v: k for k, v in test_pairs}

    for trial_index, (img_file, audio_file) in enumerate(trials):
        if "escape" in event.getKeys():
            win.close()
            core.quit()

        trial_clock = core.Clock()
        trial_type = random.choice(["shape+2sounds", "sound+2shapes"])
        tones = None  # Prevent crash if trial_type is sound+2shapes

        # Get true pairings from test_pairs
        correct_sound = test_shape_to_sound.get(img_file)
        correct_shape = test_sound_to_shape.get(audio_file)

        if trial_type == "sound+2shapes":
            # --- Fixation before first stimulus ---
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(0.5)
            # -------------------------------------

            available_images = [img for img in test_shape_files if img != img_file]
            distractor_image = random.choice(available_images)
            images = [img_file, distractor_image]
            random.shuffle(images)

            img_stim.image = os.path.join(test_image_dir, images[0])
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            tone1 = test_sounds[audio_file]  # Use preloaded sound
            tone1.play()
            core.wait(1.0)

            # Insert 0.5s fixation cross between presentations
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(0.5)

            img_stim.image = os.path.join(test_image_dir, images[1])
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            tone2 = test_sounds[audio_file]  # Use preloaded sound
            tone2.play()
            core.wait(1.0)

            response_prompt_shape.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            trial_clock.reset()
            response = None
            while trial_clock.getTime() < 5.0:  # Updated response window to 5 seconds
                keys = event.getKeys(keyList=["1", "2", "escape"])
                if "escape" in keys:
                    win.close()
                    core.quit()
                elif keys:
                    response = keys[0]
                    break
                core.wait(0.01)

            if response is None:
                response = "NA"
            reaction_time = round(trial_clock.getTime(), 3)
            # Use correct_shape logic
            if images[0] == correct_shape:
                correct_answer = "1"
            else:
                correct_answer = "2"

            if response == correct_answer:
                participant_data["block 2 correct"] += 1
            else:
                participant_data["block 2 incorrect"] += 1

            progress_value += 1.0 / total_trials
            progress_bar = create_progress_bar(progress_value)

            trial_data = {
                "subblock": subblock,
                "trial_index": trial_index,
                "trial_type": trial_type,
                "stimulus": img_file,
                "audio": audio_file,
                "tones_order": tones if trial_type == "shape+2sounds" else "N/A",
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time,
                "pairings": list(zip(test_shape_files, [audio_file]*len(test_shape_files))),
                "order": tones if trial_type == "shape+2sounds" else images if trial_type == "sound+2shapes" else "N/A",
            }
            participant_data["block 2 log"].append(trial_data)

        elif trial_type == "shape+2sounds":
            # --- Fixation before first stimulus ---
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(0.5)
            # -------------------------------------

            image_path = os.path.join(test_image_dir, img_file)
            img_stim.image = image_path
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            available_tones = [f"sound_{i:02d}.wav" for i in range(1, 7) if f"sound_{i:02d}.wav" != audio_afile]
            incorrect_tone = random.choice(available_tones)
            tones = [audio_file, incorrect_tone]
            random.shuffle(tones)

            response = None
            while trial_clock.getTime() < 5.0:  # Updated response window to 5 seconds
                keys = event.getKeys(keyList=["1", "2", "escape"])
                if "escape" in keys:
                    win.close()
                    core.quit()
                elif keys:
                    response = keys[0]
                    break
                core.wait(0.01)

            reaction_time = round(trial_clock.getTime(), 3)
            # Use correct_sound logic
            if tones[0] == correct_sound:
                correct_answer = "1"
            else:
                correct_answer = "2"

            participant_data["reaction time"].append(reaction_time)
            if response == correct_answer:
                participant_data["block 2 correct"] += 1
            else:
                participant_data["block 2 incorrect"] += 1

            progress_value += 1.0 / total_trials
            progress_bar = create_progress_bar(progress_value)

            trial_data = {
                "subblock": subblock,
                "trial_index": trial_index,
                "trial_type": trial_type,
                "stimulus": img_file,
                "audio": audio_file,
                "tones_order": tones if trial_type == "shape+2sounds" else "N/A",
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time,
                "pairings": list(zip(test_shape_files, [audio_file]*len(test_shape_files))),
                "order": tones if trial_type == "shape+2sounds" else images if trial_type == "sound+2shapes" else "N/A",

            }
            participant_data["block 2 log"].append(trial_data)


# Define the main menu function before it is called
def main_menu():
    """Display the main menu and return the user's choice."""
    instructions_text = (
        "Press 1 for Passive Test\n"
        "Press 2 for Active Test\n\n"
    )
    # Allow only keys "1" and "2" here (no space)
    return show_instructions(instructions_text, ["1", "2"])

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


# Define second free pairings before it is called

def block3_free_pairings_test():
    """Second Free Pairing Block for Block 2 testset."""
    global participant_data
    participant_data["free_pairings_test"] = []
    # Use shape_01.png–shape_06.png and sound_01.wav–sound_06.wav from test set, paired by index
    shape_files = [f"shape_{i:02d}.png" for i in range(1, 7)]
    tone_files = [f"sound_{i:02d}.wav" for i in range(1, 7)]

    # Randomize the order of shapes and tones for display only
    random.shuffle(shape_files)
    random.shuffle(tone_files)

    num_pairs = len(shape_files)
    shape_positions = np.linspace(-0.9, 0.9, num_pairs)
    tone_positions = np.linspace(-0.9, 0.9, num_pairs)
    shapes = []
    tones = []
    tone_sounds = {}
    for i, filename in enumerate(shape_files):
        stim = visual.ImageStim(win, image=os.path.join(test_image_dir, filename), pos=(shape_positions[i], 0.5), size=(0.15, 0.25))
        shapes.append({"stim": stim, "file": filename})
    for i, filename in enumerate(tone_files):
        stim = visual.ImageStim(win, image="musical_note.png", pos=(tone_positions[i], -0.5), size=(0.1, 0.1))
        tones.append({"stim": stim, "file": filename})
        tone_sounds[filename] = test_sounds[filename]  # Use preloaded sound
    selected_tone = None
    mouse = event.Mouse(visible=True)
    
    # Instructions for second free pairing block
    instr_result = show_instructions(
        "On the next screen, you’ll see a list of shapes and a list of sounds.\n"
        "Click a musical note to hear its sound,\n"
        "then click the shape you think goes best with that sound.\n\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instr_result == "s":
        return "skip"
    
    while True:
        for shape in shapes:
            shape["stim"].draw()
        for tone in tones:
            tone["stim"].draw()
        if all("paired_shape" in t for t in tones):
            ready_msg = visual.TextStim(win, text="All sounds paired – press SPACEBAR to continue", color="lightgrey", height=0.05, pos=(0, -0.85))
            ready_msg.draw()
        win.flip()
        buttons = mouse.getPressed()
        if buttons[0]:
            core.wait(0.05)
            tone_clicked = next((t for t in tones if t["stim"].contains(mouse)), None)
            if tone_clicked:
                tone_sounds[tone_clicked["file"]].play()
                selected_tone = tone_clicked
            elif selected_tone:
                for shape in shapes:
                    if shape["stim"].contains(mouse):
                        new_pos = (shape["stim"].pos[0], shape["stim"].pos[1] - 0.3)
                        selected_tone["stim"].pos = new_pos
                        selected_tone["paired_shape"] = shape["file"]
                        selected_tone["new_pos"] = new_pos
                selected_tone = tone_clicked
            elif selected_tone:
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
    
    for tone in tones:
        if "paired_shape" in tone:
            sound_index = int(tone["file"].split('_')[1].split('.')[0])
            shape_index = int(next(s["file"] for s in shapes if s["file"] == tone["paired_shape"]).split('_')[1].split('.')[0])
            participant_data["free_pairings_test"].append({
                "tone_file": tone["file"],
                "shape_file": tone["paired_shape"],
                "sound_index": sound_index,
                "shape_index": shape_index,
                "tone_pos": tone["new_pos"],
                "shape_pos": next(s["stim"].pos for s in shapes if s["file"] == tone["paired_shape"])
            })
    print("Test set pairings recorded:", participant_data["free_pairings_test"])
    return "done"

# === Main experiment flow ===
participant_id = get_participant_id()  # new: get participant id at start
participant_data["participant_id"] = participant_id

try:
    win = visual.Window(fullscr=True, color="gray", units="norm", allowGUI=True)
except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()

# --- Enforce workflow order ---

# Block 1: Free pairings with train data
result = block1_free_pairings_train()
if result == "skip":
    # Skip to block 3
    block3_free_pairings_test()
    save_free_pairings_test_to_excel()
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
participant_data["block_completed"] = True  # Mark block as completed

# Block 2: Active or passive learning
choice = main_menu()
if choice == "1":
    result = block2_passive()
    if result == "skip":
        # Skip to block 3
        block3_free_pairings_test()
        save_free_pairings_test_to_excel()
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
    # After passive, always do active as well
    result = block2_active()
    if result == "skip":
        # Skip to block 3
        block3_free_pairings_test()
        save_free_pairings_test_to_excel()
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
elif choice == "2":
    result = block2_active()
    if result == "skip":
        # Skip to block 3
        block3_free_pairings_test()
        save_free_pairings_test_to_excel()
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
else:
    result = None
save_block2_to_excel()

# Block 3: Free pairings with test data
result = block3_free_pairings_test()
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
save_free_pairings_test_to_excel()  # <-- Save second free pairings here

# Block 4: Testing block
result = block4_testing()
if result == "skip":
    show_end_screen()
    save_block2_to_excel()
    save_block4_to_excel()
    win.close()
    core.quit()
participant_data["block_completed"] = True
result = "done"
save_block4_to_excel()

# --- End workflow ---

# Ensure the experiment does not terminate prematurely
if result == "done":
    show_end_screen()

# Save data after each block
save_block2_to_excel()
save_block4_to_excel()


# Cleanup
win.close()
core.quit()
