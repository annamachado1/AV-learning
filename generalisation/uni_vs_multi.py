from psychopy import prefs
prefs.hardware['audioLib'] = ['pygame']  # or try 'pyo', or ['pygame', 'pyo']
import os
os.environ["QT_QPA_PLATFORM"] = "cocoa"
import random
#random.seed(42)  # Added fixed seed for consistent random pairings
import pandas as pd
import csv
import time
from psychopy import visual, core, gui, event, sound, prefs 
import numpy as np
import traceback

# This version of the code splits the associated stimuli to be shown on the left and right, with a 0.5s gap in between
# This version has two potential orders
# If participant ID is odd, crossmodal block with feedback first, then unimodal testing block with no feedback
# If participant ID is even, unimodal block with feedback first, then crossmodal testing block with no feedback
# This version does not use the practice block before the main blocks, because it hasn't been updated yet
# Trials should be completely randomized, and unimodal block should be interleaved 1:1 audio and visual
# Participant responses will only be recorded after they have been prompted to answer
# Sounds are stopped before playing the next sound, to avoid overlap

# === Collect participant ID and set up directories before anything else ===

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
    core.wait(0.3)  # changed from 1.0 to 0.3

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
    wait_for_space(win, "Mixed Trial: Press SPACE to begin.")
    
    show_practice_visual_until_space(win, stimuli["visual"]["target"], with_border=True)
    wait_for_space(win, "This is the target shape.")
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
    wait_for_space(win, "Shape/Sound Trials: Press SPACE to begin.")

    show_practice_visual_until_space(win, stimuli["visual"]["target"], with_border=True)
    wait_for_space(win, "This is the target shape.")
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

    wait_for_space(win, "Next you will hear two sounds.\n\nPress SPACE to continue.")
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

    practice_instructions = (
        "Practice Instructions:\n\n"
        "You will first complete a few practice trials to learn how the task works.\n"
        "In each trial, you will see or hear a target stimulus (a shape or a sound).\n"
        "Then, you will be given two options. Your task is to choose which one matches the target.\n\n"
        "Press '1' if the FIRST option matches the target.\n"
        "Press '2' if the SECOND option matches the target.\n\n"
        "You will receive feedback after each response.\n\n"
        "Press SPACEBAR to begin practice."
    )
    instructions = visual.TextStim(
        win,
        text=practice_instructions,
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

def save_crossmodal_with_feedback_to_excel():
    # Save crossmodal with feedback data to Excel in the participant folder as crossmodal_wf_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("crossmodal_wf_log", []))
    excel_filename = os.path.join(participant_folder, "crossmodal_wf_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Crossmodal with feedback data saved to {excel_filename}")

def save_unimodal_with_feedback_to_excel():
    # Save unimodal with feedback data to Excel in the participant folder as unimodal_wf_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("unimodal_wf_log", []))
    excel_filename = os.path.join(participant_folder, "unimodal_wf_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Unimodal with feedback data saved to {excel_filename}")

def save_crossmodal_no_feedback_to_excel():
    # Save crossmodal testing to Excel in the participant folder as crossmodal_nf_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("crossmodal_nf_log", []))
    excel_filename = os.path.join(participant_folder, "crossmodal_nf_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Crossmodal no feedback data saved to {excel_filename}")

def save_unimodal_no_feedback_to_excel():
    # Save unimodal no feedback data to Excel in the participant folder as unimodal_nf_log.xlsx
    import os
    import pandas as pd
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("unimodal_nf_log", []))
    excel_filename = os.path.join(participant_folder, "unimodal_nf_log.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"unimodal no feedback data saved to {excel_filename}")

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
    "crossmodal with feedback correct": 0,
    "crossmodal with feedback incorrect": 0,
    "unimodal with feedback correct": 0,
    "unimodal with feedback incorrect": 0,
    "crossmodal no feedback correct": 0,
    "crossmodal no feedback incorrect": 0,
    "unimodal no feedback correct": 0,
    "unimodal no feedback incorrect": 0,
    "reaction time": [],
    "unimodal with feedback log": [],
}
# Set image/audio directories (adjust as needed for your experiment)
image_dir = "./generated_shapes"
audio_dir = "./generated_sounds"

