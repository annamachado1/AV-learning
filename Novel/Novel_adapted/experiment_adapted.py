import os
import random
random.seed(42)  # Added fixed seed for consistent random pairings
import pandas as pd
import csv
import time
from psychopy import visual, core, event, sound, prefs, gui
import numpy as np
import traceback

# === Collect participant ID and set up directories before anything else ===
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

def save_block1_crossmodal_to_excel():
    # Save block 1 data to Excel in the participant folder as block1_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("block1_crossmodal_log", []))
    excel_filename = os.path.join(participant_folder, "block1_crossmodal_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Block 1 data saved to {excel_filename}")

def save_block2_unimodal_to_excel():
    # Save block 2 data to Excel in the participant folder as block2_unimodal_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("block2_unimodal_log", []))
    excel_filename = os.path.join(participant_folder, "block2_unimodal_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Block 2 data saved to {excel_filename}")

def save_block3_test_to_excel():
    # Save block 3 data to Excel in the participant folder as block3_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
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

def run_end_survey():
    """Prompt participant for survey responses on the PsychoPy window and save to CSV and Excel."""
    survey_questions = [
        "Which features of the shapes did you focus on to help with learning?",
        "Which features of the sounds did you focus on to help with learning?",
        "Were certain shape–sound pairings easier to remember than others? Why?",
        "Did you use any specific strategies to remember the pairings?",
        "Did you find it easier to learn using sound, shape, or both together?",
        "Did you notice any patterns in the stimuli that helped you?",
        "How confident were you in your answers during the test block? Why?",
        "Did your strategy change across the blocks? If so, how and why?",
        "What did you find most challenging about the task?",
        "Did you rely more on intuition or logic when making your choices?",
        "Did you imagine any associations (e.g., stories, categories) to help remember the pairs?",
        "Any additional comments about how you approached the task?",
    ]
    responses = []
    instr = visual.TextStim(win, text="End Survey\n\nType your answer and press ENTER to continue.\n(Use BACKSPACE to edit)", color="lightgrey", height=0.06, wrapWidth=1.6, pos=(0, 0.7))
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
            for key in keys:
                if key == "return":
                    responses.append(answer)
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
            else:
                continue
            break
    # Save responses to CSV
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    survey_path = os.path.join(participant_folder, "end_survey.csv")
    with open(survey_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["question", "response"])
        for q, r in zip(survey_questions, responses):
            writer.writerow([q, r])
    print(f"Survey responses saved to {survey_path}")

    # Save responses to Excel
    try:
        import pandas as pd
        df = pd.DataFrame({"question": survey_questions, "response": responses})
        excel_path = os.path.join(participant_folder, "end_survey.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"Survey responses also saved to {excel_path}")
    except Exception as e:
        print(f"Could not save survey to Excel: {e}")

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

# --- Always collect participant ID and set up paths before anything else ---
participant_id = get_participant_id()
participant_data = {
    "participant_id": participant_id,  # <-- Ensure this is set
    "task order": "",
    "time on active task": 0,
    "click data": {},
    "block 1 correct": 0,
    "block 1 incorrect": 0,
    "block 2 correct": 0,
    "block 2 incorrect": 0,
    "reaction time": [],
    "block 2 log": [],
}
# Set image/audio directories (adjust as needed for your experiment)
image_dir = "./generated_shapes"
audio_dir = "./generated_sounds"

# === DEBUG: Skip to block 3 for debugging ===
DEBUG_SKIP_TO_BLOCK3 = False  # Set to True to skip to block 3
DEBUG_SKIP_TO_SURVEY = True   # Set to True to skip directly to end survey
DEBUG_SKIP_BLOCK3 = True      # Set to True to skip block 3 entirely

# --- Debug skip to end survey ---
if DEBUG_SKIP_TO_SURVEY:
    print("DEBUG: Skipping directly to end survey and end screen.")
    # Create the window before showing survey/end screen
    win = visual.Window(fullscr=True, color="gray", units="norm", allowGUI=True)
    run_end_survey()
    show_end_screen()
    win.close()
    core.quit()

# --- Debug skip all blocks and go to survey ---
if DEBUG_SKIP_TO_BLOCK3 and DEBUG_SKIP_BLOCK3:
    print("DEBUG: Skipping all blocks, proceeding to survey and end screen.")
    run_end_survey()
    try:
        from psychopy import visual
        win = visual.Window(fullscr=True, color="gray", units="norm", allowGUI=True)
        show_end_screen()
        win.close()
    except Exception:
        pass
    save_block1_crossmodal_to_excel()
    save_block2_unimodal_to_excel()
    save_block3_test_to_excel()
    core.quit()

# === Create PsychoPy window early so it's available for all functions ===
try:
    win = visual.Window(fullscr=True, color="gray", units="norm", allowGUI=True)
except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()

# Configure sound preferences
prefs.hardware['audioLib'] = ['pygame', 'sounddevice']
prefs.general['audioDevice'] = ['default']
# Use the same directories for test set as for main set
test_image_dir = image_dir
test_audio_dir = audio_dir

# Store participant data
participant_data.update({
    "block 1 correct": 0,      # <-- Add this line
    "block 1 incorrect": 0,    # <-- Add this line
    "block 2 correct": 0,
    "block 2 incorrect": 0,
    "reaction time": [],
    "block 2 log": [],
})

# === Presentation timing constants ===
STIMULUS_DURATION = 1.0  # seconds, all shapes and sounds
FIXATION_DURATION = 0.3  # seconds, all fixations

# Generate ordered list of paired stimuli (shape_01.png with sound_05.wav, etc.)
stimuli_pairs = [
    ("shape_01.png", "sound_05.wav"),
    ("shape_02.png", "sound_03.wav"),
    ("shape_03.png", "sound_06.wav"),
    ("shape_04.png", "sound_04.wav"),
    ("shape_05.png", "sound_01.wav"),
    ("shape_06.png", "sound_02.wav"),
]

# Test set pairings: use the same as stimuli_pairs
test_pairs = list(stimuli_pairs)

# Preload all sound objects
def preload_sounds(audio_dir):
    sound_dict = {}
    for fname in sorted([f for f in os.listdir(audio_dir) if f.startswith("sound_") and f.endswith(".wav")]):
        sound_dict[fname] = sound.Sound(os.path.join(audio_dir, fname))
    return sound_dict

main_sounds = preload_sounds(audio_dir)
test_sounds = preload_sounds(test_audio_dir)

# Preload all images for block 2 visual-only trials
def preload_images(image_dir, image_files):
    return {
        fname: visual.ImageStim(win, image=os.path.join(image_dir, fname), size=(0.3, 0.4))
        for fname in set(image_files)
    }

# Explicitly define visual shape pairings for block 2 (visual only)
visual_shape_pairs = [
    ("shape_01.png", "associated_shape_06.png"),
    ("shape_02.png", "associated_shape_02.png"),
    ("shape_03.png", "associated_shape_04.png"),
    ("shape_04.png", "associated_shape_01.png"),
    ("shape_05.png", "associated_shape_05.png"),
    ("shape_06.png", "associated_shape_03.png"),
]

# Explicitly define auditory sound pairings for block 2 (auditory only)
auditory_sound_pairs = [
    ("sound_01.wav", "associated_sound_03.wav"),
    ("sound_02.wav", "associated_sound_06.wav"),
    ("sound_03.wav", "associated_sound_01.wav"),
    ("sound_04.wav", "associated_sound_05.wav"),
    ("sound_05.wav", "associated_sound_02.wav"),
    ("sound_06.wav", "associated_sound_04.wav"),
]

# Preload associated sounds for block 2 auditory-only trials
def preload_sounds_explicit(audio_dir, sound_files):
    return {
        fname: sound.Sound(os.path.join(audio_dir, fname))
        for fname in set(sound_files)
    }

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
    

# Define block functions next

# Block 1 - Crossmodal

def block1_crossmodal():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["block1_crossmodal_log"] = []
    event.clearEvents()

    print("Starting Block 1 Crossmodal...")

    instruction_result = show_instructions(
        "Task Instructions: \n\n"
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
        crossmodal_trials = []
        # For each pair, create exactly half congruent-first and half congruent-second
        for img_file, audio_file in local_stimuli:
            available_tones = [snd for snd in [pair[1] for pair in stimuli_pairs] if snd != audio_file]
            for _ in range(15 // 2):
                # Congruent first
                incorrect_tone = random.choice(available_tones)
                crossmodal_trials.append((img_file, audio_file, [audio_file, incorrect_tone]))
                # Congruent second
                incorrect_tone = random.choice(available_tones)
                crossmodal_trials.append((img_file, audio_file, [incorrect_tone, audio_file]))
        # If odd, add one more randomly to reach 15 per pair
        if 15 % 2 != 0:
            for img_file, audio_file in local_stimuli:
                available_tones = [snd for snd in [pair[1] for pair in stimuli_pairs] if snd != audio_file]
                if random.random() < 0.5:
                    incorrect_tone = random.choice(available_tones)
                    crossmodal_trials.append((img_file, audio_file, [audio_file, incorrect_tone]))
                else:
                    incorrect_tone = random.choice(available_tones)
                    crossmodal_trials.append((img_file, audio_file, [incorrect_tone, audio_file]))
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

        TRIALS_BEFORE_BREAK = 35  # Break every 35 trials
        total_trials = len(crossmodal_trials)

        fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
        prompt_sound2 = visual.TextStim(win, text="Press 1 if FIRST sound matches; 2 if SECOND sound matches.",
                                        color="white", height=0.05, pos=(0, 0))
        img_stim = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0, 0))

        for trial_index, (img_file, audio_file, tones) in enumerate(crossmodal_trials):
            event.clearEvents()
            if "escape" in event.getKeys():
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                return "skip"

            trial_clock = core.Clock()
            image_path = os.path.join(image_dir, img_file)

            # --- Fixation before first stimulus ---
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # always 0.3s
            # -------------------------------------

            # --- PRESENTATION ORDER: shape (no sound), then sound 1, then sound 2 ---
            # 1. Show shape (no sound)
            img_stim.image = image_path
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(STIMULUS_DURATION)  # always 1s

            # 2. Fixation + play first sound
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            main_sounds[tones[0]].play()
            core.wait(STIMULUS_DURATION)  # always 1s

            # 3. Fixation + play second sound
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            main_sounds[tones[1]].play()
            core.wait(STIMULUS_DURATION)  # always 1s
            # -----------------------------------------------------------------------

            # Prompt for response
            prompt_sound2.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip(); trial_clock.reset()

            response = None
            while trial_clock.getTime() < 4:  # was 5
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
            core.wait(0.5)  # always 0.5s

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
            text="You have completed this block.\n\nPress SPACEBAR to continue.",
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
        "Task Instructions: \n\n"
        "You will complete two types of trials:\n"
        "1. Visual only: You will see a shape twice, each time with a different pairing.\n"
        "2. Auditory only: You will hear two sounds in sequence, one is correct, one is not.\n"
        "For each, press '1' if the first matches, '2' if the second matches.\n"
        "You will receive feedback after each response.\n\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"
    if instruction_result != "space":
        print("Block 2 Unimodal skipped.")
        return "skip"

    # Prepare trial lists using explicit pairings
    visual_only_trials = []
    for v in visual_shape_pairs:
        for _ in range(15 // 2):
            # Congruent first
            distractors = [f for f in [vv[1] for vv in visual_shape_pairs] if f != v[1]]
            distractor = random.choice(distractors)
            visual_only_trials.append(("visual", v[0], v[1], [v[1], distractor]))
            # Congruent second
            distractor = random.choice(distractors)
            visual_only_trials.append(("visual", v[0], v[1], [distractor, v[1]]))
    if 15 % 2 != 0:
        for v in visual_shape_pairs:
            distractors = [f for f in [vv[1] for vv in visual_shape_pairs] if f != v[1]]
            if random.random() < 0.5:
                distractor = random.choice(distractors)
                visual_only_trials.append(("visual", v[0], v[1], [v[1], distractor]))
            else:
                distractor = random.choice(distractors)
                visual_only_trials.append(("visual", v[0], v[1], [distractor, v[1]]))
    auditory_only_trials = []
    for a in auditory_sound_pairs:
        for _ in range(15 // 2):
            # Congruent first
            distractors = [f for f in [aa[1] for aa in auditory_sound_pairs] if f != a[1]]
            distractor = random.choice(distractors)
            auditory_only_trials.append(("auditory", a[0], a[1], [a[1], distractor]))
            # Congruent second
            distractor = random.choice(distractors)
            auditory_only_trials.append(("auditory", a[0], a[1], [distractor, a[1]]))
    if 15 % 2 != 0:
        for a in auditory_sound_pairs:
            distractors = [f for f in [aa[1] for aa in auditory_sound_pairs] if f != a[1]]
            if random.random() < 0.5:
                distractor = random.choice(distractors)
                auditory_only_trials.append(("auditory", a[0], a[1], [a[1], distractor]))
            else:
                distractor = random.choice(distractors)
                auditory_only_trials.append(("auditory", a[0], a[1], [distractor, a[1]]))
    unimodal_trials = visual_only_trials + auditory_only_trials
    random.shuffle(unimodal_trials)

    # Preload images
    shape_files = [v[0] for v in visual_shape_pairs]
    associated_shape_files = [v[1] for v in visual_shape_pairs]
    preloaded_shapes = preload_images("./generated_shapes", shape_files)
    preloaded_associated = preload_images("./generated_associated_shapes", associated_shape_files)

    # Preload both sets of sounds for auditory-only trials
    auditory_first_files = [a[0] for a in auditory_sound_pairs]
    auditory_second_files = [a[1] for a in auditory_sound_pairs]
    preloaded_sounds = preload_sounds_explicit("./generated_sounds", auditory_first_files)
    preloaded_associated_sounds = preload_sounds_explicit("./generated_associated_sounds", auditory_second_files)

    # Feedback
    correct_feedback = visual.ImageStim(win, image="green_tick.png", size=(0.2, 0.2), pos=(0, 0))
    incorrect_feedback = visual.ImageStim(win, image="red_cross.png", size=(0.2, 0.2), pos=(0, 0))

    # Progress bar setup (same as block 1)
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
    TRIALS_BEFORE_BREAK = 35  # Break every 35 trials

    fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
    prompt_visual = visual.TextStim(win, text="Press 1 if FIRST shape matches; 2 if SECOND shape matches.",
                                    color="white", height=0.05, pos=(0, 0))
    prompt_auditory = visual.TextStim(win, text="Press 1 if FIRST sound matches; 2 if SECOND sound matches.",
                                      color="white", height=0.05, pos=(0, 0))
    img_stim = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0, 0))

    for trial_index, trial in enumerate(unimodal_trials):
        event.clearEvents()
        if "escape" in event.getKeys():
            win.close()
            core.quit()
        if "s" in event.getKeys(keyList=["s"]):
            return "skip"

        trial_type = trial[0]
        trial_clock = core.Clock()
        response = None
        correct_answer = None
        order = None

        # --- Fixation before stimulus ---
        fixation.draw()
        progress_bg.draw()
        progress_bar.draw()
        win.flip()
        core.wait(FIXATION_DURATION)  # always 0.3s

        if trial_type == "visual":
            # Show the same shape twice, once with correct associated, once with distractor
            shape_file, associated_shape_file = trial[1], trial[2]
            images = trial[3]

            for i in range(2):
                img_stim.image = os.path.join("./generated_associated_shapes", images[i])
                img_stim.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                core.wait(STIMULUS_DURATION)  # always 1s
                if i == 0:
                    fixation.draw()
                    progress_bg.draw()
                    progress_bar.draw()
                    win.flip()
                    core.wait(FIXATION_DURATION)  # always 0.3s
                else:
                    core.wait(FIXATION_DURATION)  # always 0.3s

            prompt_visual.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            trial_clock.reset()

            while trial_clock.getTime() < 4:  # was 5
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
            correct_answer = "1" if images[0] == associated_shape_file else "2"
            order = images

        elif trial_type == "auditory":
            # Play two sounds, one is correct pair, one is distractor
            sound_file, associated_sound_file = trial[1], trial[2]
            sounds_pair = trial[3]

            for i in range(2):
                fixation.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                core.wait(FIXATION_DURATION)  # always 0.3s
                # Play from associated sounds directory
                preloaded_associated_sounds[sounds_pair[i]].play()
                core.wait(STIMULUS_DURATION)  # always 1s

            prompt_auditory.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            trial_clock.reset()

            while trial_clock.getTime() < 4:  # was 5
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
            correct_answer = "1" if sounds_pair[0] == associated_sound_file else "2"
            order = sounds_pair

        # Feedback
        if response == correct_answer:
            participant_data["block 2 correct"] += 1
            correct_feedback.draw()
        else:
            participant_data["block 2 incorrect"] += 1
            incorrect_feedback.draw()
        win.flip()
        core.wait(0.5)  # always 0.5s

        progress_value += 1.0 / total_trials
        progress_bar = create_progress_bar(progress_value)

        # Log trial
        participant_data["block2_unimodal_log"].append({
            "trial_index": trial_index,
            "trial_type": trial_type,
            "stimulus": trial[1],
            "associated": trial[2],
            "order": order,
            "correct_answer": correct_answer,
            "response": response,
            "reaction_time": reaction_time,
        })

        # Breaks
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
        text="You have completed this block.\n\nPress SPACEBAR to continue.",
        color="lightgrey", height=0.06, pos=(0, 0)
    )
    end_msg.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "s"])
    if "s" in keys:
        return "skip"

    print("Block 2 completed successfully.")
    return "done"

