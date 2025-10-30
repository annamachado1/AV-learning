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

def save_unimodal_to_excel(matrix, trial_log, type, order):
    try:
        participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
        os.makedirs(participant_folder, exist_ok=True)
        # Construct full file path
        filename = os.path.join(participant_folder, f"Unimodal_{type}s_({order}).xlsx")
        
        # Convert matrix to DataFrame
        column_names = [f"{type}_0{i+1}" for i in range(9)]
        column_names.append(f"{type}_10")
        rows = [f"{type}_0{i+1}" for i in range(9)]
        rows.append(f"{type}_10")
        matrix_data = pd.DataFrame(matrix, columns=column_names, index=rows)

        # Convert trial log to DataFrame
        rows = [[x + 1 for x in trial] + [res + 1] for trial, res in trial_log]
        trial_log_df = pd.DataFrame(rows, columns=[f"{type} 1",f"{type} 2",f"{type} 3",f"Chosen {type}"])
        trial_log_df.index = range(1, len(trial_log) + 1)
        trial_log_df.index.name = "Trial Number"

        with pd.ExcelWriter(filename) as writer:
            trial_log_df.to_excel(writer, sheet_name="Trials", index=True)
            matrix_data.to_excel(writer,sheet_name="Difference_Scores", index=True)

        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Could not save matrix to Excel ({e}). Printing data instead:\n")
        print(matrix)
        print(trial_log)

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

# === Advanced end of survey experiment ===
def run_end_survey_adv():    
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
    mouse_was_pressed = False

    shape_pairings = {}  # pairing states
    tone_by_file  = {t["file"]: t for t in tones} # dictionaries for convenience
    tone_index_by_file = {t["file"]: i for i, t in enumerate(tones)}  # index into tone_positions
    highlight_rect = None

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
        
        mouse_pressed, _, _ = mouse.getPressed()
        clicked_now = mouse_pressed and not mouse_was_pressed
        
        if clicked_now:
            tone_clicked = next((t for t in tones if t["stim"].contains(mouse)), None)

            if tone_clicked is not None:
                for t in tones:
                    tone_sounds[t["file"]].stop()
                tone_sounds[tone_clicked["file"]].play()
                
                if highlight_rect is not None: # Remove the previous highlight, if there is one
                    highlight_rect.setAutoDraw(False)
                    highlight_rect = None
                highlight_rect = highlight_note(tone_clicked["stim"], on=True) # Draw the new highlight
                highlight_rect.setAutoDraw(True)

                selected_tone = tone_clicked # Update the selected tone

            elif selected_tone is not None:
                # Check if a shape was clicked
                clicked_shape = next((s for s in shapes if s["stim"].contains(mouse)), None)
                if clicked_shape is not None:
                    shape_file = clicked_shape["file"]
                    tone_file  = selected_tone["file"]

                    # if shape already has a tone, send old tone back home
                    if shape_file in shape_pairings:
                        old_tone_file = shape_pairings[shape_file]
                        old_tone = tone_by_file[old_tone_file]
                        idx = tone_index_by_file[old_tone_file]
                        old_tone["stim"].pos = (tone_positions[idx], -0.5)
                        old_tone.pop("paired_shape", None)
                        old_tone.pop("new_pos", None)

                    # move selected tone under shape
                    new_pos = (clicked_shape["stim"].pos[0], clicked_shape["stim"].pos[1] - 0.3)
                    selected_tone["stim"].pos = new_pos
                    selected_tone["paired_shape"] = shape_file
                    selected_tone["new_pos"] = new_pos

                    # update mappings
                    for shape, tone in shape_pairings.items():
                        if tone == selected_tone["file"]:
                            del shape_pairings[shape]
                            break
                    shape_pairings[shape_file] = tone_file
                    selected_tone = None

                    if highlight_rect is not None: # remove the highlight since the tone is now paired
                        highlight_rect.setAutoDraw(False) 
                        highlight_rect = None
        mouse_was_pressed = mouse_pressed

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

        for trial_index, (img_file, audio_file, tones) in enumerate(crossmodal_trials):
            event.clearEvents()
            if "escape" in event.getKeys(keyList=["escape"]):
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                return "skip"

            trial_clock = core.Clock()
            image_path = os.path.join(image_dir, img_file)

            # Update progress bar
            progress = trial_index / float((TRIALS_PER_PAIR * 10) - 1)  # progress fraction (0–1)
            width = finalwidth * progress
            progress_bar.width = width
            progress_bar.pos = (left + width/2,cy)
            progress_bar.autoDraw = True
            win.flip()

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

        progress_bar.autoDraw = False
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

