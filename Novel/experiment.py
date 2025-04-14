import os
import random
import csv
import time
from psychopy import visual, core, event, sound, prefs, gui=

# Configure sound preferences
prefs.hardware['audioLib'] = ['sounddevice', 'pygame']
prefs.general['audioDevice'] = ['default']

image_dir = "./generated_shapes"
audio_dir = "./generated_sounds"

participant_data = {
    "task order": "",
    "time on active task": 0,
    "click data": {},
    "block 2 correct": 0,
    "block 2 incorrect": 0,
    "reaction time": [],
    "block2_log": [],
}

stimuli_pairs = [(f"shape_{i:02d}.png", f"sound_{i:01d}.wav") for i in range(1, 11)]
stimuli_pairs = random.sample(stimuli_pairs, 7)
all_trials = stimuli_pairs * 10  # Each pair appears 5 times
random.shuffle(all_trials)  # Completely randomize order


win = visual.Window(size=[1200, 800], color="gray", units="norm", allowGUI=True, pos=[0, 0])

def show_instructions(text, continue_keys=["1", "2", "space"]):
    instructions = visual.TextStim(win, text=text, color="white", height=0.06, pos=(0, 0))
    instructions.draw()
    win.flip()
    while True:
        keys = event.waitKeys(keyList=continue_keys + ["escape"])
        if "escape" in keys:
            win.close()
            core.quit()
        elif "1" in keys:
            return "passive"
        elif "2" in keys:
            return "active"
        elif "space" in keys:
            return "continue"

def main_menu():
    return show_instructions(
        "Welcome to the experiment!\n\nPress 1 for Passive Test\nPress 2 for Active Test\n\nPress ESC to quit.",
        ["1", "2"]
    )

def block_one_passive():
    show_instructions("In this block, you will be presented with shapes that are paired with sounds. Your task is to observe and listen carefully to memorize these pairings. No response is required. \n\nPress SPACEBAR to begin.", ["space"])
    event.clearEvents()

    fixation = visual.TextStim(win, text="+", color="white", height=0.1, pos=(0, 0))
    for img_file, audio_file in all_trials:
        keys = event.getKeys()
        if "escape" in keys:
            win.close()
            core.quit()

        fixation.draw()
        win.flip()
        core.wait(0.5)

        img_stim = visual.ImageStim(win, image=os.path.join(image_dir, img_file), size=(0.25, 0.35), pos=(0, 0))
        audio_path = os.path.join(audio_dir, audio_file)
        img_stim.draw()
        win.flip()
        try:
            sound_stim = sound.Sound(audio_path, secs=1)
            sound_stim.play()
            core.wait(1)
            sound_stim.stop()
        except Exception as e:
            print(f"Error: {e}")
            core.wait(1)

    return "done"

# # First block: Active viewing of shapes and sounds
# def block_one_active():
#     global participant_data
    
#     instructions_text = (
#         "Instructions: \n\n"
#         "In this part of the experiment, you will see several shapes on the screen. "
#         "By clicking on any shape, you will hear its matching sound. " \
#         "Your task is to learn these pairings."
#         "You can click on the shapes as many times as you like."
#         "Once you have learned these pairings, please press the quit button to continue to the next block.\n\n"
#         "Press SPACEBAR to start."
#     )

#     if show_instructions(instructions_text, ["space"]) != "continue":
#         return "skip"
    
#     participant_data["task order"] = "active"
    
#     start_time = time.time()
        
#     grid_positions = [
#         (-0.6,  0.25), (-0.3,  0.25), (0.0,  0.25), (0.3,  0.25), (0.6,  0.25),
#         (-0.6, -0.25), (-0.3, -0.25), (0.0, -0.25), (0.3, -0.25), (0.6, -0.25)
#     ]
#     random.shuffle(grid_positions)

#     stimuli_objects = []
    
#     for idx, (img_file, audio_file) in enumerate(stimuli_pairs):
#         image_path = os.path.join(image_dir, img_file)
#         audio_path = os.path.join(audio_dir, audio_file)
#         if os.path.exists(image_path) and os.path.exists(audio_path):
#             img_stim = visual.ImageStim(win, image=image_path, pos=grid_positions[idx], size=(0.25, 0.35))
#             sound_stim = sound.Sound(audio_path, secs=1.0, stereo=True, hamming=True)
#             stimuli_objects.append((img_stim, sound_stim))
#             participant_data["click data"][img_file] = {"clicks": 0}

