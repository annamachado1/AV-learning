import os
import random
random.seed(42)  # Added fixed seed for consistent random pairings
import pandas as pd
import csv
import time
from psychopy import visual, core, event, sound, prefs, gui
import numpy as np
import traceback
import json  # Added for JSON serialization

# Configure sound preferences
prefs.hardware['audioLib'] = ['sounddevice', 'pygame']
prefs.general['audioDevice'] = ['default']

# Set the path where images and sounds are stored
image_dir = "./generated_shapes"
audio_dir = "./generated_sounds"

# NEW: Set paths for the testsets for block 2
test_image_dir = "./generated_shapes_testset"
test_audio_dir = "./generated_sounds_testset"

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

# Generate ordered list of paired stimuli (each appearing 6 times)
stimuli_pairs = [(f"shape_{i:02d}.png", f"sound_{i:02d}.wav") for i in range(4, 10)]  # Limit to 6 pairs (4 to 9)

for shp, snd in stimuli_pairs:
    n_shape = int(shp.split('_')[1].split('.')[0])
    n_sound = int(snd.split('_')[1].split('.')[0])
    assert n_shape == n_sound, f"Mapping error: {shp} vs {snd}"

all_trials = stimuli_pairs * 10  # Each pair appears 10 times
random.shuffle(all_trials)  # Completely randomize order

# Define utility functions first
def get_participant_id():
    """Prompt for participant ID and handle existing data."""
    info = {"Participant ID": ""}
    dlg = gui.DlgFromDict(info, title="Participant Info")
    if not dlg.OK:
        core.quit()
    participant_id = info["Participant ID"]

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

def load_partial_results(participant_id):
    """Load partial results if they exist for the given participant ID."""
    global participant_data
    participant_folder = os.path.join("./participant_data", participant_id)
    try:
        # Load free pairings
        free_pairings_file = os.path.join(participant_folder, f"{participant_id}_free_pairings_partial.csv")
        if os.path.exists(free_pairings_file):
            free_pairings_df = pd.read_csv(free_pairings_file)
            participant_data["free_pairings"] = free_pairings_df.to_dict("records")
            print(f"Loaded free pairings from {free_pairings_file}")

        # Load block 2 log
        block2_log_file = os.path.join(participant_folder, f"{participant_id}_block2_log_partial.csv")
        if os.path.exists(block2_log_file):
            block2_log_df = pd.read_csv(block2_log_file)
            participant_data["block 2 log"] = block2_log_df.to_dict("records")
            participant_data["block 2 correct"] = block2_log_df["Correct Answer"].eq(block2_log_df["Response"]).sum()
            participant_data["block 2 incorrect"] = len(block2_log_df) - participant_data["block 2 correct"]
            print(f"Loaded block 2 log from {block2_log_file}")

        print("Partial results loaded successfully.")
    except Exception as e:
        print(f"Error loading partial results: {e}")
        traceback.print_exc()

# ...existing code...

def save_block_data_to_excel():
    """Save block data to individual .xlsx files."""
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    if not os.path.exists(participant_folder):
        os.makedirs(participant_folder)

    # Save free pairings (Block 0)
    if "free_pairings" in participant_data:
        free_pairings_df = pd.DataFrame(participant_data["free_pairings"])
        free_pairings_file = os.path.join(participant_folder, "free_pairings.xlsx")
        free_pairings_df.to_excel(free_pairings_file, index=False)
        print(f"Block 0 data saved to {free_pairings_file}")

    # Save free pairings testset (Block 0 Testset)
    if "free_pairings_testset" in participant_data:
        free_pairings_testset_df = pd.DataFrame(participant_data["free_pairings_testset"])
        free_pairings_testset_file = os.path.join(participant_folder, "free_pairings_testset.xlsx")
        free_pairings_testset_df.to_excel(free_pairings_testset_file, index=False)
        print(f"Block 0 Testset data saved to {free_pairings_testset_file}")

    # Save Block 1 log
    if "block1_log" in participant_data:
        block1_log_df = pd.DataFrame(participant_data["block1_log"])
        block1_log_file = os.path.join(participant_folder, "block1_log.xlsx")
        block1_log_df.to_excel(block1_log_file, index=False)
        print(f"Block 1 data saved to {block1_log_file}")

    # Save Block 2 log
    if "block 2 log" in participant_data:
        block2_log_df = pd.DataFrame(participant_data["block 2 log"])
        block2_log_file = os.path.join(participant_folder, "block2_log.xlsx")
        block2_log_df.to_excel(block2_log_file, index=False)
        print(f"Block 2 data saved to {block2_log_file}")