# === DEBUG: Skip to block 3 for debugging ===
DEBUG_SKIP_TO_BLOCK3 = False  # Set to True to skip to block 3
DEBUG_SKIP_TO_SURVEY = False   # Set to True to skip directly to end survey
DEBUG_SKIP_BLOCK3 = True      # Set to True to skip block 3 entirely

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
    save_crossmodal_with_feedback_to_excel()
    save_unimodal_with_feedback_to_excel()
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


# Store participant data
participant_data.update({
    "crossmodal with feedback correct": 0,      # <-- Add this line
    "crossmodal with feedback incorrect": 0,    # <-- Add this line
    "unimodal with feedback correct": 0,
    "unimodal with feedback incorrect": 0,
    "crossmodal no feedback correct": 0,
    "crossmodal no feedback incorrect": 0,
    "unimodal no feedback correct": 0,
    "unimodal no feedback incorrect": 0,
    "reaction time": [],
    "unimodal with feedback log": [],
})

# === Presentation timing constants ===
STIMULUS_DURATION = 1.0  # seconds, all shapes and sounds
FIXATION_DURATION = 0.5  # seconds, all fixations

# Generate ordered list of paired stimuli (shape_01.png with sound_05.wav, etc.)
stimuli_pairs = [
    ("shape_01.png", "sound_01.wav"),
    ("shape_02.png", "sound_02.wav"),
    ("shape_03.png", "sound_03.wav"),
    ("shape_04.png", "sound_04.wav"),
    ("shape_05.png", "sound_05.wav"),
    ("shape_06.png", "sound_06.wav"),
]


# Preload all sound objects
def preload_sounds(audio_dir):
    sound_dict = {}
    for fname in sorted([f for f in os.listdir(audio_dir) if f.startswith("sound_") and f.endswith(".wav")]):
        sound_dict[fname] = sound.Sound(os.path.join(audio_dir, fname))
    return sound_dict

main_sounds = preload_sounds(audio_dir)

# Preload all images for unimodal visual-only trials
def preload_images(image_dir, image_files):
    return {
        fname: visual.ImageStim(win, image=os.path.join(image_dir, fname), size=(0.3, 0.4))
        for fname in set(image_files)
    }

# Explicitly define visual shape pairings for unimodal (visual only)
visual_shape_pairs = [
    ("shape_01.png", "associated_shape_01.png"),
    ("shape_02.png", "associated_shape_02.png"),
    ("shape_03.png", "associated_shape_03.png"),
    ("shape_04.png", "associated_shape_04.png"),
    ("shape_05.png", "associated_shape_05.png"),
    ("shape_06.png", "associated_shape_06.png"),
]

# Explicitly define auditory sound pairings for unimodal (auditory only)
auditory_sound_pairs = [
    ("sound_01.wav", "associated_sound_01.wav"),
    ("sound_02.wav", "associated_sound_02.wav"),
    ("sound_03.wav", "associated_sound_03.wav"),
    ("sound_04.wav", "associated_sound_04.wav"),
    ("sound_05.wav", "associated_sound_05.wav"),
    ("sound_06.wav", "associated_sound_06.wav"),
]

# Preload associated sounds for unimodal auditory-only trials
def preload_sounds_explicit(audio_dir, sound_files):
    return {
        fname: sound.Sound(os.path.join(audio_dir, fname))
        for fname in set(sound_files)
    }


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

# This function is no longer necessary, the red fixation is drawn manually in the unimodal blocks, but might be useful for practice trials?

'''def show_red_fixation(win):
    fixation = visual.TextStim(win, text="+", color="red", height=0.1)
    fixation.draw()
    win.flip()
    core.wait(0.5)'''

# Define block functions next

# Crossmodal with feedback

