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
prefs.hardware['audioLib'] = ['sounddevice', 'pygame']
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

# Generate ordered list of paired stimuli (each appearing 6 times)
stimuli_pairs = [(f"shape_{i:02d}.png", f"sound_{i:02d}.wav") for i in range(4, 10)]  # Limit to 6 pairs (4 to 9)

for shp, snd in stimuli_pairs:
    n_shape = int(shp.split('_')[1].split('.')[0])
    n_sound = int(snd.split('_')[1].split('.')[0])
    assert n_shape == n_sound, f"Mapping error: {shp} vs {snd}"

all_trials = stimuli_pairs * 10  # Each pair appears 10 times
random.shuffle(all_trials)  # Completely randomize order

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
        # Check if the folder contains any data files
        data_files = [f for f in os.listdir(participant_folder) if os.path.isfile(os.path.join(participant_folder, f))]
        if data_files:  # Only prompt if there are existing data files
            resume_or_overwrite = gui.Dlg(title="Existing Participant Data")
            resume_or_overwrite.addText(f"Data for Participant ID '{participant_id}' already exists.")
            resume_or_overwrite.addField("Choose an option:", choices=["Resume", "Overwrite"])
            choice = resume_or_overwrite.show()
            if not resume_or_overwrite.OK:
                core.quit()
            if choice[0] == "Overwrite":
                # Clear existing data
                for file in data_files:
                    os.remove(os.path.join(participant_folder, file))
            elif choice[0] == "Resume":
                global participant_data
                load_partial_results(participant_id)

    return participant_id

def load_partial_results(participant_id):
    """Load partial results if they exist for the given participant ID."""
    global participant_data
    participant_folder = os.path.join("./participant_data", participant_id)
    try:
        # Load free pairings
        free_pairings_file = os.path.join(participant_folder, f"{participant_id}_free_pairings_partial.csv")
        if os.path.exists(free_pairings_file):
            free_pairings_df = pd.read_csv(free_pairings_file)
            participant_data["free_pairings"] = free_pairings_df.to_dict("records")
            print(f"Loaded free pairings from {free_pairings_file}")

        # Load block 2 log
        block2_log_file = os.path.join(participant_folder, f"{participant_id}_block2_log_partial.csv")
        if os.path.exists(block2_log_file):
            block2_log_df = pd.read_csv(block2_log_file)
            participant_data["block 2 log"] = block2_log_df.to_dict("records")
            participant_data["block 2 correct"] = block2_log_df["Correct Answer"].eq(block2_log_df["Response"]).sum()
            participant_data["block 2 incorrect"] = len(block2_log_df) - participant_data["block 2 correct"]
            print(f"Loaded block 2 log from {block2_log_file}")

        print("Partial results loaded successfully.")
    except Exception as e:
        print(f"Error loading partial results: {e}")
        traceback.print_exc()

def resume_experiment():
    """Determine where to resume the experiment based on loaded data."""
    if participant_data.get("block 2 log"):
        print("Resuming from Block 2...")
        return "block2"
    elif participant_data.get("free_pairings"):
        print("Resuming from Block 1...")
        return "block1"
    else:
        print("Starting from the beginning...")
        return "start"

# === Main experiment flow ===
participant_id = get_participant_id()  # new: get participant id at start
participant_data["participant_id"] = participant_id

# Load partial results if they exist
load_partial_results(participant_id)

# Determine where to resume
resume_point = resume_experiment()

try:
    win = visual.Window(fullscr=True, color="gray", units="norm", allowGUI=True)
except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()

# Handle each resume point
if resume_point == "start":
    block_zero_pairing()
    participant_data["block_completed"] = True  # Mark block as completed
    choice = main_menu()
    if choice == "passive":
        result = block_one_passive()
        participant_data["block_completed"] = True  # Mark block as completed
    elif choice == "active":
        result = block_one_active()
        participant_data["block_completed"] = True  # Mark block as completed
    else:
        result = None
