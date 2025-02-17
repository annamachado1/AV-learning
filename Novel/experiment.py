import os
import random
import pandas as pd
from psychopy import visual, core, event, sound, prefs

# Configure sound preferences
prefs.hardware['audioLib'] = ['sounddevice', 'pygame']
prefs.general['audioDevice'] = ['default']

# Set the path where images and sounds are stored
image_dir = "./generated_shapes"
audio_dir = "./generated_tones"

# Generate ordered list of paired stimuli (each appearing 5 times)
stimuli_pairs = [(f"shape_{i:02d}.png", f"tone_{i:02d}.wav") for i in range(1, 11)]
all_trials = stimuli_pairs * 5  # Each pair appears 5 times
random.shuffle(all_trials)  # Completely randomize order

# Create a PsychoPy window
try:
    win = visual.Window(fullscr=True, color="black", units="pix", monitor='testMonitor', allowGUI=True)
    # win = visual.Window(size=[1600, 1200], color="black", units="pix", allowGUI=True, pos=[0, 0])

except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()

# # Function to display instructions
# def show_instructions(text, allow_skip=False):
#     instructions = visual.TextStim(win, text=text, color="white", height=40)
#     instructions.draw()
#     win.flip()
#     while True:
#         keys = event.waitKeys(keyList=["space", "escape", "s"] if allow_skip else ["space", "escape"])
#         if "escape" in keys:
#             win.close()
#             core.quit()
#         elif "s" in keys and allow_skip:
#             return 'skip'
#         elif "space" in keys:
#             return 'continue'
def show_instructions(text, continue_keys=["1", "2", "space"]):
    instructions = visual.TextStim(win, text=text, color="white", height=40)
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
        "In this part of the experiment, you will see several shapes on the screen. "
        "Your task is to click on any shape to hear the sound paired with it. "
        "You can click on multiple shapes as many times as you like.\n\n"
        "Explore freely and try to remember the pairings.\n\n"
        "Press SPACEBAR to continue."
    )

    show_instructions(instructions_text, ["space"])

    fixation = visual.TextStim(win, text="+", color="white", height=50)
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
            img_stim = visual.ImageStim(win, image=image_path, size=(300, 300))  # Set smaller display size
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
    instructions_text = (
        "Instructions: \n\n"
        "Click on any shape to hear the sound paired with it.\n"
        "Press the quit button to quit and continue to the next block.\n\n"
        "Press SPACEBAR to start."
    )

    if show_instructions(instructions_text, ["space"]) != "continue":
        return "skip"
    
    grid_positions = [(-450, 200), (-225, 200), (0, 200), (225, 200), (450, 200),
                      (-450, -200), (-225, -200), (0, -200), (225, -200), (450, -200)]
    random.shuffle(grid_positions)

    stimuli_objects = []
    click_data = {}  # Dictionary to track clicks
    
    for idx, (img_file, audio_file) in enumerate(stimuli_pairs):
        image_path = os.path.join(image_dir, img_file)
        audio_path = os.path.join(audio_dir, audio_file)
        if os.path.exists(image_path) and os.path.exists(audio_path):
            img_stim = visual.ImageStim(win, image=image_path, pos=grid_positions[idx], size=(200, 200))
            sound_stim = sound.Sound(audio_path, secs=1.0, stereo=True, hamming=True)
            stimuli_objects.append((img_stim, sound_stim))
            click_data[img_file] = 0  # Initialize click count

    # Create a timer display
    timer_display = visual.TextStim(win, text="Time Left: 10:00", color="white", pos=(0, 400), height=40)

    # Create a Quit button
    quit_button = visual.ShapeStim(win, vertices=[(-75, 25), (75, 25), (75, -25), (-75, -25)], fillColor="white", pos=(750, 400))

    quit_text = visual.TextStim(win, text="Quit", color="black", pos=(750, 400), height=30)

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
                    click_data[img_stim.image.split("/")[-1]] += 1  # Increment click count
            
            # Check if quit button was clicked
            if quit_button.contains(mouse):
                print("Exiting block one active...")
                return 'done'

        keys = event.getKeys()
        if "escape" in keys:
            win.close()
            core.quit()

    print("Click Data:", click_data)  # Click statistics
    print("Time Spent:", timer.getTime(), "seconds")  # Time spent

    return 'done'

    

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
    
    for img_file, audio_file in stimuli_pairs:
        if "escape" in event.getKeys():
            win.close()
            core.quit()
        
        image_path = os.path.join(image_dir, img_file)
        img_stim = visual.ImageStim(win, image=image_path, size=(300, 300))  # Smaller shape display
        
        # Start timing the trial
        trial_clock = core.Clock()
        
        # Display shape for 1s
        img_stim.draw()
        win.flip()
        core.wait(1)
        
        # Pick a random incorrect tone
        available_tones = [f"tone_{i:02d}.wav" for i in range(1, 11) if f"tone_{i:02d}.wav" != audio_file]
        incorrect_tone = random.choice(available_tones)
        
        # Randomly order the two tones
        tones = [audio_file, incorrect_tone]
        random.shuffle(tones)
        correct_answer = "1" if tones[0] == audio_file else "2"

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
        response_prompt = visual.TextStim(win, text="Press 1 if the first tone matches.\nPress 2 if the second tone matches.", color="white", height=30)
        response_prompt.draw()
        win.flip()

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
        
        # Determine correctness
        if response == correct_answer:
            feedback_img = "green_tick.png"  # Replace with actual image path
            correct = True
        else:
            feedback_img = "red_cross.png"  # Replace with actual image path
            correct = False
        
        # Show feedback for 1 second
        feedback_stim = visual.ImageStim(win, image=feedback_img, size=(150, 150))  # Smaller feedback icons
        feedback_stim.draw()
        win.flip()
        core.wait(1)
        
# Run Experiment
choice = main_menu()
if choice == "passive":
    block_one_passive()
else:
    block_one_active()

show_instructions("Second Block: Matching Task.\n\n"
                      "Press SPACEBAR to continue.", ["space"])
block_two()

# Cleanup
win.close()
core.quit()