# === Triplets block == 
# the main fucnction calls the two triplets blocks in an order based on participant ID
def unisensory_triplets_block():
    numtrials = 50 # must be a multiple of 10 
    try:
        participant_num = int(participant_id[-1]) # Sort participants in half by ID
    except ValueError:
        print("Participant ID not valid, randomizing block order")
        participant_num = random.randint(0,9)

    if participant_num % 2 == 0:
        result = triplets_block_shapes(numtrials)
        if result == "skip":
            print("Triplets block shapes skipped")
        else:
            diffcounts_shapes, trial_log1 = result
            save_unimodal_to_excel(diffcounts_shapes,trial_log1,"shape","first")
        
        result = triplets_block_sounds(numtrials)
        if result == "skip":
            print("Triplets block sounds skipped")
        else:
            diffcounts_sounds, trial_log2 = result
            save_unimodal_to_excel(diffcounts_sounds,trial_log2,"sound","second")
    else:
        result = triplets_block_sounds(numtrials)
        if result == "skip":
            print("Triplets block sounds skipped")
        else:
            diffcounts_sounds, trial_log2 = result
            save_unimodal_to_excel(diffcounts_sounds,trial_log2,"sound","first")

        result = triplets_block_shapes(numtrials)
        if result == "skip":
            print("Triplets block shapes skipped")
        else:
            diffcounts_shapes, trial_log1 = result
            save_unimodal_to_excel(diffcounts_shapes,trial_log1,"shape","second")