# Block 3 Testing

def block3_testing():
    global participant_data
    participant_data["block3_test_log"] = []

    instruction_result = show_instructions(
        "Block 3 Instructions: \n\n"
        "You will complete four types of trials:\n"
        "1. Visual cue: See a shape, then hear two sounds. Press 1 if the FIRST sound matches, 2 if the SECOND matches.\n"
        "2. Auditory cue: Hear a sound, then see two shapes. Press 1 if the FIRST shape matches, 2 if the SECOND matches.\n"
        "3. Auditory only: Hear a sound, then hear two sounds. Press 1 if the FIRST matches, 2 if the SECOND matches.\n"
        "4. Visual only: See a shape, then see two shapes. Press 1 if the FIRST matches, 2 if the SECOND matches.\n"
        "You will NOT receive feedback.\n\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"

    try:
        # Prepare all trial types for each pair
        test_shape_files = [p[0] for p in test_pairs]
        test_sound_files = [p[1] for p in test_pairs]
        pair_dict = dict(test_pairs)
        inv_pair_dict = {v: k for k, v in test_pairs}

        # For each pair, create all four trial types
        all_trials = []
        for shape, sound in test_pairs:
            # Find incongruent shape/sound
            incongruent_shapes = [s for s in test_shape_files if s != shape]
            incongruent_sounds = [s for s in test_sound_files if s != sound]
            incongruent_shape = random.choice(incongruent_shapes)
            incongruent_sound = random.choice(incongruent_sounds)

            for _ in range(10 // 2):
                # Visual cue: congruent first
                all_trials.append({
                    "trial_type": "visual_cue",
                    "cue": shape,
                    "congruent": sound,
                    "incongruent": incongruent_sound,
                    "order": [sound, incongruent_sound]
                })
                # Visual cue: congruent second
                all_trials.append({
                    "trial_type": "visual_cue",
                    "cue": shape,
                    "congruent": sound,
                    "incongruent": incongruent_sound,
                    "order": [incongruent_sound, sound]
                })
                # Auditory cue: congruent first
                all_trials.append({
                    "trial_type": "auditory_cue",
                    "cue": sound,
                    "congruent": shape,
                    "incongruent": incongruent_shape,
                    "order": [shape, incongruent_shape]
                })
                # Auditory cue: congruent second
                all_trials.append({
                    "trial_type": "auditory_cue",
                    "cue": sound,
                    "congruent": shape,
                    "incongruent": incongruent_shape,
                    "order": [incongruent_shape, shape]
                })
                # Auditory only: congruent first
                all_trials.append({
                    "trial_type": "auditory_only",
                    "cue": sound,
                    "congruent": sound,
                    "incongruent": incongruent_sound,
                    "order": [sound, incongruent_sound]
                })
                # Auditory only: congruent second
                all_trials.append({
                    "trial_type": "auditory_only",
                    "cue": sound,
                    "congruent": sound,
                    "incongruent": incongruent_sound,
                    "order": [incongruent_sound, sound]
                })
                # Visual only: congruent first
                all_trials.append({
                    "trial_type": "visual_only",
                    "cue": shape,
                    "congruent": shape,
                    "incongruent": incongruent_shape,
                    "order": [shape, incongruent_shape]
                })
                # Visual only: congruent second
                all_trials.append({
                    "trial_type": "visual_only",
                    "cue": shape,
                    "congruent": shape,
                    "incongruent": incongruent_shape,
                    "order": [incongruent_shape, shape]
                })

        # If odd, add one more randomly per pair/trial_type to reach 10 per type
        if 10 % 2 != 0:
            pass
        random.shuffle(all_trials)
        total_trials = len(all_trials)

        # Progress bar setup
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
        prompt_sound2 = visual.TextStim(win, text="Press 1 if FIRST sound matches; 2 if SECOND sound matches.",
                                        color="white", height=0.05, pos=(0, 0))
        prompt_shape2 = visual.TextStim(win, text="Press 1 if FIRST shape matches; 2 if SECOND shape matches.",
                                        color="white", height=0.05, pos=(0, 0))
        img_stim = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0, 0))

        TRIALS_BEFORE_BREAK = 60  # Break every 60 trials (~4 breaks)

        for trial_index, trial in enumerate(all_trials):
            if "escape" in event.getKeys():
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                return "skip"

            trial_clock = core.Clock()
            response = None
            correct_answer = None
            order = trial["order"]

            # --- Fixation ---
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # always 0.3s

            # --- Trial logic ---
            if trial["trial_type"] == "visual_cue":
                # Show shape, then play two sounds (congruent/incongruent, random order)
                img_stim.image = os.path.join(test_image_dir, trial["cue"])
                img_stim.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                core.wait(STIMULUS_DURATION)  # always 1s

                for i in range(2):
                    test_sounds[order[i]].play()
                    core.wait(STIMULUS_DURATION)  # always 1s
                    if i == 0:
                        fixation.draw()
                        progress_bg.draw()
                        progress_bar.draw()
                        win.flip()
                        core.wait(FIXATION_DURATION)  # always 0.3s
                    else:
                        core.wait(FIXATION_DURATION)  # always 0.3s

                prompt_sound2.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                trial_clock.reset()

                while trial_clock.getTime() < 4:  # was 5
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
                correct_answer = "1" if order[0] == trial["congruent"] else "2"

            elif trial["trial_type"] == "auditory_cue":
                # Play sound, then show two shapes (congruent/incongruent, random order)
                test_sounds[trial["cue"]].play()
                core.wait(STIMULUS_DURATION)  # always 1s

                for i in range(2):
                    img_stim.image = os.path.join(test_image_dir, order[i])
                    img_stim.draw()
                    progress_bg.draw()
                    progress_bar.draw()
                    win.flip()
                    core.wait(STIMULUS_DURATION)  # always 1s
                    if i == 0:
                        fixation.draw()
                        progress_bg.draw()
                        progress_bar.draw()
                        win.flip()
                        core.wait(FIXATION_DURATION)  # always 0.3s
                    else:
                        core.wait(FIXATION_DURATION)  # always 0.3s

                prompt_shape2.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                trial_clock.reset()

                while trial_clock.getTime() < 4:  # was 5
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
                correct_answer = "1" if order[0] == trial["congruent"] else "2"

            elif trial["trial_type"] == "auditory_only":
                # Play sound, then play two sounds (congruent/incongruent, random order)
                test_sounds[trial["cue"]].play()
                core.wait(STIMULUS_DURATION)  # always 1s

                for i in range(2):
                    test_sounds[order[i]].play()
                    core.wait(STIMULUS_DURATION)  # always 1s
                    if i == 0:
                        fixation.draw()
                        progress_bg.draw()
                        progress_bar.draw()
                        win.flip()
                        core.wait(FIXATION_DURATION)  # always 0.3s
                    else:
                        core.wait(FIXATION_DURATION)  # always 0.3s

                prompt_sound2.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                trial_clock.reset()

                while trial_clock.getTime() < 4:  # was 5
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
                correct_answer = "1" if order[0] == trial["congruent"] else "2"

            elif trial["trial_type"] == "visual_only":
                # Show shape, then show two shapes (congruent/incongruent, random order)
                img_stim.image = os.path.join(test_image_dir, trial["cue"])
                img_stim.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                core.wait(STIMULUS_DURATION)  # always 1s

                for i in range(2):
                    img_stim.image = os.path.join(test_image_dir, order[i])
                    img_stim.draw()
                    progress_bg.draw()
                    progress_bar.draw()
                    win.flip()
                    core.wait(STIMULUS_DURATION)  # always 1s
                    if i == 0:
                        fixation.draw()
                        progress_bg.draw()
                        progress_bar.draw()
                        win.flip()
                        core.wait(FIXATION_DURATION)  # always 0.3s
                    else:
                        core.wait(FIXATION_DURATION)  # always 0.3s

                prompt_shape2.draw()
                progress_bg.draw()
                progress_bar.draw()
                win.flip()
                trial_clock.reset()

                while trial_clock.getTime() < 4:  # was 5
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
                correct_answer = "1" if order[0] == trial["congruent"] else "2"

            # Log results
            participant_data["reaction time"].append(reaction_time)
            trial_data = {
                "trial_index": trial_index,
                "trial_type": trial["trial_type"],
                "cue": trial["cue"],
                "congruent": trial["congruent"],
                "incongruent": trial["incongruent"],
                "order": order,
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time,
            }
            participant_data["block3_test_log"].append(trial_data)

            # Update progress bar
            progress_value += 1.0 / total_trials
            progress_bar = create_progress_bar(progress_value)

            # Break every 60 trials
            if (trial_index + 1) % TRIALS_BEFORE_BREAK == 0 and (trial_index + 1) < total_trials:
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
            color="lightgrey", height=0.06,
            pos=(0, 0)
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


