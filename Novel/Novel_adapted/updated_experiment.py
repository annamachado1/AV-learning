from psychopy import prefs
prefs.hardware['audioLib'] = ['pygame']  # or try 'pyo', or ['pygame', 'pyo']
import os
os.environ["QT_QPA_PLATFORM"] = "cocoa"
import random
random.seed(42)  # Added fixed seed for consistent random pairings
import pandas as pd
import csv
import time
from psychopy import visual, core, gui, event, sound, prefs 
import numpy as np
import traceback

# === Collect participant ID and set up directories before anything else ===
'''def get_participant_id():
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

    return participant_id'''

def get_participant_id():
    participant_id = input("Enter Participant ID: ")

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

# === Practice trial functions ===
def show_practice_visual_until_space(win, img_path, with_border=False):
    img = visual.ImageStim(win, image=img_path, size=(0.3, 0.4), units="norm")
    if with_border:
        border_size = (img.size[0] + 0.02, img.size[1] + 0.02)
        x, y = img.pos
        border = visual.ShapeStim(
            win,
            vertices=[
                [x - border_size[0]/2, y - border_size[1]/2],
                [x - border_size[0]/2, y + border_size[1]/2],
                [x + border_size[0]/2, y + border_size[1]/2],
                [x + border_size[0]/2, y - border_size[1]/2]
            ],
            closeShape=True,
            lineColor='red',
            fillColor=None,
            lineWidth=5,
            units="norm"
        )
        border.draw()
    img.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

def wait_for_space(win, message="Press SPACE to continue."):
    prompt = visual.TextStim(win, text=message, color="lightgrey", height=0.06)
    prompt.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

def load_practice_stimuli():
    shape_dir = "practice_shapes"
    sound_dir = "practice_sounds"

    visual_target = os.path.join(shape_dir, "target.png")
    visual_associated = os.path.join(shape_dir, "associated.png")
    visual_distractor = os.path.join(shape_dir, "distractor.png")

    audio_target = sound.Sound(os.path.join(sound_dir, "target.wav"))
    audio_associated = sound.Sound(os.path.join(sound_dir, "associated.wav"))
    audio_distractor = sound.Sound(os.path.join(sound_dir, "distractor.wav"))

    return {
        "visual": {
            "target": visual_target,
            "associated": visual_associated,
            "distractor": visual_distractor
        },
        "audio": {
            "target": audio_target,
            "associated": audio_associated,
            "distractor": audio_distractor
        }
    }

def show_practice_fixation(win, red=False):
    fixation = visual.TextStim(win, text="+", color="red" if red else "lightgrey", height=0.1)
    fixation.draw()
    win.flip()
    core.wait(0.5)

def show_practice_feedback(win, correct):
    img_path = "green_tick.png" if correct else "red_cross.png"
    feedback = visual.ImageStim(win, image=img_path, size=(0.2, 0.2))
    feedback.draw()
    win.flip()
    core.wait(1.0)

def show_practice_visual(win, img_path, with_border=False):
    img = visual.ImageStim(win, image=img_path, size=(0.3, 0.4), units="norm")
    if with_border:
        border_size = (img.size[0] + 0.02, img.size[1] + 0.02)
        x, y = img.pos
        border = visual.ShapeStim(
            win,
            vertices=[
                [x - border_size[0]/2, y - border_size[1]/2],
                [x - border_size[0]/2, y + border_size[1]/2],
                [x + border_size[0]/2, y + border_size[1]/2],
                [x + border_size[0]/2, y - border_size[1]/2]
            ],
            closeShape=True,
            lineColor='red',
            fillColor=None,
            lineWidth=5,
            units="norm"
        )
        border.draw()
    img.draw()
    win.flip()
    core.wait(1.0)

def prompt_practice_response(win, text="Press 1 for FIRST, 2 for SECOND."):
    prompt = visual.TextStim(win, text=text, color="lightgrey", height=0.05)
    prompt.draw()
    win.flip()
    clock = core.Clock()
    while clock.getTime() < 5:
        keys = event.getKeys(keyList=["1", "2", "escape"])
        if "escape" in keys:
            win.close()
            core.quit()
        if keys:
            return keys[0]
        core.wait(0.01)
    return "NA"