def triplets_block_shapes(numtrials):
    # Setup
    img_stim_left = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(-0.5, 0))
    img_stim_center = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0, 0))
    img_stim_right = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0.5, 0))
    mouse = event.Mouse(win=win)

    diff_cts =  np.zeros((10,10), dtype=int)
    
    all_shapes = [pair[0] for pair in stimuli_pairs]
    image_path_list = []
    for img_file in all_shapes:
        image_path_list.append(os.path.join(image_dir, img_file))

    instructions = visual.TextStim(
        win,
        text="Pick The Shape That You Think Doesn't Belong",
        pos=(0, 0.55),
        height=0.08,
        color="lightgray",
        wrapWidth=1.4,
        alignText="center",
    )
    
    # Make the trials
    trial_list = []
    item_uses = np.zeros((10), dtype=int)
    for _ in range(numtrials):
        trial, item_uses = pick_triplet_trial(item_uses)
        trial_list.append(trial)
    trial_log = []

    # Show instructions
    instr_result = show_instructions(
        "INSTRUCTIONS\n\n"
        "In this section you will be presented with three shapes.\n"
        "Click on the shape you feel is the odd on out.\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instr_result == "s":
        print("Triplets shapes block skipped.")
        return "skip"
    
    # Make the progress bar
    cx, cy = 0, -0.6
    finalwidth = 1.4
    left = cx - (finalwidth / 2)
    progress_bar = visual.Rect(
        win,
        width=0.001, height=0.05,  # start at 0%
        pos=(cx, cy),
        lineColor="white", fillColor="white",
        autoDraw=False, name="progress_bar"
    )

    for idx, trial in enumerate(trial_list):
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
        
        instructions.draw()
        instructions.autoDraw = True

        # 1) Draw all shapes
        img_stim_left.image = image_path_list[trial[0]]
        img_stim_center.image = image_path_list[trial[1]]
        img_stim_right.image = image_path_list[trial[2]]
        img_stim_left.autoDraw = True
        img_stim_center.autoDraw = True
        img_stim_right.autoDraw = True
        win.flip()

        # Update progress bar
        progress = idx / float(numtrials - 1)  # progress fraction (0–1)
        width = finalwidth * progress
        progress_bar.width = width
        progress_bar.pos = (left + width/2,cy)
        progress_bar.autoDraw = True
        win.flip()

        # Response, print the selected shape index
        trial_clock = core.Clock()
        mouse.clickReset()
        prev_buttons = mouse.getPressed()
        clicked_index = None

        while trial_clock.getTime() < 5:
            # Allow skip/quit during response window
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
            # Detect a fresh click (transition from not pressed to pressed)
            if any(buttons) and not any(prev_buttons):
                # Check where the mouse is at click-down
                if img_stim_left.contains(mouse):
                    clicked_index = trial[0]
                elif img_stim_center.contains(mouse):
                    clicked_index = trial[1]
                elif img_stim_right.contains(mouse):
                    clicked_index = trial[2]
                if clicked_index is not None:
                    result = [] # list of indices in the trial, first is clicked, second and third are not
                    for idx in trial:
                        if idx == clicked_index:
                            result.insert(0, idx)
                        else:
                            result.append(idx)
                    diff_cts[result[0], result[1]] += 1
                    diff_cts[result[1], result[0]] += 1
                    diff_cts[result[0], result[2]] += 1
                    diff_cts[result[2], result[0]] += 1

                    diff_cts[result[1], result[2]]-= 1
                    diff_cts[result[2], result[1]] -= 1
                    trial_log.append([trial,result[0]])   
                    break  # move to next trial

            prev_buttons = buttons
            core.wait(0.01)  # short poll to avoid busy-waiting
        if clicked_index is None:
            pass

    progress_bar.autoDraw = False
    instructions.autoDraw = False
    img_stim_left.autoDraw = False
    img_stim_center.autoDraw = False
    img_stim_right.autoDraw = False

    end_msg = visual.TextStim(
        win,
        text="You have completed this block.\n\nPress SPACEBAR to continue.",
        color="lightgrey", height=0.06, pos=(0, 0)
    )

    end_msg.draw()
    win.flip()
    event.waitKeys(keyList=["space"])

    return diff_cts, trial_log

def triplets_block_sounds(numtrials):
    # Setup
    all_sounds = [pair[1] for pair in stimuli_pairs]
    diff_cts = np.zeros((10,10), dtype=int) 
    
    # Make the trials
    uses = np.zeros((10), dtype=int)
    trial_list = []
    for _ in range(numtrials):
        trial, uses = pick_triplet_trial(uses)
        trial_list.append(trial)
    trial_log = []
    
    # Show instructions
    instr_result = show_instructions(
        "INSTRUCTIONS\n\n"
        "You will hear three sounds.\n"
        "Click the sound that you think is the odd one out.\n"
        "Press SPACEBAR to continue.",
        ["space"]
    )
    if instr_result == "s":
        print("Triplets (sounds) block skipped.")
        return "skip"
    
    # Build three clicable music notes
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

    # Create the notes
    note1 = note_left()
    note2 = note_center()
    note3 = note_right()
    notes = [note1, note2, note3]

    # Build a replay button
    def button(label, center_pos, color):
        padding = (0.14, 0.05)
        w, h = padding[0] * 2.4, padding[1] * 2.4
        rect = visual.Rect(win, width=w, height=h, pos=center_pos, fillColor= color, lineColor=None, opacity=1)
        text = visual.TextStim(win, text=label, pos=center_pos, height=0.06, color="white")
        return rect, text
    
    # Makes the Replay buttons
    rone_rect, rone_text = button("Replay", (-0.5, -0.3), "#4C7BF1")
    rtwo_rect, rtwo_text = button("Replay", (0, -0.3), "#4C7BF1") #Replay buttons
    rthree_rect, rthree_text = button("Replay", (0.5, -0.3), "#4C7BF1")

    # Define the instructions
    instructions = visual.TextStim(
        win,
        text="Pick The Sound That You Think Doesn't Belong",
        pos=(0, 0.55),
        height=0.08,
        color="lightgray",
        wrapWidth=1.4,
        alignText="center",
    )

    # Make the progress bar
    cx, cy = 0, -0.6
    finalwidth = 1.4
    left = cx - (finalwidth / 2)
    progress_bar = visual.Rect(
        win,
        width=0.001, height=0.05,  # start at 0%
        pos=(cx, cy),
        lineColor="white", fillColor="white", name="progressbar"
    )

    mouse = event.Mouse(win=win)

    # Trial loop
    for idx, trial in enumerate(trial_list):
        event.clearEvents()
        mouse.clickReset()
        if "escape" in event.getKeys(keyList=["escape"]):
            win.close(); core.quit()
        if "s" in event.getKeys(keyList=["s"]):
            return "skip"
    
        # Draw notes
        for n in notes:
            n.draw()
            n.autoDraw = True

        # Draw Progress Bar
        progress = idx / float(numtrials - 1)  # progress fraction (0–1)
        width = finalwidth * progress
        progress_bar.width = width
        progress_bar.pos = (left + width/2,cy)
        progress_bar.autoDraw = True
        win.flip()
        
        # Write Instructions
        instructions.draw()
        instructions.autoDraw = True

        # Play sounds and highlight notes
        main_sounds[all_sounds[trial[0]]].stop()
        main_sounds[all_sounds[trial[0]]].play()
        highlight = highlight_note(notes[0])
        highlight.draw()
        notes[0].draw()
        win.flip()
        core.wait(STIMULUS_DURATION + 0.4)

        main_sounds[all_sounds[trial[1]]].stop()
        main_sounds[all_sounds[trial[1]]].play()
        highlight = highlight_note(notes[1])
        highlight.draw()
        notes[1].draw()
        win.flip()
        core.wait(STIMULUS_DURATION + 0.4)

        main_sounds[all_sounds[trial[2]]].stop()
        main_sounds[all_sounds[trial[2]]].play()
        highlight = highlight_note(notes[2])
        highlight.draw()
        notes[2].draw()
        win.flip()
        core.wait(STIMULUS_DURATION + 0.4)
    
        # Loop logic
        clicked = False
        was_down = False
        canreplay1 = True
        canreplay2 = True
        canreplay3 = True

        while not clicked:
            if "escape" in event.getKeys(keyList=["escape"]):
                win.close(); core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                for n in notes:
                    n.autoDraw = False
                instructions.autoDraw = False
                progress_bar.autoDraw = False
                win.flip()
                return "skip"
        
            # Draw replay buttons
            rone_rect.draw();  rone_text.draw()
            rtwo_rect.draw();  rtwo_text.draw()
            rthree_rect.draw(); rthree_text.draw()
            win.flip()

            # Handle mouse clicks
            is_down = mouse.getPressed()[0] == 1

            # Replay button logic
            if canreplay1:
                rone_rect.fillColor = "#4C7BF1"
            else:
                rone_rect.fillColor = "#565656"
            if canreplay2:
                rtwo_rect.fillColor = "#4C7BF1"
            else:
                rtwo_rect.fillColor = "#565656"
            if canreplay3:
                rthree_rect.fillColor = "#4C7BF1"
            else:
                rthree_rect.fillColor = "#565656"
            
            if is_down and not was_down:
                # Notes
                if notes[0].contains(mouse):
                    result = [trial[0], trial[1], trial[2]]
                    clicked = True
                elif notes[1].contains(mouse):
                    result = [trial[1], trial[0], trial[2]]
                    clicked = True
                elif notes[2].contains(mouse):
                    result = [trial[2], trial[0], trial[1]]
                    clicked = True
                
                # Replay buttons
                elif (abs(mouse.getPos()[0] - rone_rect.pos[0]) <= rone_rect.width / 2) and (abs(mouse.getPos()[1] - rone_rect.pos[1]) <= rone_rect.height / 2):
                    if canreplay1:
                        main_sounds[all_sounds[trial[0]]].stop()
                        main_sounds[all_sounds[trial[0]]].play()
                        hightlight = highlight_note(notes[0])
                        hightlight.draw()
                        win.flip()
                        core.wait(STIMULUS_DURATION)
                        canreplay1 = False
                elif (abs(mouse.getPos()[0] - rtwo_rect.pos[0]) <= rtwo_rect.width / 2) and (abs(mouse.getPos()[1] - rtwo_rect.pos[1]) <= rtwo_rect.height / 2):
                    if canreplay2:
                        main_sounds[all_sounds[trial[1]]].stop()
                        main_sounds[all_sounds[trial[1]]].play()
                        hightlight = highlight_note(notes[1])
                        hightlight.draw()
                        win.flip()
                        core.wait(STIMULUS_DURATION)
                        canreplay2 = False
                elif (abs(mouse.getPos()[0] - rthree_rect.pos[0]) <= rthree_rect.width / 2) and (abs(mouse.getPos()[1] - rthree_rect.pos[1]) <= rthree_rect.height / 2):
                    if canreplay3:
                        main_sounds[all_sounds[trial[2]]].stop()
                        main_sounds[all_sounds[trial[2]]].play()
                        hightlight = highlight_note(notes[2])
                        hightlight.draw()
                        win.flip()
                        core.wait(STIMULUS_DURATION)
                        canreplay3 = False

                if clicked:
                    diff_cts[result[0], result[1]] += 1
                    diff_cts[result[1], result[0]] += 1
                    diff_cts[result[0], result[2]] += 1
                    diff_cts[result[2], result[0]] += 1

                    diff_cts[result[1], result[2]] -= 1
                    diff_cts[result[2], result[1]] -= 1  
                    trial_log.append([trial,result[0]])
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
        text="You have completed this block.\n\nPress SPACEBAR to continue.",
        color="lightgrey", height=0.06, pos=(0, 0)
    )

    end_msg.draw()
    win.flip()
    event.waitKeys(keyList=["space"])

    return diff_cts, trial_log