# === DEBUG: Skip to block 3 for debugging ===
DEBUG_SKIP_TO_BLOCK3 = False  # Set to True to skip to block 3

# === DEBUG: Skip to end survey for debugging ===
DEBUG_SKIP_TO_SURVEY = False  # Set to True to skip directly to end survey

# Add this flag:
DEBUG_SKIP_BLOCK3 = False  # Set to True to skip block 3 entirely

# --- Debug skip to end survey ---
if DEBUG_SKIP_TO_SURVEY:
    print("DEBUG: Skipping directly to end survey and end screen.")
    run_end_survey()
    show_end_screen()
    win.close()
    core.quit()

# --- Debug skip all blocks and go to survey ---
if DEBUG_SKIP_TO_BLOCK3 and DEBUG_SKIP_BLOCK3:
    print("DEBUG: Skipping all blocks, proceeding to survey and end screen.")
    run_end_survey()
    show_end_screen()
    # Optionally save empty logs for completeness
    save_block1_crossmodal_to_excel()
    save_block2_unimodal_to_excel()
    save_block3_test_to_excel()
    win.close()
    core.quit()

# --- Counterbalanced workflow ---

if DEBUG_SKIP_TO_BLOCK3:
    print("DEBUG: Skipping directly to block 3 (testing block).")
    if DEBUG_SKIP_BLOCK3:
        print("DEBUG: Skipping block 3 entirely, proceeding to survey and end screen.")
        run_end_survey()
        show_end_screen()
        # Optionally save empty block 1 and 2 logs for completeness
        save_block1_crossmodal_to_excel()
        save_block2_unimodal_to_excel()
        save_block3_test_to_excel()
        win.close()
        core.quit()
    else:
        result = block3_testing()
        if result == "skip":
            win.close(); core.quit()
        save_block3_test_to_excel()
        run_end_survey()
        show_end_screen()
        # Optionally save empty block 1 and 2 logs for completeness
        save_block1_crossmodal_to_excel()
        save_block2_unimodal_to_excel()
        save_block3_test_to_excel()
        win.close()
        core.quit()

