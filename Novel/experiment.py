import os
import random
import pandas as pd
from psychopy import visual, core, event, sound, prefs

# Configure sound preferences
prefs.hardware['audioLib'] = ['sounddevice', 'pygame']
prefs.general['audioDevice'] = ['default']

# Set the path where images and sounds are stored
image_dir = "/Users/annamachado/Documents/GitHub/AV-learning/Novel/generated_shapes"
audio_dir = "/Users/annamachado/Documents/GitHub/AV-learning/Novel/generated_tones"

# Generate ordered list of paired stimuli
stimuli_pairs = [(f"shape_{i:02d}.png", f"tone_{i:02d}.wav") for i in range(1, 11)]

# Randomize the order of presentation for Block 1
random.shuffle(stimuli_pairs)

# Create a PsychoPy window
try:
    win = visual.Window(fullscr=True, color="black", units="pix", monitor='testMonitor', allowGUI=True)
except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()

# Function to display instructions
def show_instructions(text):
    instructions = visual.TextStim(win, text=text, color="white", height=40)
    instructions.draw()
    win.flip()
    while True:
        keys = event.waitKeys(keyList=["space", "escape", "s"])
        if "escape" in keys:
            win.close()
            core.quit()
        elif "s" in keys:
            return 'skip'  # Skip current block
        elif "space" in keys:
            return 'continue'  # Proceed normally

# First block: Passive viewing of shapes and sounds
def block_one():
    instructions_text = (
        "Instructions: \n\n"
        "In this part of the experiment, you will see shapes on the screen paired with sounds. "
        "Your task is to pay close attention to the sound that corresponds to each shape."
        "There is no need to respond during this block.\n\n"
        "Press SPACEBAR to begin when you are ready."
    )

    if show_instructions(instructions_text) == 'skip':
        return 'skip'

    fixation = visual.TextStim(win, text="+", color="white", height=50)
    for img_file, audio_file in stimuli_pairs:
        keys = event.getKeys(keyList=["escape", "s"])
        if "escape" in keys:
            win.close()
            core.quit()
        if "s" in keys:
            return 'skip'  # Skip Block 1 immediately

        fixation.draw()
        win.flip()
        core.wait(3)

        image_path = os.path.join(image_dir, img_file)
        audio_path = os.path.join(audio_dir, audio_file)

        if os.path.exists(image_path) and os.path.exists(audio_path):
            img_stim = visual.ImageStim(win, image=image_path)
            try:
                sound_stim = sound.Sound(audio_path, secs=1.0, stereo=True, hamming=True)
                img_stim.draw()
                win.flip()
                sound_stim.play()
                core.wait(1.0)
                sound_stim.stop()
            except Exception as e:
                print(f"Error playing sound {audio_file}: {str(e)}")
                img_stim.draw()
                win.flip()
                core.wait(1.0)  # Default duration if sound fails

    return 'done'

# Second block: Matching task
def block_two():
    instructions_text = (
        "Instructions: \n\n"
        "In this part of the experiment, you will see a shape and hear two tones played one after the other. "
        "Your task is to match the shape with the correct sound.\n\n"
        "If the first tone matches the shape, press '1'. If the second tone matches the shape, press '2'.\n\n"
        "Please respond as quickly as possible.\n\n"
        "Press SPACEBAR to continue."
    )

    if show_instructions(instructions_text) == 'skip':
        return

    results = []
    for img_file, audio_file in stimuli_pairs:
        keys = event.getKeys(keyList=["escape", "s"])
        if "escape" in keys:
            win.close()
            core.quit()
        if "s" in keys:
            return  # Skip Block 2 immediately

        # Ensure correct tone is used
        correct_tone = audio_file

        # Pick a random incorrect tone (ensuring it's not the correct one)
        available_tones = [f"tone_{i:02d}.wav" for i in range(1, 11) if f"tone_{i:02d}.wav" != correct_tone]
        incorrect_tone = random.choice(available_tones)

        # Randomly order the two tones
        random_tones = [correct_tone, incorrect_tone]
        random.shuffle(random_tones)

        image_path = os.path.join(image_dir, img_file)
        img_stim = visual.ImageStim(win, image=image_path)
        img_stim.draw()
        win.flip()

        # Play first tone
        tone1 = sound.Sound(os.path.join(audio_dir, random_tones[0]), secs=2.0)
        tone1.play()
        core.wait(2)

        # Play second tone
        tone2 = sound.Sound(os.path.join(audio_dir, random_tones[1]), secs=2.0)
        tone2.play()
        core.wait(2)

        # Display response prompt
        response_prompt = visual.TextStim(
            win, 
            text="Press 1 if the first tone matches.\nPress 2 if the second tone matches.", 
            color="white", 
            height=30
        )
        response_prompt.draw()
        win.flip()

        start_time = core.getTime()
        keys = event.waitKeys(keyList=["1", "2", "s", "escape"])

        if "escape" in keys:
            win.close()
            core.quit()
        if "s" in keys:
            return  # Skip remaining trials and end the experiment

        response = keys[0] if keys else None
        rt = core.getTime() - start_time if response else None

        # Store the trial data
        results.append({
            "shape": img_file,
            "tone1": random_tones[0],
            "tone2": random_tones[1],
            "response": response,
            "reaction_time": rt,
            "correct_tone": correct_tone,
            "incorrect_tone": incorrect_tone,
            "correct_answer": "1" if random_tones[0] == correct_tone else "2"
        })

    # Save results to Excel
    results_df = pd.DataFrame(results)
    results_df.to_excel("participant_responses.xlsx", index=False)

# Run experiment in sequence
if block_one() != 'skip':
    show_instructions("Second block. Press SPACE to continue.")
    block_two()

# Cleanup
win.close()
core.quit()
