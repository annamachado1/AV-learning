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
    
    # Show target shape
    img_stim = visual.ImageStim(win, image=stimuli["visual"]["target"], size=(0.3, 0.4), pos=(0, 0))
    draw_red_border(win, img_stim)
    img_stim.draw()
    win.flip()
    core.wait(STIMULUS_DURATION)

    # Show fixation cross
    fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
    fixation.draw()
    win.flip()
    core.wait(0.5)

    # Show first sound with fixation on the left
    fixation.pos = (-0.4, 0)
    fixation.draw()
    win.flip()
    stimuli["audio"]["target"].play()
    core.wait(STIMULUS_DURATION)

    # Show fixation cross
    fixation.pos = (0, 0)
    fixation.draw()
    win.flip()
    core.wait(0.5)

    # Show second sound with fixation on the right
    fixation.pos = (0.4, 0)
    fixation.draw()
    win.flip()
    stimuli["audio"]["distractor"].play()
    core.wait(STIMULUS_DURATION)

    # Prompt for response
    prompt = visual.TextStim(win, text="Press 1 if FIRST sound matches; 2 if SECOND.", color="lightgrey", height=0.05)
    prompt.draw()
    win.flip()
    response = prompt_practice_response(win)
    correct = "1" if stimuli["audio"]["target"] == stimuli["audio"]["target"] else "2"
    show_practice_feedback(win, response == correct)

def run_aa_practice(win, stimuli):
    wait_for_space(win, "Shape/Sound Trials: Press SPACE to begin.")

    # Show target shape
    img_stim = visual.ImageStim(win, image=stimuli["visual"]["target"], size=(0.3, 0.4), pos=(0, 0))
    draw_red_border(win, img_stim)
    img_stim.draw()
    win.flip()
    core.wait(STIMULUS_DURATION)

    # Show fixation cross
    fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
    fixation.draw()
    win.flip()
    core.wait(0.5)

    # Show first shape on the left
    img_stim.image = stimuli["visual"]["associated"]
    img_stim.pos = (-0.4, 0)
    img_stim.draw()
    win.flip()
    core.wait(STIMULUS_DURATION)

    # Show fixation cross
    fixation.pos = (0, 0)
    fixation.draw()
    win.flip()
    core.wait(0.5)

    # Show second shape on the right
    img_stim.image = stimuli["visual"]["distractor"]
    img_stim.pos = (0.4, 0)
    img_stim.draw()
    win.flip()
    core.wait(STIMULUS_DURATION)

    # Prompt for response
    prompt = visual.TextStim(win, text="Press 1 if FIRST shape matches; 2 if SECOND.", color="lightgrey", height=0.05)
    prompt.draw()
    win.flip()
    response = prompt_practice_response(win)
    correct = "1" if stimuli["visual"]["associated"] == stimuli["visual"]["associated"] else "2"
    show_practice_feedback(win, response == correct)

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

def save_crossmodal_pairings_to_excel():
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("crossmodal_pairings", []))
    excel_filename = os.path.join(participant_folder, "crossmodal_pairings.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Crossmodal pairings data saved to {excel_filename}")
    # Save to participant data
    participant_data["crossmodal_pairings_data"] = participant_data["crossmodal_pairings"]

def save_unimodal_pairings_to_excel():
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("unimodal_pairings", []))
    excel_filename = os.path.join(participant_folder, "unimodal_pairings.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Unimodal pairings data saved to {excel_filename}")
    # Save to participant data
    participant_data["unimodal_pairings_data"] = participant_data["unimodal_pairings"]

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

# Configure sound preferences
prefs.hardware['audioLib'] = ['pygame', 'sounddevice']
prefs.general['audioDevice'] = ['default']


