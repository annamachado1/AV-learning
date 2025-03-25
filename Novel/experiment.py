import os
import random
import pandas as pd
import csv
import time
from psychopy import visual, core, event, sound, prefs

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
all_trials = stimuli_pairs * 5  # Each pair appears 5 times
random.shuffle(all_trials)  # Completely randomize order

# Create a PsychoPy window
try:
    # win = visual.Window(fullscr=True, color="gray", units="norm", monitor='testMonitor', allowGUI=True)
    win = visual.Window(size=[1200, 800], color="gray", units="norm", allowGUI=True, pos=[0, 0])

except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()

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
            return "passive"  # User selected Passive test
        elif "2" in keys:
            return "active"  # User selected Active test
        elif "space" in keys:
            return "continue"


# Main menu
def main_menu():
    instructions_text = (
        "Welcome to the experiment!\n\n"
        "Press 1 for Passive Test\n"
        "Press 2 for Active Test\n\n"
        "Press ESC to quit."
    )
    
    return show_instructions(instructions_text, ["1", "2"])

        

# First block: Passive viewing of shapes and sounds
def block_one_passive():
    instructions_text = (
        "Instructions: \n\n"
        "In this part of the experiment, you will see shapes on the screen paired with sounds. "
        "Your task is to pay close attention to the sound that corresponds to each shape."
        "There is no need to respond during this block.\n\n"
        "Press SPACEBAR to begin when you are ready."
    )

    show_instructions(instructions_text, ["space"])

    fixation = visual.TextStim(win, text="+", color="white", height=0.1, pos=(0, 0))
    for img_file, audio_file in all_trials:
        if "escape" in event.getKeys():
            win.close()
            core.quit()

        fixation.draw()
        win.flip()
        core.wait(0.5)  # Fixation cross appears for 500ms

        image_path = os.path.join(image_dir, img_file)
        audio_path = os.path.join(audio_dir, audio_file)
        if os.path.exists(image_path) and os.path.exists(audio_path):
            img_stim = visual.ImageStim(win, image=image_path, size=(0.25, 0.35), pos=(0,0))  # Set smaller display size
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
                core.wait(1)  # Default duration (1s) if sound fails

    return 'done'