def run_av_practice(win, stimuli):
    wait_for_space(win, "Crossmodal Trial: Press SPACE to begin.")
    
    show_practice_visual_until_space(win, stimuli["visual"]["target"], with_border=True)
    wait_for_space(win, "This is the target shape.\n\nPress SPACE to hear the sounds.")
    show_practice_fixation(win)

    options = [stimuli["audio"]["target"], stimuli["audio"]["distractor"]]
    random.shuffle(options)
    correct = "1" if options[0] == stimuli["audio"]["target"] else "2"

    for snd in options:
        show_practice_fixation(win)
        snd.play()
        core.wait(1.0)

    response = prompt_practice_response(win, "Press 1 if FIRST sound matches; 2 if SECOND.")
    show_practice_feedback(win, response == correct)

def run_aa_practice(win, stimuli):
    wait_for_space(win, "Unimodal Trial: Press SPACE to begin.")

    show_practice_visual_until_space(win, stimuli["visual"]["target"], with_border=True)
    wait_for_space(win, "This is the target shape.\n\nPress SPACE to see other shapes.")
    show_practice_fixation(win)

    options = [stimuli["visual"]["associated"], stimuli["visual"]["distractor"]]
    random.shuffle(options)
    correct_visual = "1" if options[0] == stimuli["visual"]["associated"] else "2"

    for img_path in options:
        show_practice_visual(win, img_path)
        show_practice_fixation(win)

    response_visual = prompt_practice_response(win, "Press 1 if FIRST shape matches; 2 if SECOND.")
    show_practice_feedback(win, response_visual == correct_visual)

    wait_for_space(win, "Now you'll hear the target sound.\n\nPress SPACE to continue.")
    show_practice_fixation(win, red=True)
    stimuli["audio"]["target"].play()
    core.wait(1.0)

    wait_for_space(win, "Now you'll hear two more sounds.\n\nPress SPACE to continue.")
    show_practice_fixation(win)
    options = [stimuli["audio"]["associated"], stimuli["audio"]["distractor"]]
    random.shuffle(options)
    correct_audio = "1" if options[0] == stimuli["audio"]["associated"] else "2"

    for snd in options:
        show_practice_fixation(win)
        snd.play()
        core.wait(1.0)

    response_audio = prompt_practice_response(win, "Press 1 if FIRST sound matches; 2 if SECOND.")
    show_practice_feedback(win, response_audio == correct_audio)

def run_practice_trials(win, participant_id):
    """Run practice trials with order counterbalanced by participant_id."""

    instructions = visual.TextStim(
        win,
        text=(
        "This is a practice trial.\n"
        "You will be presented with a shape and either sounds or more shapes.\n"
        "Respond using the '1' or '2' keys based on which item matches the target.\n"
        "You will receive feedback after each response.\n\n"
        "Press SPACEBAR to begin."
        ),
        color="lightgray", height=0.06
    )
    instructions.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

    if int(participant_id) % 2 == 0:
        stimuli = load_practice_stimuli()
        run_av_practice(win, stimuli)

        stimuli = load_practice_stimuli()
        run_aa_practice(win, stimuli)
    else:
        stimuli = load_practice_stimuli()
        run_aa_practice(win, stimuli)

        stimuli = load_practice_stimuli()
        run_av_practice(win, stimuli)

    wait_for_space(win, "Practice complete.\n\nPress SPACE to continue.")

def save_unimodal_test_to_excel():
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("unimodal_test_log", []))
    excel_filename = os.path.join(participant_folder, "unimodal_test_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Unimodal test data saved to {excel_filename}")

def save_crossmodal_test_to_excel():
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("crossmodal_test_log", []))
    excel_filename = os.path.join(participant_folder, "crossmodal_test_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Crossmodal test data saved to {excel_filename}")

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
DEBUG_SKIP_TO_SURVEY = False   # Set to True to skip directly to end survey
DEBUG_SKIP_BLOCK3 = False      # Set to True to skip block 3 entirely

# --- Debug skip all blocks and go to survey ---
if DEBUG_SKIP_TO_BLOCK3 and DEBUG_SKIP_BLOCK3:
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