elif resume_point == "block1":
    choice = main_menu()
    if choice == "passive":
        result = block_one_passive()
        participant_data["block_completed"] = True  # Mark block as completed
    elif choice == "active":
        result = block_one_active()
        participant_data["block_completed"] = True  # Mark block as completed
    else:
        result = None
elif resume_point == "block2":
    show_instructions("Second Block: Matching Task.\n\nPress SPACEBAR to continue.", ["space"])
    block_two()
    participant_data["block_completed"] = True  # Mark block as completed
    result = "done"  # Ensure result is set to "done" for proper flow

# Ensure the experiment does not terminate prematurely
if result == "done":
    save_partial_results()
    save_results()
    show_end_screen()
    show_instructions("Thank you for participating!\n\nPress SPACEBAR to exit.", ["space"])

# Save data after each block
save_free_pairings_to_excel()
save_block1_to_excel()
save_block2_to_excel()

# Consolidate all data into a single file
consolidate_data()

# Cleanup
win.close()
core.quit()

def show_instructions(text, continue_keys=["1", "2", "space"]):
    instructions = visual.TextStim(win, text=text, color="lightgrey", height=0.06, pos=(0, 0))
    instructions.draw()
    win.flip()
    
    while True:
        keys = event.waitKeys(keyList=continue_keys + ["escape"])
        if "escape" in keys:
            win.close()
            core.quit()
        elif "1" in keys:
            return "passive"  # User selected Passive test
        elif "2" in keys:
            return "active"  # User selected Active test
        elif "space" in keys:
            return "continue"
        
def block_zero_pairing():
    global participant_data
    participant_data["free_pairings"] = []

    # Load shapes and tones (limit to shapes 4 to 9 and tones 4 to 9)
    shape_files = sorted([f for f in os.listdir(image_dir) if f.startswith("shape_") and f.endswith(".png")])[3:9]
    tone_files = sorted([f for f in os.listdir(audio_dir) if f.startswith("sound_") and f.endswith(".wav")])[3:9]

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
        tone_sounds[filename] = sound.Sound(os.path.join(audio_dir, filename))

    # Use a variable to keep track of the currently selected tone (if any)
    selected_tone = None
    mouse = event.Mouse(visible=True)

    show_instructions(
    "Welcome to the experiment!\n\n"
    "On the next screen, you’ll see a list of shapes and a list of sounds.\n"
    "Click a musical note to hear its sound,\n"
    "then click the shape you think goes best with that sound.\n\n"
    "Take your time.\n\n"
    "Press SPACEBAR to continue.",
    ["space"]
)


    while True:  # fixed indentation level
        # ───── draw shapes & tones ──────────────────────────────────────
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

        # ───── handle keyboard ─────────────────────────────────────────
        keys = event.getKeys()
        if "escape" in keys:
            win.close(); core.quit()
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
    
    # Save free pairing data to Excel
    import pandas as pd
    df = pd.DataFrame(participant_data["free_pairings"])
    excel_filename = f"{participant_data['participant_id']}_free_pairings.xlsx"
    df.to_excel(excel_filename, index=False)
    print(f"Block zero data saved to {excel_filename}")
    
    # Clear the screen so that the main menu appears on a separate screen
    win.clearBuffer()
    win.flip()
    
    save_partial_results()
    return 'done'

# First block: Passive viewing of shapes and sounds