# First block: Active viewing of shapes and sounds
def block_one_active():
    global participant_data
    
    instructions_text = (
        "Instructions: \n\n"
        "In this part of the experiment, you will see several shapes on the screen. "
        "By clicking on any shape, you will hear its matching sound. " \
        "Your task is to learn these pairings."
        "You can click on the shapes as many times as you like."
        "Once you have learned these pairings, please press the quit button to continue to the next block.\n\n"
        "Press SPACEBAR to start."
    )

    if show_instructions(instructions_text, ["space"]) != "continue":
        return "skip"
    
    participant_data["task order"] = "active"
    
    start_time = time.time()
        
    grid_positions = [
        (-0.6,  0.25), (-0.3,  0.25), (0.0,  0.25), (0.3,  0.25), (0.6,  0.25),
        (-0.6, -0.25), (-0.3, -0.25), (0.0, -0.25), (0.3, -0.25), (0.6, -0.25)
    ]
    random.shuffle(grid_positions)

    stimuli_objects = []
    
    for idx, (img_file, audio_file) in enumerate(stimuli_pairs):
        image_path = os.path.join(image_dir, img_file)
        audio_path = os.path.join(audio_dir, audio_file)
        if os.path.exists(image_path) and os.path.exists(audio_path):
            img_stim = visual.ImageStim(win, image=image_path, pos=grid_positions[idx], size=(0.25, 0.35))
            sound_stim = sound.Sound(audio_path, secs=1.0, stereo=True, hamming=True)
            stimuli_objects.append((img_stim, sound_stim))
            participant_data["click data"][img_file] = {"clicks": 0}

    # Create a timer display
    timer_display = visual.TextStim(win, text="Time Left: 10:00", color="white", pos=(0, 0.75), height=0.07)
    
    quit_button_vertices = [
        (-0.1, -0.05), (0.1, -0.05),
        (0.1, 0.05),   (-0.1, 0.05)
    ]

    quit_button = visual.ShapeStim(
        win,
        vertices=quit_button_vertices,
        fillColor="white",
        pos=(0.75, 0.75),
        closeShape=True
    )
    quit_text = visual.TextStim(
        win,
        text="Quit",
        color="black",
        pos=(0.75, 0.75),
        height=0.07
    )

    timer = core.Clock()
    max_time = 600  # 10 minutes (600 seconds)

    while timer.getTime() < max_time:
        # Update timer text
        time_left = max_time - int(timer.getTime())
        minutes, seconds = divmod(time_left, 60)
        timer_display.text = f"Time Left: {minutes:02}:{seconds:02}"
        
        # Draw stimuli, timer, and quit button
        for img_stim, _ in stimuli_objects:
            img_stim.draw()
        timer_display.draw()
        quit_button.draw()
        quit_text.draw()
        
        win.flip()

        # Check for mouse clicks
        mouse = event.Mouse(visible=True)
        if mouse.getPressed()[0]:  # Left mouse button clicked
            for img_stim, sound_stim in stimuli_objects:
                if img_stim.contains(mouse):
                    sound_stim.play()
                    core.wait(1.0)
                    sound_stim.stop()
                    img_file = img_stim.image.split("/")[-1]
                    participant_data["click data"][img_file]["clicks"] += 1  # Log clicks
            
            # Check if quit button was clicked
            if quit_button.contains(mouse):
                participant_data["time on active task"] = round(time.time() - start_time, 2)
                print("Exiting block one active...")
                return 'done'

        keys = event.getKeys()
        if "escape" in keys:
            win.close()
            core.quit()

    # End timing
    participant_data["time on active task"] = round(time.time() - start_time, 2)  # Store time spent
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
            
        image_path = os.path.join(image_dir, img_file)
        img_stim = visual.ImageStim(win, image=image_path, size=(0.3, 0.4), pos=(0, 0))
        
        # Start timing the trial
        trial_clock = core.Clock()
        
        # Display shape for 1s
        img_stim.draw()
        progress_bg.draw()
        progress_bar.draw()
        win.flip()
        core.wait(1)
        
        # Pick a random incorrect tone
        available_tones = [f"sound_{i:d}.wav" for i in range(1, 11) if f"sound_{i:d}.wav" != audio_file]
        incorrect_tone = random.choice(available_tones)
        
        # Randomly order the two tones
        tones = [audio_file, incorrect_tone]
        random.shuffle(tones)
        
        # Play first tone
        tone1 = sound.Sound(os.path.join(audio_dir, tones[0]), secs=1.0)
        tone1.play()
        core.wait(1)
        tone1.stop()
        
        # Pause before second tone
        core.wait(0.5)
        
        # Play second tone
        tone2 = sound.Sound(os.path.join(audio_dir, tones[1]), secs=1.0)
        tone2.play()
        core.wait(1)
        tone2.stop()
        
        # Show response prompt
        response_prompt = visual.TextStim(
            win,
            text="Press 1 if the first tone matches.\nPress 2 if the second tone matches.",
            color="white",
            height=0.05,
            pos=(0, 0)
        )
        response_prompt.draw()
        progress_bg.draw()
        progress_bar.draw()
        win.flip()
        
        # Start reaction time tracking
        trial_clock.reset()
        # Wait for response but limit total trial duration to 5 seconds
        response = None
        while trial_clock.getTime() < 5:
            keys = event.getKeys(keyList=["1", "2", "escape"])
            if "escape" in keys:
                win.close()
                core.quit()
            elif keys:
                response = keys[0]
                break
            
        reaction_time = round(trial_clock.getTime(), 3)
        participant_data["reaction time"].append(reaction_time)
        
        correct_answer = "1" if tones[0] == audio_file else "2"
        if response == correct_answer:
            participant_data["block 2 correct"] += 1
        else:
            participant_data["block 2 incorrect"] += 1
            
        progress_value += 1.0 / total_trials
        progress_bar = create_progress_bar(progress_value)
        
        trial_data = {
            "subblock": subblock,
            "trial_index": trial_index,
            "stimulus": img_file,
            "audio": audio_file,
            "tones_order": tones,  # randomized tone order
            "correct_answer": correct_answer,
            "response": response,
            "reaction_time": reaction_time
        }
        participant_data["block 2 log"].append(trial_data)

def block_two_break():
    break_message = visual.TextStim(
        win,
        text="Take a short break.\n\nNext part will begin in 30 seconds.",
        color="white",
        height=0.06,
        pos=(0, 0)
    )
    
    break_message.draw()
    win.flip()
    core.wait(30)  # 30 seconds break
    
    continue_message = visual.TextStim(
        win,
        text="Break over. Press SPACEBAR to continue.",
        color="white",
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
        "In this part of the experiment, you will see a shape and hear two tones played one after the other. "
        "Your task is to match the shape with the correct sound.\n\n"
        "If the first tone matches the shape, press '1'. If the second tone matches the shape, press '2'.\n\n"
        "Please respond as quickly as possible. If no response is given within 5 seconds, the next trial will start automatically.\n\n"
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
    filename = f"participant_data_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Task Order", "Time on Active Task (s)", "Block 2 Correct", "Block 2 Incorrect", "Reaction Times"])
        writer.writerow([participant_data["task order"], participant_data["time on active task"], 
                         participant_data["block 2 correct"], participant_data["block 2 incorrect"], participant_data["reaction time"]])
        
        writer.writerow([])  # Separation
        writer.writerow(["Image Click Data"])
        writer.writerow(["Image", "Clicks"])
        
        for img, data in participant_data["click data"].items():
            writer.writerow([img, data["clicks"]])
            
        writer.writerow([])  # Separation
        writer.writerow(["Block 2 Log: Trial Index", "Stimulus", "Audio", "Tone Order", "Correct Answer", "Response", "Reaction Time"])
        for trial in participant_data["block 2 log"]:
            writer.writerow([trial["trial_index"], trial["stimulus"], trial["audio"],
                             ", ".join(trial["tones_order"]), trial["correct_answer"], trial["response"], trial["reaction_time"]])


# Run Experiment
choice = main_menu()
if choice == "passive":
    block_one_passive()
else:
    block_one_active()

show_instructions("Second Block: Matching Task.\n\n"
                      "Press SPACEBAR to continue.", ["space"])
block_two()

save_results()

# Cleanup
win.close()
core.quit()