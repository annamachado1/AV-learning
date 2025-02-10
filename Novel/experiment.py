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
except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()

# Function to display instructions
def show_instructions(text, allow_skip=False):
    instructions = visual.TextStim(win, text=text, color="white", height=40)
    instructions.draw()
    win.flip()
    while True:
        keys = event.waitKeys(keyList=["space", "escape", "s"] if allow_skip else ["space", "escape"])
        if "escape" in keys:
            win.close()
            core.quit()
        elif "s" in keys and allow_skip:
            return 'skip'
        elif "space" in keys:
            return 'continue'  

# First block: Active learning with interaction
def block_one_interactive():
    instructions_text = (
        "Instructions: \n\n"
        "In this part of the experiment, you will see several shapes on the screen. "
        "Your task is to click on any shape to hear the sound paired with it. "
        "You can click on multiple shapes as many times as you like.\n\n"
        "Explore freely and try to remember the pairings.\n\n"
        "Press SPACEBAR to continue."
    )
    
    if show_instructions(instructions_text, allow_skip=True) == 'skip':
        return 'skip'
    
    grid_positions = [ (-450, 200), (-225, 200), (0, 200), (225, 200), (450, 200),
                      (-450, -200), (-225, -200), (0, -200), (225, -200), (450, -200) ]
    
    random.shuffle(grid_positions)
    
    # load image and sound pairs into visual and audio objects
    stimuli_objects = []
    for idx, (img_file, audio_file) in enumerate(stimuli_pairs):
        image_path = os.path.join(image_dir, img_file)
        audio_path = os.path.join(audio_dir, audio_file)
        if os.path.exists(image_path) and os.path.exists(audio_path):
            img_stim = visual.ImageStim(win, image=image_path, pos=grid_positions[idx], size=(200, 200))
            sound_stim = sound.Sound(audio_path, secs=1.0, stereo=True, hamming=True)
            stimuli_objects.append((img_stim, sound_stim))
    
    
    exploration_time = 60  # allow 60 seconds for processing
    timer = core.Clock()
    
    while timer.getTime() < exploration_time:
        for img_stim, _ in stimuli_objects:
            img_stim.draw()
        win.flip()
        
        mouse = event.Mouse(visible=True)
        if mouse.getPressed()[0]:  # click detected
            for img_stim, sound_stim in stimuli_objects:
                if img_stim.contains(mouse):
                    sound_stim.play()
                    core.wait(1.0)  # ensure audio plays
                    sound_stim.stop()
                    
        keys = event.getKeys()
        if "escape" in keys:
            win.close()
            core.quit()
        elif "s" in keys:
            return 'skip'
    
    return 'done'

# Run experiment in sequence
block_one_result = block_one_interactive()
if block_one_result == 'skip' or block_one_result == 'done':
    show_instructions("Second Block: Matching Task.\n\n"
                      "Press SPACEBAR to continue.")
    block_two()

# Cleanup
win.close()
core.quit()