def crossmodal_with_feedback():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["crossmodal_wf_log"] = []
    event.clearEvents()

    print("Starting Crossmodal with feedback...")

    instruction_result = show_instructions(
        "INSTRUCTIONS – Crossmodal Block with Feedback\n\n"
        "In this block, you’ll see a SHAPE and then hear TWO SOUNDS, one after the other.\n\n"
        "Only ONE of the sounds is the correct match for the shape.\n\n"
        "When asked to do so:\n"
        "• ‘1’ if the FIRST sound matches the shape\n"
        "• ‘2’ if the SECOND sound matches the shape\n\n"
        "You’ll get FEEDBACK after each response:\n"
        "✓ A green check mark means you were correct.\n"
        "✗ A red X means the other sound was correct.\n\n"
        "Try your best to match the correct sound to the shape.\n\n"
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

        # === DEBUG CHECK: Count how often correct sound is in position 1 or 2 ===
        from collections import Counter
        side_counts = Counter(['1' if t[2][0] == t[1] else '2' for t in crossmodal_trials])
        print("Correct sound position counts:", side_counts)
        # =======================================================================

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

        TRIALS_BEFORE_BREAK = 45  
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
            core.wait(FIXATION_DURATION)  # always 0.5s
            # -------------------------------------

            # --- PRESENTATION ORDER: shape (no sound), then sound 1, then sound 2 ---
            # 1. Show shape (no sound)
            img_stim.image = image_path
            draw_red_border(win, img_stim)
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(STIMULUS_DURATION)  # always 1s

            # 2. Fixation + play first sound
            fixation.pos = (-0.4, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            main_sounds[tones[0]].stop()
            main_sounds[tones[0]].play()
            core.wait(STIMULUS_DURATION)  # always 1s

            # 2.5. Central fixation between sounds
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # typically 0.5s

            # 3. Fixation + play second sound
            fixation.pos = (0.4, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            main_sounds[tones[1]].stop() 
            main_sounds[tones[1]].play()
            core.wait(STIMULUS_DURATION)  # always 1s

            fixation.pos = (0, 0)
            # -----------------------------------------------------------------------

            # Prompt for response
            event.clearEvents()  # ✅ Flush any premature keypresses before collecting input
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
                participant_data["crossmodal with feedback correct"] += 1
                correct_feedback.draw()
            else:
                participant_data["crossmodal with feedback incorrect"] += 1
                incorrect_feedback.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(0.5)  # changed from 0.5 to 0.3 and back to 0.5

            progress_value += 1.0 / total_trials
            progress_bar = create_progress_bar(progress_value)

            try:
                participant_data["crossmodal_wf_log"].append({
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
                    text=(f"You may take a 30 second break.\n\n"
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

        print("crossmodal with feedback completed successfully.")
        return "done"

    except Exception as e:
        print("Error during crossmodal with feedback:")
        traceback.print_exc()
        core.quit()

# Crossmodal no feedback version

def crossmodal_no_feedback():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["crossmodal_nf_log"] = []
    event.clearEvents()

    print("Starting Crossmodal no feedback...")

    instruction_result = show_instructions(
        "INSTRUCTIONS – Crossmodal Block (No Feedback)\n\n"
        "You’ll again see a SHAPE and then hear TWO SOUNDS.\n\n"
        "Only ONE of the sounds is the correct match for the shape.\n\n"
        "When asked to do so:\n"
        "• ‘1’ if the FIRST sound matches the shape\n"
        "• ‘2’ if the SECOND sound matches the shape\n\n"
        "This time, you will NOT get feedback after each response.\n\n"
        "Just do your best to match what you’ve learned.\n\n"
        "Press SPACEBAR to begin.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"
    if instruction_result != "space":
        print("Crossmodal no feedback skipped.")
        return "skip"

    try:
        print("Entering trial loop for Crossmodal no feedback...")
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

        TRIALS_BEFORE_BREAK = 45  
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
            core.wait(FIXATION_DURATION)  # always 0.5s
            # -------------------------------------

            # --- PRESENTATION ORDER: shape (no sound), then sound 1, then sound 2 ---
            # 1. Show shape (no sound)
            img_stim.image = image_path
            draw_red_border(win, img_stim)
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(STIMULUS_DURATION)  # always 1s

            # 2. Fixation + play first sound
            fixation.pos = (-0.4, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            main_sounds[tones[0]].stop()
            main_sounds[tones[0]].play()
            core.wait(STIMULUS_DURATION)  # always 1s

            # 2.5. Central fixation between sounds
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # typically 0.5s

            # 3. Fixation + play second sound
            fixation.pos = (0.4, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            main_sounds[tones[1]].stop()
            main_sounds[tones[1]].play()
            core.wait(STIMULUS_DURATION)  # always 1s

            fixation.pos = (0, 0)
            # -----------------------------------------------------------------------

            # Prompt for response
            event.clearEvents()  # ✅ Flush any premature keypresses before collecting input
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
                participant_data["crossmodal no feedback correct"] += 1
            else:
                participant_data["crossmodal no feedback incorrect"] += 1

            # Show neutral fixation instead of feedback
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(0.5)  # match the feedback duration

            progress_value += 1.0 / total_trials
            progress_bar = create_progress_bar(progress_value)

            try:
                participant_data["crossmodal_nf_log"].append({
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
                    text=(f"You may take a 30 second break.\n\n"
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

        print("crossmodal no feedback completed successfully.")
        return "done"

    except Exception as e:
        print("Error during crossmodal no feedback:")
        traceback.print_exc()
        core.quit()

# Unimodal with feedback

def unimodal_with_feedback():
    global participant_data
    participant_data["unimodal_wf_log"] = []
    event.clearEvents()

    print("Unimodal block with feedback...")

    instruction_result = show_instructions(
        "INSTRUCTIONS – Shape and Sound Matching with Feedback\n\n"
        "In this block, you’ll do TWO kinds of trials:\n\n"
        "1. Shape matching:\n"
        "• You’ll see a TARGET shape, followed by TWO shapes.\n"
        "When asked to do so:\n"
        "• Press ‘1’ if the FIRST shape matches the target.\n"
        "• Press ‘2’ if the SECOND shape matches.\n\n"
        "2. Sound matching:\n"
        "• You’ll hear a TARGET sound, then hear TWO sounds.\n"
        "When asked to do so:\n"
        "• Press ‘1’ if the FIRST sound matches the target.\n"
        "• Press ‘2’ if the SECOND sound matches.\n\n"
        "You’ll get FEEDBACK after each trial:\n"
        "✓ for correct, ✗ for incorrect.\n\n"
        "Press SPACEBAR to begin.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"
    if instruction_result != "space":
        print("Unimodal with feedback skipped.")
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
    # Make sure both trial lists are the same length
    min_length = min(len(visual_only_trials), len(auditory_only_trials))
    visual_only_trials = visual_only_trials[:min_length]
    auditory_only_trials = auditory_only_trials[:min_length]

    # Shuffle each list independently
    random.shuffle(visual_only_trials)
    random.shuffle(auditory_only_trials)

    # Interleave strictly 1:1
    if random.choice([True, False]):
        unimodal_trials = [item for pair in zip(visual_only_trials, auditory_only_trials) for item in pair]
    else:
        unimodal_trials = [item for pair in zip(auditory_only_trials, visual_only_trials) for item in pair]

    # Optional sanity check
    for i in range(1, len(unimodal_trials)):
        assert unimodal_trials[i][0] != unimodal_trials[i - 1][0], f"Error: trial {i} repeats modality"


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

    # Progress bar setup (same as crossmodal)
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
    TRIALS_BEFORE_BREAK = 45  

    # Change: define red fixation for trial start
    fixation_red = visual.TextStim(win, text="+", color="red", height=0.1, pos=(0, 0))
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

        # --- Fixation before stimulus: red if auditory target, grey if visual target ---
        if trial_type == "auditory":
            fixation_red.draw()
        else:
            fixation.draw()
        progress_bg.draw()
        progress_bar.draw()
        win.flip()
        core.wait(FIXATION_DURATION)  # always 0.5s

        if trial_type == "visual":
            shape_file, associated_shape_file = trial[1], trial[2]
            images = trial[3]  # [correct_image, distractor_image] or vice versa

            # 1. Show the target shape in the center
            img_stim.image = os.path.join("./generated_shapes", shape_file)
            img_stim.pos = (0, 0)
            draw_red_border(win, img_stim)
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(STIMULUS_DURATION)  # 1s

            # 2. Fixation in center
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # 0.5s

            # 3. Show first test shape on the LEFT
            img_stim.image = os.path.join("./generated_associated_shapes", images[0])
            img_stim.pos = (-0.4, 0)
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(STIMULUS_DURATION)  # 1s

            # 4. Fixation in center
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # 0.5s

            # 5. Show second test shape on the RIGHT
            img_stim.image = os.path.join("./generated_associated_shapes", images[1])
            img_stim.pos = (0.4, 0)
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(STIMULUS_DURATION)  # 1s

            # Reset position for next trial
            img_stim.pos = (0, 0)
            # -------------------------------------------------------

            event.clearEvents()  # ✅ Flush any premature keypresses before collecting input
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

            # --- Target sound with red fixation and progress bar ---
            fixation_red.pos = (0, 0)
            fixation_red.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()

            # Debug: Print which sound is being played
            print(f"\n🔊 Trial {trial_index} — Trying to play target sound: {sound_file}")

            if sound_file not in preloaded_sounds:
                print(f"❌ ERROR: {sound_file} not found in preloaded_sounds!")
            else:
                try:
                    for snd in preloaded_sounds.values():
                        snd.stop()
                    preloaded_sounds[sound_file].play()
                    print(f"✅ Playing: {sound_file}")
                except Exception as e:
                    print(f"❌ ERROR while trying to play {sound_file}: {e}")
            core.wait(STIMULUS_DURATION)

            # --- Pause between target and test sounds with grey fixation ---
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)

            # 1. First associated sound (LEFT)
            fixation.pos = (-0.4, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            preloaded_associated_sounds[sounds_pair[0]].stop()
            preloaded_associated_sounds[sounds_pair[0]].play()
            core.wait(STIMULUS_DURATION)  # 1s

            # 2. Center fixation between test sounds
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # 0.5s

            # 3. Second associated sound (RIGHT)
            fixation.pos = (0.4, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            preloaded_associated_sounds[sounds_pair[1]].stop()
            preloaded_associated_sounds[sounds_pair[1]].play()
            core.wait(STIMULUS_DURATION)  # 1s

            fixation.pos = (0, 0)

            event.clearEvents()  # ✅ Flush any premature keypresses before collecting input
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
            participant_data["unimodal with feedback correct"] += 1
            correct_feedback.draw()
        else:
            participant_data["unimodal with feedback incorrect"] += 1
            incorrect_feedback.draw()
        progress_bg.draw()
        progress_bar.draw()
        win.flip()
        core.wait(0.5)  # changed from 0.5 to 0.3 and back to 0.5

        progress_value += 1.0 / total_trials
        progress_bar = create_progress_bar(progress_value)

        # Log trial
        participant_data["unimodal_wf_log"].append({
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
                text=(f"You may take a 30 second break.\n\n"
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

    print("unimodal with feedback completed successfully.")
    return "done"

# Unimodal no feedback version

def unimodal_no_feedback():
    global participant_data
    participant_data["unimodal_nf_log"] = []
    event.clearEvents()

    print("Starting Unimodal no feedback...")

    instruction_result = show_instructions(
        "INSTRUCTIONS – Shape and Sound Matching (No Feedback)\n\n"
        "You’ll again complete both shape and sound trials:\n\n"
        "1. Shape trials: See a target shape → then two options\n"
        "2. Sound trials: Hear a target sound → then two options\n\n"
        "When asked to do so:\n"
        "• Press ‘1’ if the FIRST option matches the target\n"
        "• Press ‘2’ if the SECOND option matches\n\n"
        "Please wait until you're asked before responding — don’t press any keys early.\n\n"
        "You will NOT get feedback.\n\n"
        "Press SPACEBAR to begin.",
        ["space"]
    )
    if instruction_result == "s":
        return "skip"
    if instruction_result != "space":
        print("Unimodal no feedback skipped.")
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
    # Make sure both trial lists are the same length
    min_length = min(len(visual_only_trials), len(auditory_only_trials))
    visual_only_trials = visual_only_trials[:min_length]
    auditory_only_trials = auditory_only_trials[:min_length]

    # Shuffle each list independently
    random.shuffle(visual_only_trials)
    random.shuffle(auditory_only_trials)

    # Interleave strictly 1:1
    if random.choice([True, False]):
        unimodal_trials = [item for pair in zip(visual_only_trials, auditory_only_trials) for item in pair]
    else:
        unimodal_trials = [item for pair in zip(auditory_only_trials, visual_only_trials) for item in pair]

    # Optional sanity check
    for i in range(1, len(unimodal_trials)):
        assert unimodal_trials[i][0] != unimodal_trials[i - 1][0], f"Error: trial {i} repeats modality"

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

    # Progress bar setup (same as crossmodal)
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
    TRIALS_BEFORE_BREAK = 45  

    # Change: define red fixation for trial start
    fixation_red = visual.TextStim(win, text="+", color="red", height=0.1, pos=(0, 0))
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

        # --- Fixation before stimulus: red if auditory target, grey if visual target ---
        if trial_type == "auditory":
            fixation_red.draw()
        else:
            fixation.draw()
        progress_bg.draw()
        progress_bar.draw()
        win.flip()
        core.wait(FIXATION_DURATION)  # always 0.5s

        if trial_type == "visual":
            shape_file, associated_shape_file = trial[1], trial[2]
            images = trial[3]  # [correct_image, distractor_image] or vice versa

            # 1. Show the target shape in the center
            img_stim.image = os.path.join("./generated_shapes", shape_file)
            img_stim.pos = (0, 0)
            draw_red_border(win, img_stim)
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(STIMULUS_DURATION)  # 1s

            # 2. Fixation in center
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # 0.5s

            # 3. Show first test shape on the LEFT
            img_stim.image = os.path.join("./generated_associated_shapes", images[0])
            img_stim.pos = (-0.4, 0)
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(STIMULUS_DURATION)  # 1s

            # 4. Fixation in center
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # 0.5s

            # 5. Show second test shape on the RIGHT
            img_stim.image = os.path.join("./generated_associated_shapes", images[1])
            img_stim.pos = (0.4, 0)
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(STIMULUS_DURATION)  # 1s

            # Reset position for next trial
            img_stim.pos = (0, 0)
            # -------------------------------------------------------

            event.clearEvents()  # ✅ Flush any premature keypresses before collecting input
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

            # --- Target sound with red fixation and progress bar ---
            fixation_red.pos = (0, 0)
            fixation_red.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()

            for snd in preloaded_sounds.values():
                snd.stop()
            preloaded_sounds[sound_file].play()
            core.wait(STIMULUS_DURATION)

            # --- Pause between target and test sounds with grey fixation ---
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)

            # 1. First associated sound (LEFT)
            fixation.pos = (-0.4, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            preloaded_associated_sounds[sounds_pair[0]].stop()
            preloaded_associated_sounds[sounds_pair[0]].play()
            core.wait(STIMULUS_DURATION)  # 1s

            # 2. Center fixation between test sounds
            fixation.pos = (0, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # 0.5s

            # 3. Second associated sound (RIGHT)
            fixation.pos = (0.4, 0)
            fixation.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            preloaded_associated_sounds[sounds_pair[1]].stop()
            preloaded_associated_sounds[sounds_pair[1]].play()
            core.wait(STIMULUS_DURATION)  # 1s

            fixation.pos = (0, 0)

            event.clearEvents()  # ✅ Flush any premature keypresses before collecting input
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
            participant_data["unimodal no feedback correct"] += 1
        else:
            participant_data["unimodal no feedback incorrect"] += 1

        # Show neutral fixation instead of feedback
        fixation.pos = (0, 0)
        fixation.draw()
        progress_bg.draw()
        progress_bar.draw()
        win.flip()
        core.wait(0.5)  # match the feedback duration

        progress_value += 1.0 / total_trials
        progress_bar = create_progress_bar(progress_value)

        # Log trial
        participant_data["unimodal_nf_log"].append({
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
                text=(f"You may take a 30 second break.\n\n"
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

    print("unimodal no feedback completed successfully.")
    return "done"


# Use participant_id for automatic counterbalancing - even digiit = order 1, odd digit = order 2
last_char = participant_id.strip()[-1] if participant_id.strip() else "0"
if last_char.isdigit():
    order_key = "1" if int(last_char) % 2 == 0 else "2"
else:
    order_key = "1"  # Default to order 1 if no digit
participant_data["order"] = order_key

if order_key == "1":
    # Unimodal with feedback -> Crossmodal with no feedback

    #run_practice_trials(win, participant_id)

    result = unimodal_with_feedback()
    if result == "skip":
        win.close(); core.quit()
    save_unimodal_with_feedback_to_excel()

    result = unimodal_no_feedback()
    if result == "skip":
        win.close(); core.quit()
    save_unimodal_no_feedback_to_excel()

    result = crossmodal_no_feedback()
    if result == "skip":
        win.close(); core.quit()
    save_crossmodal_no_feedback_to_excel()

elif order_key == "2":
    # Crossmodal with feedback -> Unimodal with no feedback

    #run_practice_trials(win, participant_id)

    result = crossmodal_with_feedback()
    if result == "skip":
        win.close(); core.quit()
    save_crossmodal_with_feedback_to_excel()

    result = crossmodal_no_feedback()
    if result == "skip":
        win.close(); core.quit()
    save_crossmodal_no_feedback_to_excel()

    result = unimodal_no_feedback()
    if result == "skip":
        win.close(); core.quit()
    save_unimodal_no_feedback_to_excel()



# --- End workflow ---
run_end_survey()
show_end_screen()

# Save data after each block (redundant, but safe)
save_crossmodal_with_feedback_to_excel()
save_unimodal_with_feedback_to_excel()
save_crossmodal_no_feedback_to_excel()
save_unimodal_no_feedback_to_excel()

# Cleanup
win.close()
core.quit()