def block_one_passive():
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
    show_instructions(instructions_text, ["space"])

    # ─── prepare trial list ─────────────────────────────────────────────
    if participant_data.get("free_pairings"):
        trials = [(p["shape_file"], p["tone_file"])
                  for p in participant_data["free_pairings"]]
    else:
        trials = list(stimuli_pairs)
    trials *= 40  # Double the number of repetitions (was 20)
    random.shuffle(trials)

    TRIALS_BEFORE_BREAK = 20
    total_trials = len(trials)
    fixation = visual.TextStim(win, text="+", color="lightgrey",
                               height=0.1, pos=(0, 0))

    # ─── single loop with periodic breaks ──────────────────────────────
    idx = 0
    while idx < len(trials):
        img_file, audio_file = trials[idx]
        idx += 1

        if "escape" in event.getKeys():
            win.close()
            core.quit()

        # fixation
        fixation.draw()
        win.flip()
        core.wait(0.5)

        # stimulus presentation
        img_path = os.path.join(image_dir, img_file)
        wav_path = os.path.join(audio_dir, audio_file)
        if (os.path.exists(img_path) and os.path.exists(wav_path)):
            stim_img = visual.ImageStim(win, image=img_path, size=(0.25, 0.35), pos=(0, 0))
            stim_sound = sound.Sound(wav_path, secs=1, stereo=True, hamming=True)
            stim_img.draw()
            win.flip()
            stim_sound.play()
            core.wait(1.0)
            stim_sound.stop()

        if idx % TRIALS_BEFORE_BREAK == 0 and idx < total_trials:
            break_msg = visual.TextStim(
                win,
                text=(f"You may take a short break.\n\n"
                      f"{idx} trials completed out of {total_trials}.\n\n"
                      "Press SPACEBAR when you are ready to continue."),
                color="lightgrey", height=0.06, pos=(0, 0)
            )
            break_msg.draw()
            win.flip()
            event.waitKeys(keyList=["space"])

    # Show a message at the end of the block
    end_msg = visual.TextStim(
        win,
        text="You have completed the Passive Learning Block.\n\nPress SPACEBAR to continue.",
        color="lightgrey", height=0.06, pos=(0, 0)
    )
    end_msg.draw()
    win.flip()
    event.waitKeys(keyList=["space"])

    return "done"