# Use participant_id for automatic counterbalancing - even digiit = order 1, odd digit = order 2
last_char = participant_id.strip()[-1] if participant_id.strip() else "0"
if last_char.isdigit():
    order_key = "1" if int(last_char) % 2 == 0 else "2"
else:
    order_key = "1"  # Default to order 1 if no digit
participant_data["order"] = order_key

if order_key == "1":
    # Block 1 → Block 2 → Block 3
    result = block1_crossmodal()
    if result == "skip":
        win.close(); core.quit()
    save_block1_crossmodal_to_excel()

    result = block2_unimodal()
    if result == "skip":
        win.close(); core.quit()
    save_block2_unimodal_to_excel()

    if not DEBUG_SKIP_BLOCK3:
        result = block3_testing()
        if result == "skip":
            win.close(); core.quit()
        save_block3_test_to_excel()
    else:
        print("DEBUG: Skipping block 3 entirely, proceeding to survey and end screen.")

elif order_key == "2":
    # Block 2 → Block 1 → Block 3
    result = block2_unimodal()
    if result == "skip":
        win.close(); core.quit()
    save_block2_unimodal_to_excel()

    result = block1_crossmodal()
    if result == "skip":
        win.close(); core.quit()
    save_block1_crossmodal_to_excel()

    if not DEBUG_SKIP_BLOCK3:
        result = block3_testing()
        if result == "skip":
            win.close(); core.quit()
        save_block3_test_to_excel()
    else:
        print("DEBUG: Skipping block 3 entirely, proceeding to survey and end screen.")

# --- End workflow ---

run_end_survey()
show_end_screen()

# Save data after each block (redundant, but safe)
save_block1_crossmodal_to_excel()
save_block2_unimodal_to_excel()
save_block3_test_to_excel()

# Cleanup
win.close()
core.quit()
