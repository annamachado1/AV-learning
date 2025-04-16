import os
import random
random.seed(42)  # Added fixed seed for consistent random pairings
import pandas as pd
import csv
import time
from psychopy import visual, core, event, sound, prefs, gui
import numpy as np

# Configure sound preferences
prefs.hardware['audioLib'] = ['sounddevice', 'pygame']
prefs.general['audioDevice'] = ['default']

# Set the path where images and sounds are stored
image_dir = "./generated_shapes"
audio_dir = "./generated_sounds"

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

# Generate ordered list of paired stimuli (each appearing 5 times)
stimuli_pairs = [(f"shape_{i:02d}.png", f"sound_{i:01d}.wav") for i in range(1, 11)]
stimuli_pairs = random.sample(stimuli_pairs, 7)
all_trials = stimuli_pairs * 10  # Each pair appears 10 times
random.shuffle(all_trials)  # Completely randomize order

def get_participant_id():
    info = {"Participant ID": ""}
    dlg = gui.DlgFromDict(info, title="Participant Info")  # new function to prompt for ID
    if not dlg.OK:
        core.quit()
    return info["Participant ID"]

# === Main experiment flow ===
participant_id = get_participant_id()  # new: get participant id at start
participant_data["participant_id"] = participant_id

try:
    win = visual.Window(fullscr=True, color="gray", units="norm", allowGUI=True)