#     # Create a timer display
#     timer_display = visual.TextStim(win, text="Time Left: 10:00", color="lightgrey", pos=(0, 0.75), height=0.07)
    
#     quit_button_vertices = [
#         (-0.1, -0.05), (0.1, -0.05),
#         (0.1, 0.05),   (-0.1, 0.05)
#     ]

#     quit_button = visual.ShapeStim(
#         win,
#         vertices=quit_button_vertices,
#         fillColor="lightgrey",
#         pos=(0.75, 0.75),
#         closeShape=True
#     )
#     quit_text = visual.TextStim(
#         win,
#         text="Quit",
#         color="black",
#         pos=(0.75, 0.75),
#         height=0.07
#     )

#     timer = core.Clock()
#     max_time = 600  # 10 minutes (600 seconds)

#     while timer.getTime() < max_time:
#         # Update timer text
#         time_left = max_time - int(timer.getTime())
#         minutes, seconds = divmod(time_left, 60)
#         timer_display.text = f"Time Left: {minutes:02}:{seconds:02}"
        
#         # Draw stimuli, timer, and quit button
#         for img_stim, _ in stimuli_objects:
#             img_stim.draw()
#         timer_display.draw()
#         quit_button.draw()
#         quit_text.draw()
        
#         win.flip()

#         # Check for mouse clicks
#         mouse = event.Mouse(visible=True)
#         if mouse.getPressed()[0]:  # Left mouse button clicked
#             for img_stim, sound_stim in stimuli_objects:
#                 if img_stim.contains(mouse):
#                     sound_stim.play()
#                     core.wait(1.0)
#                     sound_stim.stop()
#                     img_file = img_stim.image.split("/")[-1]
#                     participant_data["click data"][img_file]["clicks"] += 1  # Log clicks
            
#             # Check if quit button was clicked
#             if quit_button.contains(mouse):
#                 participant_data["time on active task"] = round(time.time() - start_time, 2)
#                 print("Exiting block one active...")
#                 return 'done'

#         keys = event.getKeys()
#         if "escape" in keys:
#             win.close()
#             core.quit()

#     # End timing
#     participant_data["time on active task"] = round(time.time() - start_time, 2)  # Store time spent
#     return "done"

def block_one_active():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["block2_log"] = []

    if show_instructions(
        "In this block, you will see a shape and hear two tones.\n"
        "Your task is to learn which tone is correctly paired with each shape..\n"
        "Press '1' if you think the FIRST tone is paired with the shape.\n"
        "Press '2' if you think the SECOND tone is paired with the shape.\n\n"
        "You will receive feedback after each response.\n\n"
        "Press SPACEBAR to start.",
        ["space"]
    ) != "continue":
        return "skip"

    event.clearEvents()
    active_trials = stimuli_pairs * 10  # changed multiplier from 5 to 10
    random.shuffle(active_trials)
    feedback_duration = 1.0

    for trial_index, (img_file, audio_file) in enumerate(active_trials):
        keys = event.getKeys()
        if "escape" in keys:
            win.close()
            core.quit()

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
        tone2 = sound.Sound(os.path.join(audio_dir, tones[1]), secs=1.0)
        tone1.play()
        core.wait(1)
        tone1.stop()
        core.wait(0.5)
        tone2.play()
        core.wait(1)
        tone2.stop()

        prompt = visual.TextStim(win, text="Press 1 if first tone matches.\nPress 2 if second tone matches.", color="white", height=0.05)
        prompt.draw()
        win.flip()

        event.clearEvents()
        trial_clock = core.Clock()
        response = None
        while trial_clock.getTime() < 5:

            keys = event.getKeys(["1", "2", "escape"])
            if "escape" in keys:
                win.close()
                core.quit()
            elif keys:
                response = keys[0]
                break

        correct_answer = "1" if tones[0] == audio_file else "2"
        feedback_img = visual.ImageStim(win, image="green_tick.png" if response == correct_answer else "red_cross.png", size=(0.2, 0.3))
        feedback_img.draw()
        win.flip()
        core.wait(feedback_duration)

        participant_data["block2_log"].append({
            "trial_index": trial_index,
            "stimulus": img_file,
            "audio": audio_file,
            "tones_order": tones,
            "correct_answer": correct_answer,
            "response": response,
            "reaction_time": round(trial_clock.getTime(), 3)
        })

    return "done"