def block_one_active():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["block2_log"] = []
    event.clearEvents()

    print("Starting Block 1 Active...")

    instruction_result = show_instructions(
        "Instructions: \n\n"
        "You will either:\n"
        "1. see an image and hear two tones (image+sound trial) or\n"
        "2. hear one tone and then see two images (sound+image trial).\n\n"
        "For image+tone trials, press '1' if the first tone is correct, '2' if the second tone is correct\n"
        "For audio+image trials, press '1' if the first image matches the audio, '2' if the second image matches.\n\n"
        "You will receive feedback after each trial.\n\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instruction_result != "continue":
        print("Block 1 Active skipped.")
        return "skip"

    try:
        print("Entering trial loop for Block 1 Active...")
        # Limit active trials to pairs 4 to 9
        local_stimuli = list(stimuli_pairs)
        random.shuffle(local_stimuli)
        active_trials = local_stimuli * 40  # Double the number of repetitions (was 20)
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

        TRIALS_BEFORE_BREAK = 20  # Add breaks after every 20 trials
        total_trials = len(active_trials)

        for trial_index, (img_file, audio_file) in enumerate(active_trials):
            event.clearEvents()
            if "escape" in event.getKeys():
                save_partial_results()
                win.close()
                core.quit()

            trial_clock = core.Clock()
            trial_type = random.choice(["audio+image", "image+tone"])
            tones = None
            correct_answer = None
            response = None

            # Draw progress bar
            progress_bg.draw()
            progress_bar.draw()

            if trial_type == "audio+image":
                available_images = [pair[0] for pair in stimuli_pairs if pair[0] != img_file]
                distractor = random.choice(available_images)
                images = [img_file, distractor]
                random.shuffle(images)

                img_first = visual.ImageStim(win, image=os.path.join(image_dir, images[0]), size=(0.3, 0.4), pos=(0, 0))
                img_first.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                tone1 = sound.Sound(os.path.join(audio_dir, audio_file), secs=1.0)
                tone1.play()  # Removed the 1-second pause before this line
                core.wait(1.0)
                tone1.stop()

                img_second = visual.ImageStim(win, image=os.path.join(image_dir, images[1]), size=(0.3, 0.4), pos=(0, 0))
                img_second.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                tone2 = sound.Sound(os.path.join(audio_dir, audio_file), secs=1.0)
                tone2.play()
                core.wait(1.0)
                tone2.stop()

                prompt = visual.TextStim(win, text="Press 1 if FIRST image matches; 2 if SECOND image matches.",
                                         color="white", height=0.05, pos=(0, 0))
                prompt.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                trial_clock.reset()
                while trial_clock.getTime() < 5:
                    keys = event.getKeys(keyList=["1", "2", "escape"])
                    if "escape" in keys:
                        win.close(); core.quit()
                    elif keys:
                        response = keys[0]
                        break
                if response is None:
                    response = "NA"
                reaction_time = round(trial_clock.getTime(), 3)
                correct_answer = "1" if images[0] == img_file else "2"

            elif trial_type == "image+tone":
                image_path = os.path.join(image_dir, img_file)
                img_stim = visual.ImageStim(win, image=image_path, size=(0.3, 0.4), pos=(0, 0))
                img_stim.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                core.wait(1.0)

                available_tones = [f"sound_{i:02d}.wav" for i in range(4, 10) if f"sound_{i:02d}.wav" != audio_file]
                incorrect_tone = random.choice(available_tones)
                tones = [audio_file, incorrect_tone]
                random.shuffle(tones)

                tone1 = sound.Sound(os.path.join(audio_dir, tones[0]), secs=1.0)
                tone1.play(); core.wait(1); tone1.stop(); core.wait(0.5)
                tone2 = sound.Sound(os.path.join(audio_dir, tones[1]), secs=1.0)
                tone2.play(); core.wait(1); tone2.stop()

                prompt = visual.TextStim(win, text="Press 1 if FIRST tone matches; 2 if SECOND tone matches.",
                                         color="white", height=0.05, pos=(0,0))
                prompt.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip(); trial_clock.reset()

                while trial_clock.getTime() < 5:
                    keys = event.getKeys(keyList=["1", "2", "escape"])
                    if "escape" in keys:
                        win.close(); core.quit()
                    elif keys:
                        response = keys[0]
                        break
                if response is None:
                    response = "NA"
                reaction_time = round(trial_clock.getTime(), 3)
                correct_answer = "1" if tones[0] == audio_file else "2"

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
                    "tones_order": tones if trial_type == "image+tone" else "N/A",
                    "correct_answer": correct_answer,
                    "response": response,
                    "reaction_time": reaction_time
                })
            except Exception as log_err:
                print(f"Logging error at trial {trial_index}:")
                print("tones =", tones)
                print("correct_answer =", correct_answer)
                print("response =", response)
                traceback.print_exc()
                core.quit()

            event.clearEvents()
            save_partial_results()

            # Show break message after every TRIALS_BEFORE_BREAK trials
            if (trial_index + 1) % TRIALS_BEFORE_BREAK == 0 and (trial_index + 1) < total_trials:
                break_msg = visual.TextStim(
                    win,
                    text=(f"You may take a short break.\n\n"
                          f"{trial_index + 1} trials completed out of {total_trials}.\n\n"
                          "Press SPACEBAR when you are ready to continue."),
                    color="lightgrey", height=0.06, pos=(0, 0)
                )
                break_msg.draw()
                win.flip()
                event.waitKeys(keyList=["space"])

        # Show a message at the end of the block
        end_msg = visual.TextStim(
            win,
            text="You have completed the Active Learning Block.\n\nPress SPACEBAR to continue.",
            color="lightgrey", height=0.06, pos=(0, 0)
        )
        end_msg.draw()
        win.flip()
        event.waitKeys(keyList=["space"])

        print("Block 1 Active completed successfully.")
        return "done"

    except Exception as e:
        print("Error during active test:")
        traceback.print_exc()
        core.quit()