def save_consolidated_data():
    """Save consolidated data to a single .xlsx file with multiple sheets."""
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    if not os.path.exists(participant_folder):
        os.makedirs(participant_folder)

    consolidated_file = os.path.join(participant_folder, "consolidated_data.xlsx")
    with pd.ExcelWriter(consolidated_file, engine="openpyxl") as writer:
        # Save free pairings (Block 0)
        if "free_pairings" in participant_data:
            free_pairings_df = pd.DataFrame(participant_data["free_pairings"])
            free_pairings_df.to_excel(writer, sheet_name="Block 0", index=False)

        # Save free pairings testset (Block 0 Testset)
        if "free_pairings_testset" in participant_data:
            free_pairings_testset_df = pd.DataFrame(participant_data["free_pairings_testset"])
            free_pairings_testset_df.to_excel(writer, sheet_name="Block 0 Testset", index=False)

        # Save Block 1 log
        if "block1_log" in participant_data:
            block1_log_df = pd.DataFrame(participant_data["block1_log"])
            block1_log_df.to_excel(writer, sheet_name="Block 1", index=False)

        # Save Block 2 log
        if "block 2 log" in participant_data:
            block2_log_df = pd.DataFrame(participant_data["block 2 log"])
            block2_log_df.to_excel(writer, sheet_name="Block 2", index=False)

    print(f"Consolidated data saved to {consolidated_file}")

# Update the save_results function to call the new save functions
def save_results():
    """Save final results after the experiment is completed."""
    try:
        save_block_data_to_excel()
        save_consolidated_data()
    except Exception as e:
        print(f"Error saving results: {e}")
        traceback.print_exc()

# ...existing code...

def block_zero_pairing():
    """First free pairing block with shapes and tones from learning blocks."""
    global participant_data
    participant_data["free_pairings"] = []

    # Load shapes and tones (limit to shapes 4 to 9 and tones 4 to 9)
    shape_files = sorted([f for f in os.listdir(image_dir) if f.startswith("shape_") and f.endswith(".png")])[3:9]
    tone_files = sorted([f for f in os.listdir(audio_dir) if f.startswith("sound_") and f.endswith(".wav")])[3:9]

    # ...existing code for pairing logic...

    print("First free pairing block completed.")
    save_block_data_to_excel()

def block_zero_testset_pairing():
    """Second free pairing block with shapes and tones from testset (Block 2)."""
    global participant_data
    participant_data["free_pairings_testset"] = []

    # Load shapes and tones from testset (limit to shapes 4 to 9 and tones 4 to 9)
    shape_files = sorted([f for f in os.listdir(test_image_dir) if f.startswith("shape_") and f.endswith(".png")])[3:9]
    tone_files = sorted([f for f in os.listdir(test_audio_dir) if f.startswith("sound_") and f.endswith(".wav")])[3:9]

    # ...existing code for pairing logic...

    print("Second free pairing block (testset) completed.")
    save_block_data_to_excel()

# Update the main experiment flow to include the second free pairing block
# ...existing code...
if resume_point == "start":
    block_zero_pairing()
    participant_data["block_completed"] = True  # Mark block as completed
    choice = main_menu()
    if choice == "passive":
        result = block_one_passive()
        participant_data["block_completed"] = True  # Mark block as completed
    elif choice == "active":
        result = block_one_active()
        participant_data["block_completed"] = True  # Mark block as completed
    else:
        result = None
    block_zero_testset_pairing()  # Add second free pairing block here
elif resume_point == "block1":
    choice = main_menu()
    if choice == "passive":
        result = block_one_passive()
        participant_data["block_completed"] = True  # Mark block as completed
    elif choice == "active":
        result = block_one_active()
        participant_data["block_completed"] = True  # Mark block as completed
    else:
        result = None
    block_zero_testset_pairing()  # Add second free pairing block here
elif resume_point == "block2":
    show_instructions("Second Block: Matching Task.\n\nPress SPACEBAR to continue.", ["space"])
    block_two()
    participant_data["block_completed"] = True  # Mark block as completed
    result = "done"  # Ensure result is set to "done" for proper flow
# ...existing code...

def block_one_passive():
    # ...existing initialization code...
    total_trials = len(all_trials)  # total number of trials in passive block
    for idx, trial in enumerate(all_trials):
        # ...existing code processing each trial...
        
        # Added progression bar similar to active block
        progress = (idx + 1) / total_trials * 100
        print(f"Passive Block Progress: {progress:.1f}% complete", end='\r')
        
        # ...existing code...
    # ...existing code...