except Exception as e:
    print(f"Error creating window: {str(e)}")
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

    # Load shapes and tones
    shape_files = sorted([f for f in os.listdir(image_dir) if f.startswith("shape_") and f.endswith(".png")])
    tone_files = sorted([f for f in os.listdir(audio_dir) if f.startswith("sound_") and f.endswith(".wav")])

    random.shuffle(shape_files)
    random.shuffle(tone_files)

    shape_positions = np.linspace(-0.8, 0.8, 10)
    tone_positions = np.linspace(-0.8, 0.8, 10)

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

    show_instructions("Click a musical note to hear its sound.\nThen click the shape you wish to pair it with.\n\nPress SPACEBAR when done.", ["space"])

    while True:
        # Draw all shapes and tones
        for shape in shapes:
            shape["stim"].draw()
        for tone in tones:
            tone["stim"].draw()
        win.flip()

        buttons = mouse.getPressed()
        if buttons[0]:
            core.wait(0.05)  # small debounce delay
            # First, check if a tone was clicked
            tone_clicked = None
            for tone in tones:
                if tone["stim"].contains(mouse):
                    tone_clicked = tone
                    break
            if tone_clicked is not None:
                tone_sounds[tone_clicked["file"]].play()
                selected_tone = tone_clicked
            else:
                # No tone was clicked. If a tone is already selected, check for a shape click.
                if selected_tone is not None:
                    for shape in shapes:
                        if shape["stim"].contains(mouse):
                            new_pos = (shape["stim"].pos[0], shape["stim"].pos[1] - 0.3)
                            selected_tone["stim"].pos = new_pos
                            selected_tone["paired_shape"] = shape["file"]
                            selected_tone["new_pos"] = new_pos
                            selected_tone = None
                            break
            # Wait until mouse is released to avoid multiple registrations
            while any(mouse.getPressed()):
                core.wait(0.01)
        keys = event.getKeys()
        if "escape" in keys:
            win.close()
            core.quit()
        elif "space" in keys:
            break

    # Save pairings based on tones that were paired
    for tone in tones:
        if "paired_shape" in tone:
            participant_data["free_pairings"].append({
                "tone_file": tone["file"],
                "shape_file": tone["paired_shape"],
                "tone_pos": tone["new_pos"],
                # Find the shape's original position for recording:
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
    
    return 'done'

# First block: Passive viewing of shapes and sounds

def block_one_passive():
    instructions_text = "You are in the Passive Test.\nPress SPACEBAR to begin viewing the stimuli."
    show_instructions(instructions_text, ["space"])
    # Use free pairings if available; otherwise use default random pairing
    if participant_data.get("free_pairings"):
        local_trials = [(pair["shape_file"], pair["tone_file"]) for pair in participant_data["free_pairings"]]
    else:
        local_stimuli = list(stimuli_pairs)
        random.shuffle(local_stimuli)
        local_trials = local_stimuli
    local_trials = local_trials * 10
    random.shuffle(local_trials)
    
    fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
    for img_file, audio_file in local_trials:
        if "escape" in event.getKeys():
            win.close()
            core.quit()
        fixation.draw()
        win.flip()
        core.wait(0.5)  # Fixation cross appears for 500ms
        image_path = os.path.join(image_dir, img_file)
        audio_path = os.path.join(audio_dir, audio_file)
        if (os.path.exists(image_path) and os.path.exists(audio_path)):
            img_stim = visual.ImageStim(win, image=image_path, size=(0.25, 0.35), pos=(0,0))
            try:
                sound_stim = sound.Sound(audio_path, secs=1, stereo=True, hamming=True)
                img_stim.draw()
                win.flip()
                sound_stim.play()
                core.wait(1)
                sound_stim.stop()
            except Exception as e:
                print(f"Error playing sound {audio_file}: {str(e)}")
                img_stim.draw()
                win.flip()
                core.wait(1)
    return 'done'


def block_one_active():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["block2_log"] = []
    if show_instructions(
        "In this block, you will see a shape and hear two tones.\n"
        "Your task is to learn which tone is correctly paired with the shape.\n"
        "Press '1' if you think the FIRST tone is paired with the shape.\n"
        "Press '2' if you think the SECOND tone is paired with the shape.\n\n"
        "You will receive feedback after each response.\n\n"
        "Press SPACEBAR to start.",
        ["space"]
    ) != "continue":
        return "skip"
    try:
        event.clearEvents()
        # Generate a fresh randomized trial list independent of block zero pairings
        local_stimuli = list(stimuli_pairs)
        random.shuffle(local_stimuli)
        active_trials = local_stimuli * 10
        random.shuffle(active_trials)
        feedback_duration = 1.0
        # Removed stray "x" here

        for trial_index, (img_file, audio_file) in enumerate(active_trials):
            if "escape" in event.getKeys():
                win.close()
                core.quit()
            trial_clock = core.Clock()
            trial_type = random.choice(["audio+image", "image+tone"])
            
            if trial_type == "audio+image":
                # Audio+Image branch:
                tone = sound.Sound(os.path.join(audio_dir, audio_file), secs=1.0)
                tone.play()
                available_images = [pair[0] for pair in stimuli_pairs if pair[0] != img_file]
                distractor = random.choice(available_images)
                images = [img_file, distractor]
                random.shuffle(images)
                left_pos = (-0.3, 0)
                right_pos = (0.3, 0)
                imgL = visual.ImageStim(win, image=os.path.join(image_dir, images[0]),
                                        size=(0.3, 0.4), pos=left_pos)
                imgR = visual.ImageStim(win, image=os.path.join(image_dir, images[1]),
                                        size=(0.3, 0.4), pos=right_pos)
                imgL.draw()
                win.flip()
                core.wait(1.5)
                imgR.draw()
                win.flip()
                core.wait(1.5)
                tone.stop()
                prompt = visual.TextStim(win, text="Press 1 if LEFT image matches; 2 if RIGHT image matches.",
                                         color="white", height=0.05, pos=(0,0))
                prompt.draw()
                win.flip()
                event.clearEvents()
                trial_clock.reset()
                response = None
                while trial_clock.getTime() < 5:
                    keys = event.waitKeys(keyList=["1", "2", "escape"])
                    if "escape" in keys:
                        win.close()
                        core.quit()
                    elif keys:
                        response = keys[0]
                        break
                if response is None:
                    response = "NA"
                reaction_time = round(trial_clock.getTime(), 3)
                if images[0] == img_file:
                    correct_answer = "1"
                else:
                    correct_answer = "2"
            
            elif trial_type == "image+tone":
                # Image+Tone branch:
                image_path = os.path.join(image_dir, img_file)
                img_stim = visual.ImageStim(win, image=image_path, size=(0.3, 0.4), pos=(0, 0))
                img_stim.draw()
                win.flip()
                core.wait(1.0)
                available_tones = [f"sound_{i}.wav" for i in range(1, 11) if f"sound_{i}.wav" != audio_file]
                incorrect_tone = random.choice(available_tones)
                tones = [audio_file, incorrect_tone]
                random.shuffle(tones)
                tone1 = sound.Sound(os.path.join(audio_dir, tones[0]), secs=1.0)
                tone1.play()
                core.wait(1)
                tone1.stop()
                core.wait(0.5)
                tone2 = sound.Sound(os.path.join(audio_dir, tones[1]), secs=1.0)
                tone2.play()
                core.wait(1)
                tone2.stop()
                prompt = visual.TextStim(win, text="Press 1 if FIRST tone matches; 2 if SECOND tone matches.",
                                         color="white", height=0.05, pos=(0,0))
                prompt.draw()
                win.flip()
                event.clearEvents()
                trial_clock.reset()   # Reset clock before response collection
                response = None
                while trial_clock.getTime() < 5:
                    keys = event.waitKeys(keyList=["1", "2", "escape"])
                    if "escape" in keys:
                        win.close()
                        core.quit()
                    elif keys:
                        response = keys[0]
                        break
                if response is None:
                    response = "NA"
                reaction_time = round(trial_clock.getTime(), 3)
                if tones[0] == audio_file:
                    correct_answer = "1"
                else:
                    correct_answer = "2"

            # Log results (unchanged code)
            participant_data["reaction time"].append(reaction_time)
            if response == correct_answer:
                participant_data["block 2 correct"] += 1
            else:
                participant_data["block 2 incorrect"] += 1
            participant_data["block2_log"].append({
                "trial_index": trial_index,
                "trial_type": trial_type,
                "stimulus": img_file,
                "audio": audio_file,
                "tones_order": tones if trial_type=="image+tone" else "N/A",
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time
            })
        return "done"
    except Exception as e:
        print("Error during active test:", e)
        core.quit()

def block_two_subtrial():
    trials = stimuli_pairs * 10
    random.shuffle(trials)
    return trials

def block_two_subblock(subblock, trials):
    global participant_data
    
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
    
    for trial_index, (img_file, audio_file) in enumerate(trials):
        if "escape" in event.getKeys():
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

        
        if trial_type == "image+tone":
            image_path = os.path.join(image_dir, img_file)
            img_stim = visual.ImageStim(win, image=image_path, size=(0.3, 0.4), pos=(0, 0))
            img_stim.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(1)
            
            available_tones = [f"sound_{i:d}.wav" for i in range(1, 11) if f"sound_{i:d}.wav" != audio_file]
            incorrect_tone = random.choice(available_tones)
            tones = [audio_file, incorrect_tone]
            random.shuffle(tones)
            
            tone1 = sound.Sound(os.path.join(audio_dir, tones[0]), secs=1.0)
            tone1.play()
            core.wait(1)
            tone1.stop()
            core.wait(0.5)
            tone2 = sound.Sound(os.path.join(audio_dir, tones[1]), secs=1.0)
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
            while trial_clock.getTime() < 3:
                keys = event.getKeys(keyList=["1", "2", "escape"])
                if "escape" in keys:
                    win.close()
                    core.quit()
                elif keys:
                    response = keys[0]
                    break
            
            reaction_time = round(trial_clock.getTime(), 3)
            correct_answer = "1" if tones[0] == audio_file else "2"
            
        else:
            tone = sound.Sound(os.path.join(audio_dir, audio_file), secs=1.0)
            tone.play()
            core.wait(0.5)
            
            available_images = [pair[0] for pair in stimuli_pairs if pair[0] != img_file]
            distractor_image = random.choice(available_images)
            # Randomize order of correct and distractor image.
            images = [img_file, distractor_image]
            random.shuffle(images)
            
            left_pos = (-0.3, 0)
            right_pos = (0.3, 0)
            
            img_stim_left = visual.ImageStim(win, image=os.path.join(image_dir, images[0]), size=(0.3, 0.4), pos=left_pos)
            img_stim_right = visual.ImageStim(win, image=os.path.join(image_dir, images[1]), size=(0.3, 0.4), pos=right_pos)
            
            img_stim_left.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(1.5)
            
            img_stim_right.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(1.5)
            tone.stop()
            
            response_prompt = visual.TextStim(
                win,
                text="Press 1 if the LEFT image matches the audio.\nPress 2 if the RIGHT image matches.",
                color="lightgrey", height=0.05, pos=(0, 0)
            )
            response_prompt.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            
            trial_clock.reset()
            response = None
            while trial_clock.getTime() < 3:
                keys = event.getKeys(keyList=["1", "2", "escape"])
                if "escape" in keys:
                    win.close()
                    core.quit()
                elif keys:
                    response = keys[0]
                    break
                
            reaction_time = round(trial_clock.getTime(), 3)
            # Determine correct answer based on which image is the actual pairing.
            if images[0] == img_file:
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
            "tones_order": tones if trial_type == "image+tone" else "N/A",
            "correct_answer": correct_answer,
            "response": response,
            "reaction_time": reaction_time
        }
        participant_data["block 2 log"].append(trial_data)

def block_two_break():
    break_message = visual.TextStim(
        win,
        text="Take a short break.\n\nNext part will begin in 30 seconds.",
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
    event.waitKeys(keyList=["space"])  # Wait for spacebar to continue

# Second block: Matching task with timing & feedback
def block_two():
    instructions_text = (
        "Instructions: \n\n"
        "In this part, trials will be interleaved.\n"
        "You will see an image followed by two tones (image+tone trials).\n"
        "You will also hear one tone and then see two images (audio+image trials).\n\n"
        "For image+tone trials, press '1' if the FIRST tone is correct, '2' if the SECOND tone is correct.\n"
        "For audio+image trials, press '1' if the LEFT image matches the audio, '2' if the RIGHT image matches.\n\n"
        "Press SPACEBAR to continue."
    )
    show_instructions(instructions_text, ["space"])
    
    num_subblocks = 3
    for subblock in range(1, num_subblocks + 1):
        trials = block_two_subtrial()
        block_two_subblock(subblock, trials)
        if subblock < num_subblocks:
            block_two_break()
            
def save_results():
    p_id = participant_data["participant_id"]
    summary_filename = f"{p_id}.csv"
    
    with open(summary_filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Participant ID", "Task Order", "Block 2 Correct", "Block 2 Incorrect", "Average Reaction Time (s)"])
        
        # Calculate average reaction time if available
        if participant_data["reaction time"]:
            avg_rt = sum(participant_data["reaction time"]) / len(participant_data["reaction time"])
        else:
            avg_rt = ""
        
        writer.writerow([
            p_id,
            participant_data["task order"],
            participant_data["block 2 correct"],
            participant_data["block 2 incorrect"],
            avg_rt
        ])
        
        writer.writerow([])  # Blank line for separation.
        writer.writerow(["Image Click Data"])
        writer.writerow(["Image", "Clicks"])
        for img, data in participant_data["click data"].items():
            writer.writerow([img, data["clicks"]])

    # Save free pairings based on tones that were paired
    with open(f"{p_id}_free_pairings.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Tone File", "Shape File", "Tone Position", "Shape Position"])
        for pairing in participant_data["free_pairings"]:
            writer.writerow([
                pairing["tone_file"],
                pairing["shape_file"],
                pairing["tone_pos"],
                pairing["shape_pos"]
                ])

    
    # Save detailed block 2 log in another CSV file.
    log_filename = f"{p_id}_block2_log.csv"
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

################### MAIN EXPERIMENTAL FLOW ###################

block_zero_pairing()

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
elif choice == "active":
    result = block_one_active()
else:
    result = None

if result == "done":
    show_instructions("Second Block: Matching Task.\n\nPress SPACEBAR to continue.", ["space"])
    block_two()
    save_results()
    show_instructions("Thank you for participating!\n\nPress SPACEBAR to exit.", ["space"])

# Cleanup
win.close()
core.quit()