# === Helper function for making trials in the unisensory block === 
def pick_triplet_trial(uses):
    min_use = min(uses)
    candidates = [i for i, u in enumerate(uses) if u == min_use]
    if len(candidates) >= 3:
        random.shuffle(candidates)
        selection = candidates[:3]
    else:
        selection = list(candidates)

        others = [(uses[i], i) for i in range(10) if i not in candidates]
        random.shuffle(others)
        others.sort(key=lambda x: x[0])
        length_needed = 3 - len(selection)
        selection.extend([idx for _, idx in others[:length_needed]])

    for i in selection:
        uses[i] += 1
    random.shuffle(selection)
    return tuple(selection), uses

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
result = free_pairings_block(intro_text_block1)
if result == "skip":
    print("Free pairings block 1 skipped.")
save_free_pairings_to_excel("free_pairings_block1.xlsx")

# Unisensory Block
unisensory_triplets_block()

# Crossmodal with Feedback (keys: 1 = FIRST, 0 = SECOND; use left/right index fingers)
result = crossmodal_with_feedback()
if result == "skip":
    print("Crossmodal with feedback skipped.")
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
    print("Free pairings block 2 skipped.")
save_free_pairings_to_excel("free_pairings_block2.xlsx")

# End Survey
run_end_survey_adv()

# Save again (redundant but safe)
save_crossmodal_with_feedback_to_excel()

# Cleanup
win.close()
core.quit()