# Store participant data
participant_data.update({
    "crossmodal with feedback correct": 0,    
    "crossmodal with feedback incorrect": 0, 
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
    ("shape_07.png", "sound_07.wav"),
    ("shape_08.png", "sound_08.wav"),
    ("shape_09.png", "sound_09.wav"),
    ("shape_10.png", "sound_10.wav"),
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
    ("shape_07.png", "associated_shape_07.png"),
    ("shape_08.png", "associated_shape_08.png"),
    ("shape_09.png", "associated_shape_09.png"),
    ("shape_10.png", "associated_shape_10.png"),
]

# Explicitly define auditory sound pairings for unimodal (auditory only)
auditory_sound_pairs = [
    ("sound_01.wav", "associated_sound_01.wav"),
    ("sound_02.wav", "associated_sound_02.wav"),
    ("sound_03.wav", "associated_sound_03.wav"),
    ("sound_04.wav", "associated_sound_04.wav"),
    ("sound_05.wav", "associated_sound_05.wav"),
    ("sound_06.wav", "associated_sound_06.wav"),
    ("sound_07.wav", "associated_sound_07.wav"),
    ("sound_08.wav", "associated_sound_08.wav"),
    ("sound_09.wav", "associated_sound_09.wav"),
    ("sound_10.wav", "associated_sound_10.wav"),
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

# === Pairing blocks ===

# Pairing block for crossmodal condition

def block1_free_pairings():
    global participant_data
    participant_data["free_pairings"] = []

    # Use shape_01.png–shape_10.png and sound_01.wav–sound_10.wav, paired by index
    shape_files = [f"shape_{i:02d}.png" for i in range(1, 11)]
    tone_files = [f"sound_{i:02d}.wav" for i in range(1, 11)]

    # Randomize the order of shapes and tones for display only
    random.shuffle(shape_files)
    random.shuffle(tone_files)

    # Dynamically calculate positions to evenly space shapes and tones
    num_pairs = len(shape_files)
    shape_positions = np.linspace(-0.9, 0.9, num_pairs)
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
        tone_sounds[filename] = main_sounds[filename]

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

    while True:
        for shape in shapes:
            shape["stim"].draw()
        for tone in tones:
            tone["stim"].draw()

        if all("paired_shape" in t for t in tones):
            ready_msg = visual.TextStim(
                win,
                text="All sounds paired – press SPACEBAR to continue",
                color="lightgrey", height=0.05, pos=(0, -0.85)
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
    save_free_pairings_to_excel()

    win.clearBuffer()
    win.flip()
    return 'done'

def save_free_pairings_to_excel():
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("free_pairings", []))
    excel_filename = os.path.join(participant_folder, "free_pairings.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Free pairings data saved to {excel_filename}")

# Crossmodal pairing block

def crossmodal_pair_test():
    """Pairing block for crossmodal condition."""
    global participant_data
    participant_data["crossmodal_pairings"] = []

    # Use shape_01.png–shape_10.png and sound_01.wav–sound_10.wav, paired by index
    shape_files = [f"shape_{i:02d}.png" for i in range(1, 11)]
    tone_files = [f"sound_{i:02d}.wav" for i in range(1, 11)]

    # Randomize the order of shapes and tones for display only
    random.shuffle(shape_files)
    random.shuffle(tone_files)

    # Dynamically calculate positions to evenly space shapes and tones
    num_pairs = len(shape_files)
    shape_positions = np.linspace(-0.9, 0.9, num_pairs)
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
        tone_sounds[filename] = main_sounds[filename]

    selected_tone = None
    mouse = event.Mouse(visible=True)

    instr_result = show_instructions(
        "CROSSMODAL PAIRING BLOCK\n\n"
        "On the next screen, you’ll see a list of shapes and a list of sounds.\n"
        "Click a musical note to hear its sound,\n"
        "then click the shape you think goes with that sound.\n\n"
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
            ready_msg = visual.TextStim(
                win,
                text="All sounds paired – press SPACEBAR to continue",
                color="lightgrey", height=0.05, pos=(0, -0.85)
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

    for tone in tones:
        if "paired_shape" in tone:
            participant_data["crossmodal_pairings"].append({
                "tone_file": tone["file"],
                "shape_file": tone["paired_shape"],
                "tone_pos": tone["new_pos"],
                "shape_pos": next(s["stim"].pos for s in shapes if s["file"] == tone["paired_shape"])
            })

    print("Crossmodal pairings recorded:", participant_data["crossmodal_pairings"])
    save_crossmodal_pairings_to_excel()

    win.clearBuffer()
    win.flip()
    return 'done'

def save_crossmodal_pairings_to_excel():
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    df = pd.DataFrame(participant_data.get("crossmodal_pairings", []))
    excel_filename = os.path.join(participant_folder, "crossmodal_pairings.xlsx")
    df.to_excel(excel_filename, index=False)
    print(f"Crossmodal pairings data saved to {excel_filename}")
    # Save to participant data
    participant_data["crossmodal_pairings_data"] = participant_data["crossmodal_pairings"]

# Crossmodal with feedback

def crossmodal_with_feedback():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["crossmodal_wf_log"] = []
    event.clearEvents()

    print("Starting Crossmodal with feedback...")

    instruction_result = show_instructions(
        "INSTRUCTIONS – Crossmodal Block with Feedback\n\n"
        "In this block, you’ll see a SHAPE and hear a SOUND together.\n\n"
        "The same shape will be presented twice, each time with a different sound.\n\n"
        "Only ONE of the shape-sound pairs is correct.\n\n"
        "When asked to do so:\n"
        "• Press ‘1’ if the FIRST pair is correct.\n"
        "• Press ‘2’ if the SECOND pair is correct.\n\n"
        "You’ll get FEEDBACK after each response:\n"
        "✓ A green check mark means you were correct.\n"
        "✗ A red X means the other pair was correct.\n\n"
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

        correct_feedback = visual.ImageStim(win, image="green_tick.png", size=(0.2, 0.2), pos=(0, 0))
        incorrect_feedback = visual.ImageStim(win, image="red_cross.png", size=(0.2, 0.2), pos=(0, 0))

        fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
        prompt_sound2 = visual.TextStim(win, text="Press 1 if FIRST pair is correct; 2 if SECOND pair is correct.",
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

            # --- PRESENTATION ORDER: shape + sound 1, fixation, shape + sound 2 ---
            # 1. Show shape with sound 1
            img_stim.image = image_path
            img_stim.draw()
            win.flip()
            main_sounds[tones[0]].stop()
            main_sounds[tones[0]].play()
            core.wait(STIMULUS_DURATION)  # always 1s

            # 2. Fixation
            fixation.draw()
            win.flip()
            core.wait(FIXATION_DURATION)  # typically 0.5s

            # 3. Show shape with sound 2
            img_stim.draw()
            win.flip()
            main_sounds[tones[1]].stop()
            main_sounds[tones[1]].play()
            core.wait(STIMULUS_DURATION)  # always 1s
            # -----------------------------------------------------------------------

            # Prompt for response
            event.clearEvents()  # ✅ Flush any premature keypresses before collecting input
            prompt_sound2.draw()
            win.flip()
            trial_clock.reset()

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

        print("crossmodal with feedback completed successfully.")
        return "done"

    except Exception as e:
        print("Error during crossmodal with feedback:")
        traceback.print_exc()
        core.quit()

# Experiment order (same for all participants)
result = block1_free_pairings()
if result == "skip":
    win.close(); core.quit()
save_free_pairings_to_excel()

result = crossmodal_with_feedback()
if result == "skip":
    win.close(); core.quit()
save_crossmodal_with_feedback_to_excel()

result = block1_free_pairings()
if result == "skip":
    win.close(); core.quit()
save_free_pairings_to_excel()

# --- End workflow ---
run_end_survey()
show_end_screen()

# Save data after each block (redundant, but safe)
save_crossmodal_with_feedback_to_excel()

# Cleanup
win.close()
core.quit()