def block_two_subtrial():
    # NEW: use sorted testset files to fix pairings (limit to shapes 4 to 9 and tones 4 to 9)
    shape_files = sorted([f for f in os.listdir(test_image_dir) if f.startswith("shape_") and f.endswith(".png")])[3:9]
    audio_files = sorted([f for f in os.listdir(test_audio_dir) if f.startswith("sound_") and f.endswith(".wav")])[3:9]
    test_pairs = list(zip(shape_files, audio_files))
    return test_pairs * 40  # 6 pairs * 40 repetitions = 240 trials

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
                  (left_edge+bar_width, y1_bg),
                  (left_edge+bar_width, y2_bg),
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
        vertices = [(x1, bar_y - bar_height/2),
                    (x2, bar_y - bar_height/2),
                    (x2, bar_y + bar_height/2),
                    (x1, bar_y + bar_height/2)]
        
        return visual.ShapeStim(
            win,
            vertices=vertices,
            fillColor=fillColor,
            lineColor=None,
            closeShape=True
        )
    
    progress_bar = create_progress_bar(progress_value)
    
    # NEW: For distractor selections, load available testset files when needed.
    test_shape_files = sorted([f for f in os.listdir(test_image_dir) if f.startswith("shape_") and f.endswith(".png")])
    
    for trial_index, (img_file, audio_file) in enumerate(trials):
        if "escape" in event.getKeys():
            save_partial_results()
            win.close()
            core.quit()
        
        trial_clock = core.Clock()
        trial_type = random.choice(["image+tone", "audio+image"])

        tones = None  # Prevent crash if trial_type is audio+image

        if trial_type == "audio+image":
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            event.clearEvents()
            core.wait(0.7)
            tones = "N/A"

            available_images = [img for img in test_shape_files if img != img_file]
            distractor_image = random.choice(available_images)
            images = [img_file, distractor_image]
            random.shuffle(images)

            img_first = visual.ImageStim(win, image=os.path.join(test_image_dir, images[0]), size=(0.3, 0.4), pos=(0, 0))
            img_first.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            tone1 = sound.Sound(os.path.join(test_audio_dir, audio_file), secs=1.0)
            tone1.play()
            core.wait(1.0)
            tone1.stop()

            img_second = visual.ImageStim(win, image=os.path.join(test_image_dir, images[1]), size=(0.3, 0.4), pos=(0, 0))
            img_second.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            tone2 = sound.Sound(os.path.join(test_audio_dir, audio_file), secs=1.0)
            tone2.play()
            core.wait(1.0)
            tone2.stop()

            response_prompt = visual.TextStim(
                win,
                text="Press 1 if the FIRST image matches.\nPress 2 if the SECOND image matches.",
                color="lightgrey", height=0.05, pos=(0, 0)
            )
            response_prompt.draw()
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
            if response is None:
                response = "NA"
            reaction_time = round(trial_clock.getTime(), 3)
            correct_answer = "1" if images[0] == img_file else "2"

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
                "tones_order": tones if trial_type == "image+tone" else "N/A",
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time
            }
            participant_data["block 2 log"].append(trial_data)
            save_partial_results()
        
        if trial_type == "image+tone":
            # Dynamically position the image in the center
            image_path = os.path.join(test_image_dir, img_file)
            img_stim = visual.ImageStim(win, image=image_path, size=(0.3, 0.4), pos=(0, 0))  # Centered position
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(1)  # Match Block 1 Active stimulus presentation time
            
            available_tones = [f"sound_{i:02d}.wav" for i in range(4, 10) if f"sound_{i:02d}.wav" != audio_file]
            incorrect_tone = random.choice(available_tones)
            tones = [audio_file, incorrect_tone]
            random.shuffle(tones)
            
            tone1 = sound.Sound(os.path.join(test_audio_dir, tones[0]), secs=1.0)
            tone1.play()
            core.wait(1)
            tone1.stop()
            core.wait(0.5)
            tone2 = sound.Sound(os.path.join(test_audio_dir, tones[1]), secs=1.0)
            tone2.play()
            core.wait(1)
            tone2.stop()
            core.wait(0.5)
            
            response_prompt = visual.TextStim(
                win,
                text="Press 1 if the FIRST tone matches.\nPress 2 if the SECOND tone matches.",
                color="lightgrey", height=0.05, pos=(0, 0)
            )
            response_prompt.draw()
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
            
            reaction_time = round(trial_clock.getTime(), 3)
            correct_answer = "1" if tones[0] == audio_file else "2"
            
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
                "tones_order": tones if trial_type == "image+tone" else "N/A",
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time
            }
            participant_data["block 2 log"].append(trial_data)
            save_partial_results()

