import os
import random
import csv
import time
from psychopy import visual, core, event, sound, prefs, gui  # new import for participant input

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
all_trials = stimuli_pairs * 10  # changed multiplier from 5 to 10
random.shuffle(all_trials)

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
    show_instructions("Second Block: Matching Task.\n\nPress SPACEBAR to continue.", ["space"])
    block_two()
    save_results()
    show_instructions("Thank you for participating!\n\nPress SPACEBAR to exit.", ["space"])

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