def draw_red_border(win, img_stim):
    # Draws a red border around the given ImageStim
    border_size = (img_stim.size[0] + 0.02, img_stim.size[1] + 0.02)
    x, y = img_stim.pos
    border = visual.ShapeStim(
        win,
        vertices=[
            [x - border_size[0]/2, y - border_size[1]/2],
            [x - border_size[0]/2, y + border_size[1]/2],
            [x + border_size[0]/2, y + border_size[1]/2],
            [x + border_size[0]/2, y - border_size[1]/2]
        ],
        closeShape=True,
        lineColor='red',
        fillColor=None,
        lineWidth=5,
        units="norm"
    )
    border.draw()

def show_red_fixation(win):
    fixation = visual.TextStim(win, text="+", color="red", height=0.1)
    fixation.draw()
    win.flip()
    core.wait(0.5)

# Define block functions next

# Unimodal Modified Trials

def run_unimodal_trials(win, participant_id, n_trials=60):
    from psychopy import visual, sound, core, event
    import os
    import random
    import time

    # Load file lists
    shape_dir = "generated_shapes"
    assoc_shape_dir = "generated_associated_shapes"
    sound_dir = "generated_sounds"
    assoc_sound_dir = "generated_associated_sounds"

    shape_files = sorted([f for f in os.listdir(shape_dir) if f.endswith(".png")])
    sound_files = sorted([f for f in os.listdir(sound_dir) if f.endswith(".wav")])

    assoc_shape_files = sorted([f for f in os.listdir(assoc_shape_dir) if f.endswith(".png")])
    assoc_sound_files = sorted([f for f in os.listdir(assoc_sound_dir) if f.endswith(".wav")])

    feedback_images = {
        "correct": os.path.join("green_tick.png"),
        "incorrect": os.path.join("red_cross.png")
    }

    pairings = list(zip(shape_files, assoc_shape_files, sound_files, assoc_sound_files))
    trial_log = []

    instructions = visual.TextStim(
        win,
        text=(
            "In each trial, you'll see or hear a TARGET followed by two PAIRS.\n"
            "Only one pair correctly matches the target.\n\n"
            "Press 1 if the FIRST pair matches, or 2 if the SECOND does.\n\n"
            "You will receive feedback after each trial.\n\n"
            "Press SPACE to begin."
        ),
        color="lightgray", height=0.06
    )
    instructions.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

    for trial_num in range(n_trials):
        # Select a target pair
        shape_file, assoc_shape_file, sound_file, assoc_sound_file = random.choice(pairings)

        trial_type = random.choice(["visual", "audio"])
        correct_on_left = random.choice([True, False])

        if trial_type == "visual":
            incorrect_assoc_file = random.choice([f for f in assoc_shape_files if f != assoc_shape_file])

            left_pair = (assoc_shape_file if correct_on_left else incorrect_assoc_file)
            right_pair = (incorrect_assoc_file if correct_on_left else assoc_shape_file)

            # --- Left side ---
            target = visual.ImageStim(win, image=os.path.join(shape_dir, shape_file),
                                      pos=(-0.5, 0.3), size=(0.35, 0.45), units="norm")
            assoc_left = visual.ImageStim(win, image=os.path.join(assoc_shape_dir, left_pair),
                                          pos=(-0.5, -0.3), size=(0.35, 0.45), units="norm")
            target.draw()
            win.flip()
            core.wait(0.5)
            assoc_left.draw()
            win.flip()
            core.wait(0.5)

            # Fixation
            fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1)
            fixation.draw()
            win.flip()
            core.wait(0.5)

            # --- Right side ---
            target = visual.ImageStim(win, image=os.path.join(shape_dir, shape_file),
                                      pos=(0.5, 0.3), size=(0.35, 0.45), units="norm")
            assoc_right = visual.ImageStim(win, image=os.path.join(assoc_shape_dir, right_pair),
                                           pos=(0.5, -0.3), size=(0.35, 0.45), units="norm")
            target.draw()
            win.flip()
            core.wait(0.5)
            assoc_right.draw()
            win.flip()
            core.wait(0.5)

        else:  # AUDIO TRIAL
            incorrect_assoc_file = random.choice([f for f in assoc_sound_files if f != assoc_sound_file])
            left_pair = (assoc_sound_file if correct_on_left else incorrect_assoc_file)
            right_pair = (incorrect_assoc_file if correct_on_left else assoc_sound_file)

            # --- Left (audio with left fixation cross) ---
            fixation_left = visual.TextStim(win, text="+", color="lightgrey", pos=(-0.5, 0), height=0.1)
            fixation_left.draw()
            win.flip()
            sound.Sound(os.path.join(sound_dir, sound_file)).play()
            core.wait(0.5)
            core.wait(0.1)
            sound.Sound(os.path.join(assoc_sound_dir, left_pair)).play()
            core.wait(0.5)

            # Fixation
            fixation_center = visual.TextStim(win, text="+", color="lightgrey", pos=(0, 0), height=0.1)
            fixation_center.draw()
            win.flip()
            core.wait(0.5)

            # --- Right (audio with right fixation cross) ---
            fixation_right = visual.TextStim(win, text="+", color="lightgrey", pos=(0.5, 0), height=0.1)
            fixation_right.draw()
            win.flip()
            sound.Sound(os.path.join(sound_dir, sound_file)).play()
            core.wait(0.5)
            core.wait(0.1)  # gap
            sound.Sound(os.path.join(assoc_sound_dir, right_pair)).play()
            core.wait(0.5)

        # Prompt
        prompt = visual.TextStim(
            win,
            text="Which pair matched the target?\n\nPress 1 for FIRST (left)\nPress 2 for SECOND (right)",
            color="lightgrey", height=0.06
        )
        prompt.draw()
        win.flip()
        clock = core.Clock()
        response = None
        rt = None
        while clock.getTime() < 5:
            keys = event.getKeys(keyList=["1", "2", "escape"], timeStamped=clock)
            if keys:
                key, timestamp = keys[0]
                if key == "escape":
                    win.close()
                    core.quit()
                response = key
                rt = timestamp
                break
            core.wait(0.01)

        is_correct = response == ("1" if correct_on_left else "2")

        # Feedback
        feedback_img = visual.ImageStim(
            win,
            image=feedback_images["correct" if is_correct else "incorrect"],
            size=(0.2, 0.2)
        )
        feedback_img.draw()
        win.flip()
        core.wait(1.0)

        trial_log.append({
            "trial": trial_num + 1,
            "trial_type": trial_type,
            "target_shape": shape_file if trial_type == "visual" else "NA",
            "target_sound": sound_file if trial_type == "audio" else "NA",
            "correct_associated": assoc_shape_file if trial_type == "visual" else assoc_sound_file,
            "incorrect_associated": incorrect_assoc_file,
            "left_pair": left_pair,
            "right_pair": right_pair,
            "correct_on_left": correct_on_left,
            "response": response if response else "NA",
            "reaction_time": round(rt, 3) if rt else "NA",
            "correct": is_correct if response else "NA"
        })

    # Save to global participant_data
    if "unimodal_test_log" not in participant_data:
        participant_data["unimodal_test_log"] = []
    participant_data["unimodal_test_log"].extend(trial_log)

    # End message
    end_msg = visual.TextStim(win, text="Unimodal test complete.\n\nPress SPACE to continue.", color="lightgray", height=0.06)
    end_msg.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()