def block_two_break():
    """Provide a break between subblocks in Block 2."""
    break_message = visual.TextStim(
        win,
        text="Take a short break.\n\nThe next part will begin in 30 seconds.",
        color="lightgrey",
        height=0.06,
        pos=(0, 0)
    )
    break_message.draw()
    win.flip()
    core.wait(30)  # 30 seconds break

    continue_message = visual.TextStim(
        win,
        text="Break over. Press SPACEBAR to continue.",
        color="lightgrey",
        height=0.06,
        pos=(0, 0)
    )
    continue_message.draw()
    win.flip()
    event.waitKeys(keyList=["space"])

def save_results():
    """Save final results after the experiment is completed."""
    p_id = participant_data["participant_id"]
    participant_folder = os.path.join("./participant_data", p_id)
    avg_rt = np.mean(participant_data["reaction time"]) if participant_data["reaction time"] else 0

    # Save summary data
    with open(os.path.join(participant_folder, f"{p_id}_summary.csv"), "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Block", "Correct", "Incorrect", "Average Reaction Time"])
        writer.writerow([
            "Block 2",
            participant_data["block 2 correct"],
            participant_data["block 2 incorrect"],
            avg_rt
        ])
        writer.writerow([])  # Blank line for separation
        writer.writerow(["Image Click Data"])
        writer.writerow(["Image", "Clicks"])
        for img, data in participant_data["click data"].items():
            writer.writerow([img, data["clicks"]])

    # Save free pairings
    with open(os.path.join(participant_folder, f"{p_id}_free_pairings.csv"), "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Tone File", "Shape File", "Tone Position", "Shape Position"])
        for pairing in participant_data["free_pairings"]:
            writer.writerow([
                pairing["tone_file"],
                pairing["shape_file"],
                pairing["tone_pos"],
                pairing["shape_pos"]
            ])

    # Save detailed block 2 log
    log_filename = os.path.join(participant_folder, f"{p_id}_block2_log.csv")
    with open(log_filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Subblock", "Trial Index", "Trial Type", "Stimulus", "Audio", "Tone Order", "Correct Answer", "Response", "Reaction Time"])
        for trial in participant_data["block 2 log"]:
            tone_order_str = ", ".join(trial["tones_order"]) if isinstance(trial["tones_order"], list) else trial["tones_order"]
            writer.writerow([
                trial["subblock"],
                trial["trial_index"],
                trial["trial_type"],
                trial["stimulus"],
                trial["audio"],
                tone_order_str,
                trial["correct_answer"],
                trial["response"],
                trial["reaction_time"]
            ])

def save_partial_results():
    """Save results only if the participant does not complete the block."""
    if not participant_data.get("block_completed", False):  # Check if block is incomplete
        p_id = participant_data["participant_id"]
        participant_folder = os.path.join("./participant_data", p_id)
        
        # Save free pairings data
        if "free_pairings" in participant_data:
            with open(os.path.join(participant_folder, f"{p_id}_free_pairings_partial.csv"), "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Tone File", "Shape File", "Tone Position", "Shape Position"])
                for pairing in participant_data["free_pairings"]:
                    writer.writerow([
                        pairing["tone_file"],
                        pairing["shape_file"],
                        pairing["tone_pos"],
                        pairing["shape_pos"]
                    ])
        
        # Save block 2 log
        if "block 2 log" in participant_data:
            log_filename = os.path.join(participant_folder, f"{p_id}_block2_log_partial.csv")
            with open(log_filename, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Subblock", "Trial Index", "Trial Type", "Stimulus", "Audio", "Tone Order", "Correct Answer", "Response", "Reaction Time"])
                for trial in participant_data["block 2 log"]:
                    if isinstance(trial["tones_order"], list):
                        tone_order_str = ", ".join(trial["tones_order"])
                    else:
                        tone_order_str = trial["tones_order"]
                    writer.writerow([
                        trial["subblock"],
                        trial["trial_index"],
                        trial["trial_type"],
                        trial["stimulus"],
                        trial["audio"],
                        tone_order_str,
                        trial["correct_answer"],
                        trial["response"],
                        trial["reaction_time"]
                    ])

def save_free_pairings_to_excel():
    """Save free pairings to an Excel file."""
    p_id = participant_data["participant_id"]
    excel_filename = f"{p_id}_free_pairings.xlsx"
    df = pd.DataFrame(participant_data["free_pairings"])
    df.to_excel(excel_filename, index=False)
    print(f"Free pairings saved to {excel_filename}")

def save_block1_to_excel():
    """Save Block 1 data (either active or passive) to an Excel file."""
    p_id = participant_data["participant_id"]
    block1_filename = f"{p_id}_block1.xlsx"
    if participant_data["task order"] == "active":
        df = pd.DataFrame(participant_data["block2_log"])
    else:
        df = pd.DataFrame({"Reaction Time": participant_data["reaction time"]})
    df.to_excel(block1_filename, index=False)
    print(f"Block 1 data saved to {block1_filename}")

def save_block2_to_excel():
    """Save Block 2 data to an Excel file."""
    p_id = participant_data["participant_id"]
    block2_filename = f"{p_id}_block2.xlsx"
    df = pd.DataFrame(participant_data["block 2 log"])
    df.to_excel(block2_filename, index=False)
    print(f"Block 2 data saved to {block2_filename}")

def consolidate_data():
    """Consolidate all data into a single Excel file."""
    p_id = participant_data["participant_id"]
    participant_folder = os.path.join("./participant_data", p_id)
    consolidated_filename = os.path.join(participant_folder, f"{p_id}_FULL_DATA.xlsx")
    with pd.ExcelWriter(consolidated_filename) as writer:
        # Save free pairings
        free_pairings_df = pd.DataFrame(participant_data["free_pairings"])
        free_pairings_df.to_excel(writer, sheet_name="Free Pairings", index=False)
        
        # Save Block 1 data
        if participant_data["task order"] == "active":
            block1_df = pd.DataFrame(participant_data["block2_log"])
        else:
            block1_df = pd.DataFrame({"Reaction Time": participant_data["reaction time"]})
        block1_df.to_excel(writer, sheet_name="Block 1", index=False)
        
        # Save Block 2 data
        block2_df = pd.DataFrame(participant_data["block 2 log"])
        block2_df.to_excel(writer, sheet_name="Block 2", index=False)
    
    print(f"Consolidated data saved to {consolidated_filename}")

################### MAIN EXPERIMENTAL FLOW ###################

block_zero_pairing()
save_partial_results()

def main_menu():
    instructions_text = (
        "Press 1 for Passive Test\n"
        "Press 2 for Active Test\n\n"
    )
    # Allow only keys "1" and "2" here (no space)
    return show_instructions(instructions_text, ["1", "2"])

choice = main_menu()

if choice == "passive":
    result = block_one_passive()
    save_partial_results()
elif choice == "active":
    result = block_one_active()
    save_partial_results()
else:
    result = None

def show_end_screen():
    end_message = visual.TextStim(
        win,
        text="End of the experiment.",
        color="lightgrey",
        height=0.06,
        pos=(0, 0)
    )
    end_message.draw()
    win.flip()
    event.waitKeys(keyList=["space"])  # Wait for spacebar to exit

if result == "done":
    show_instructions("Second Block: Matching Task.\n\nPress SPACEBAR to continue.", ["space"])
    block_two()
    save_partial_results()
    save_results()
    show_end_screen()  # Show the thank-you screen
    show_instructions("Thank you for participating!\n\nPress SPACEBAR to exit.", ["space"])

# Save data after each block
save_free_pairings_to_excel()
save_block1_to_excel()
save_block2_to_excel()

# Consolidate all data into a single file
consolidate_data()

# Cleanup
win.close()
core.quit()