import pyglet
pyglet.options['shadow_window'] = False
import os
import random
from psychopy import visual, core, event, sound, prefs

# Configure sound preferences - try multiple backends
prefs.hardware['audioLib'] = ['PTB', 'sounddevice', 'pygame']
prefs.general['audioDevice'] = ['default']

# Set the path where images and sounds are stored
image_dir = "/Users/annamachado/Documents/GitHub/AV-learning/Novel/generated_shapes"   
audio_dir = "/Users/annamachado/Documents/GitHub/AV-learning/Novel/generated_tones"  

# Generate ordered list of paired stimuli
stimuli_pairs = [(f"shape_{i:02d}.png", f"tone_{i:02d}.wav") for i in range(1, 11)]

# Randomize the order of presentation
random.shuffle(stimuli_pairs)

# Create a PsychoPy window with proper frame rate monitoring
try:
    win = visual.Window(fullscr=True, color="black", units="pix", monitor='testMonitor', allowGUI=True)
except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()

# Check frame rate
actualFrameRate = win.getActualFrameRate()
if (actualFrameRate is not None):
    frameDur = 1.0 / round(actualFrameRate)
else:
    frameDur = 1.0 / 60.0  # default to 60 Hz if detection fails
    print("Warning: Could not determine frame rate, defaulting to 60Hz")

# Create instruction screen
instructions = visual.TextStim(win, text="Instructions\n\nPress SPACEBAR to start", color="white", height=40)

# Display instruction screen
instructions.draw()
win.flip()

# Wait for spacebar to start or Esc to exit
while True:
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()
    elif "space" in keys:
        break  # Start experiment

# Create fixation cross
fixation = visual.TextStim(win, text="+", color="white", height=50)

# Loop through randomized trials
for img_file, audio_file in stimuli_pairs:
    # Check for exit key
    if "escape" in event.getKeys():
        win.close()
        core.quit()

    # Show fixation cross for 3 seconds
    fixation.draw()
    win.flip()
    core.wait(3)

    # Load image and sound
    image_path = os.path.join(image_dir, img_file)
    audio_path = os.path.join(audio_dir, audio_file)

    if os.path.exists(image_path) and os.path.exists(audio_path):
        img_stim = visual.ImageStim(win, image=image_path)
        try:
            # More robust sound initialization
            sound_stim = sound.Sound(audio_path, secs=1.0, stereo=True, hamming=True)
            
            # Show image and play sound simultaneously
            img_stim.draw()
            win.flip()
            sound_stim.play()

            # More robust duration handling
            try:
                duration = sound_stim.getDuration()
                if duration is None or duration <= 0:
                    duration = 1.0
            except:
                duration = 1.0
            
            core.wait(duration)
            sound_stim.stop()
        except Exception as e:
            print(f"Error playing sound {audio_file}: {str(e)}")
            # If sound fails, still show image for a fixed duration
            img_stim.draw()
            win.flip()
            core.wait(1.0)  # default duration if sound fails

# Cleanup
win.close()
core.quit()