# Crossmodal Testing Block

def run_crossmodal_test_trials(win, participant_id, n_trials=60):
    from psychopy import visual, sound, core, event
    import os
    import time

    shape_dir = "generated_shapes"
    sound_dir = "generated_sounds"
    shape_files = sorted([f for f in os.listdir(shape_dir) if f.endswith(".png")])
    sound_files = sorted([f for f in os.listdir(sound_dir) if f.endswith(".wav")])

    # Assumes shape_01.png <-> sound_01.wav mapping
    pairings = list(zip(shape_files, sound_files))
    trial_log = []

    instructions = visual.TextStim(
        win,
        text=(
            "In each trial, a shape will appear with a sound on the LEFT,\n"
            "then again on the RIGHT with a different sound.\n\n"
            "Only ONE sound matches the shape.\n"
            "Press 1 if the LEFT sound matches, or 2 if the RIGHT sound matches.\n\n"
            "Press SPACE to begin."
        ),
        color="lightgray", height=0.06
    )
    instructions.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

    for trial_num in range(n_trials):
        shape_file, correct_sound_file = random.choice(pairings)
        incorrect_sounds = [s for s in sound_files if s != correct_sound_file]
        incorrect_sound_file = random.choice(incorrect_sounds)

        # Randomize left/right correct pairing
        correct_on_left = random.choice([True, False])

        if correct_on_left:
            left_sound_file = correct_sound_file
            right_sound_file = incorrect_sound_file
            correct_response = "1"
        else:
            left_sound_file = incorrect_sound_file
            right_sound_file = correct_sound_file
            correct_response = "2"

        # Load stimuli
        shape_path = os.path.join(shape_dir, shape_file)
        left_sound = sound.Sound(os.path.join(sound_dir, left_sound_file))
        right_sound = sound.Sound(os.path.join(sound_dir, right_sound_file))

        # Display shape on LEFT + play left sound
        shape_left = visual.ImageStim(win, image=shape_path, pos=(-0.5, 0), size=(0.4, 0.5), units="norm")
        shape_left.draw()
        win.flip()
        left_sound.play()
        core.wait(1.0)

        # Fixation
        fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1)
        fixation.draw()
        win.flip()
        core.wait(0.5)

        # Display shape on RIGHT + play right sound
        shape_right = visual.ImageStim(win, image=shape_path, pos=(0.5, 0), size=(0.4, 0.5), units="norm")
        shape_right.draw()
        win.flip()
        right_sound.play()
        core.wait(1.0)

        # Prompt for response
        prompt = visual.TextStim(
            win,
            text="Which sound matched the shape?\n\nPress 1 for FIRST (left)\nPress 2 for SECOND (right)",
            color="lightgrey", height=0.06
        )
        prompt.draw()
        win.flip()

        clock = core.Clock()
        response = None
        rt = None
        while clock.getTime() < 5:
            keys = event.getKeys(keyList=["1", "2", "escape"], timeStamped=clock)
            if keys:
                key, timestamp = keys[0]
                if key == "escape":
                    win.close()
                    core.quit()
                response = key
                rt = timestamp
                break
            core.wait(0.01)

        is_correct = response == correct_response
        trial_log.append({
            "trial": trial_num + 1,
            "shape": shape_file,
            "correct_sound": correct_sound_file,
            "incorrect_sound": incorrect_sound_file,
            "left_sound": left_sound_file,
            "right_sound": right_sound_file,
            "correct_on_left": correct_on_left,
            "response": response if response else "NA",
            "reaction_time": round(rt, 3) if rt else "NA",
            "correct": is_correct if response else "NA"
        })

    # Save to global participant_data
    if "crossmodal_test_log" not in participant_data:
        participant_data["crossmodal_test_log"] = []
    participant_data["crossmodal_test_log"].extend(trial_log)

    end_msg = visual.TextStim(win, text="Test complete.\n\nPress SPACE to continue.", color="lightgray", height=0.06)
    end_msg.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
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
        result = run_crossmodal_test_trials(win, participant_id, n_trials=60)
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
    #run_practice_trials(win, participant_id)

    result = run_unimodal_trials(win, participant_id, n_trials=60)
    if result == "skip":
        win.close(); core.quit()
    save_unimodal_test_to_excel()

    if not DEBUG_SKIP_BLOCK3:
        result = run_crossmodal_test_trials(win, participant_id, n_trials=60)
        if result == "skip":
            win.close(); core.quit()
        save_crossmodal_test_to_excel()
    else:
        print("DEBUG: Skipping block 3 entirely, proceeding to survey and end screen.")

elif order_key == "2":
    # Block 2 → Block 1 → Block 3
    #run_practice_trials(win, participant_id)
    if not DEBUG_SKIP_BLOCK3:
        result = run_crossmodal_test_trials(win, participant_id, n_trials=60)
        if result == "skip":
            win.close(); core.quit()
        save_crossmodal_test_to_excel()
    else:
        print("DEBUG: Skipping block 3 entirely, proceeding to survey and end screen.")

# --- End workflow ---

run_end_survey()
show_end_screen()

# Save data after each block (redundant, but safe)
save_crossmodal_test_to_excel()
save_unimodal_test_to_excel()

# Cleanup
win.close()
core.quit()