def block_two_subtrial():
    trials = stimuli_pairs * 10
    random.shuffle(trials)
    return trials

def block_two_subblock(subblock, trials):
    global participant_data
    
    total_trials = len(trials)  # should be 100
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
        
        # Randomly choose trial type: "image+tone" or "audio+image"
        trial_type = random.choice(["image+tone", "audio+image"])
        
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
            core.wait(1)
            tone.stop()
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
            
            # Then show right image for 1 second.
            img_stim_right.draw()
            progress_bg.draw()
            progress_bar.draw()
            win.flip()
            core.wait(1.5)
            
            # Now, display a separate response prompt page.
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


    return "done"

# Second block: Matching task with timing & feedback
def block_two():
    instructions_text = (
        "Instructions: \n\n"
        "In this part, trials will be interleaved.\n"
        "Sometimes you will see an image followed by two tones (image+tone trials).\n"
        "Other times, you will hear one tone and then see two images (audio+image trials).\n\n"
        "For image+tone trials, press '1' if the FIRST tone is correct, '2' if the SECOND tone is correct.\n"
        "For audio+image trials, press '1' if the LEFT image matches the audio, '2' if the RIGHT image matches.\n\n"
        "Please respond as quickly as possible. If no response is given within 3 seconds, the next trial will start automatically.\n\n"
        "Press SPACEBAR to continue."
    )
    show_instructions(instructions_text, ["space"])
    
    num_subblocks = 3
    for subblock in range(1, num_subblocks + 1):
        trials = block_two_subtrial()
        block_two_subblock(subblock, trials)
        if subblock < num_subblocks:
            block_two_break()
        
# def save_results():
#     filename = f"participant_data_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    
#     with open(filename, mode="w", newline="") as file:
#         writer = csv.writer(file)
#         writer.writerow(["Task Order", "Time on Active Task (s)", "Block 2 Correct", "Block 2 Incorrect", "Reaction Times"])
#         writer.writerow([participant_data["task order"], participant_data["time on active task"], 
#                          participant_data["block 2 correct"], participant_data["block 2 incorrect"], participant_data["reaction time"]])
        
#         writer.writerow([])  # Separation
#         writer.writerow(["Image Click Data"])
#         writer.writerow(["Image", "Clicks"])
        
#         for img, data in participant_data["click data"].items():
#             writer.writerow([img, data["clicks"]])
            
#         writer.writerow([])  # Separation
#         writer.writerow(["Block 2 Log: Trial Index", "Stimulus", "Audio", "Tone Order", "Correct Answer", "Response", "Reaction Time"])
#         for trial in participant_data["block 2 log"]:
#             writer.writerow([trial["trial_index"], trial["stimulus"], trial["audio"],
#                              ", ".join(trial["tones_order"]), trial["correct_answer"], trial["response"], trial["reaction_time"]])
            
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

def get_participant_id():
    info = {"Participant ID": ""}
    dlg = gui.DlgFromDict(info, title="Participant Info")  # new function to prompt for ID
    if not dlg.OK:
        core.quit()
    return info["Participant ID"]

# === Main experiment flow ===
participant_id = get_participant_id()  # new: get participant id at start
participant_data["participant_id"] = participant_id

choice = main_menu()

if choice == "passive":
    result = block_one_passive()
elif choice == "active":
    result = block_one_active()
else:
    result = None
    
if result == "done":
    show_instructions("Second Block: Matching Task.\n\n"
                      "Press SPACEBAR to continue.", ["space"])

    block_two()
    save_results()
    show_instructions("Thank you for participating!\n\nPress SPACEBAR to exit.", ["space"])
    
# Cleanup
win.close()
core.quit()

def save_results():
    # Create folder for participant data if it doesn't exist
    data_dir = os.path.join(os.getcwd(), "participant_data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    filename = os.path.join(data_dir, f"results_{participant_data.get('participant_id', 'unknown')}.csv")
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = list(participant_data.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(participant_data)
