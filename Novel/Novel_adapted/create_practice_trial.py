from psychopy import prefs
prefs.hardware['audioLib'] = ['pygame']  # or try 'pyo', or ['pygame', 'pyo']

from psychopy import visual, core, event, sound
import os
import random

FIXATION_DURATION = 0.5
STIMULUS_DURATION = 1.0

def load_stimuli():
    shape_dir = "practice_shapes"
    sound_dir = "practice_sounds"

    # Load visual
    visual_target = os.path.join(shape_dir, "target.png")
    visual_associated = os.path.join(shape_dir, "associated.png")
    visual_distractor = os.path.join(shape_dir, "distractor.png")

    # Load audio
    audio_target = sound.Sound(os.path.join(sound_dir, "target.wav"))
    audio_associated = sound.Sound(os.path.join(sound_dir, "associated.wav"))
    audio_distractor = sound.Sound(os.path.join(sound_dir, "distractor.wav"))

    return {
        "visual": {
            "target": visual_target,
            "associated": visual_associated,
            "distractor": visual_distractor
        },
        "audio": {
            "target": audio_target,
            "associated": audio_associated,
            "distractor": audio_distractor
        }
    }

def show_fixation(win, red=False):
    fixation = visual.TextStim(win, text="+", color="red" if red else "lightgrey", height=0.1)
    fixation.draw()
    win.flip()
    core.wait(FIXATION_DURATION)

def show_feedback(win, correct):
    img_path = "green_tick.png" if correct else "red_cross.png"
    feedback = visual.ImageStim(win, image=img_path, size=(0.2, 0.2))
    feedback.draw()
    win.flip()
    core.wait(1.0)

def show_visual(win, img_path, with_border=False):
    img = visual.ImageStim(win, image=img_path, size=(0.3, 0.4), units="norm")

    if with_border:
        border_size = (img.size[0] + 0.02, img.size[1] + 0.02)
        x, y = img.pos
        border = visual.ShapeStim(
            win,
            vertices=[
                [x - border_size[0]/2, y - border_size[1]/2],
                [x - border_size[0]/2, y + border_size[1]/2],
                [x + border_size[0]/2, y + border_size[1]/2],
                [x + border_size[0]/2, y - border_size[1]/2]
            ],
            closeShape=True,
            lineColor='red',
            fillColor=None,
            lineWidth=5,
            units="norm"
        )
        border.draw()

    img.draw()
    win.flip()
    core.wait(STIMULUS_DURATION)

def prompt_response(win, text="Press 1 for FIRST, 2 for SECOND."):
    prompt = visual.TextStim(win, text=text, color="white", height=0.05)
    prompt.draw()
    win.flip()
    clock = core.Clock()
    while clock.getTime() < 5:
        keys = event.getKeys(keyList=["1", "2", "escape"])
        if "escape" in keys:
            win.close()
            core.quit()
        if keys:
            return keys[0]
        core.wait(0.01)
    return "NA"

def run_av_practice(win, stimuli):
    # Visual target with red border
    show_visual(win, stimuli["visual"]["target"], with_border=True)

    # Fixation
    show_fixation(win)

    # Audio distractor + target (shuffled)
    options = [stimuli["audio"]["target"], stimuli["audio"]["distractor"]]
    correct = "1" if options[0] == stimuli["audio"]["target"] else "2"
    random.shuffle(options)

    for i, snd in enumerate(options):
        show_fixation(win)
        snd.play()
        core.wait(STIMULUS_DURATION)

    response = prompt_response(win, "Press 1 if FIRST sound matches; 2 if SECOND.")
    show_feedback(win, response == correct)

def run_aa_practice(win, stimuli):
    # Visual round
    show_visual(win, stimuli["visual"]["target"], with_border=True)
    show_fixation(win)

    options = [stimuli["visual"]["associated"], stimuli["visual"]["distractor"]]
    correct_visual = "1" if options[0] == stimuli["visual"]["associated"] else "2"
    random.shuffle(options)

    for img_path in options:
        show_visual(win, img_path)
        show_fixation(win)

    response_visual = prompt_response(win, "Press 1 if FIRST shape matches; 2 if SECOND.")
    show_feedback(win, response_visual == correct_visual)

    # Audio round
    show_fixation(win, red=True)
    stimuli["audio"]["target"].play()
    core.wait(STIMULUS_DURATION)

    show_fixation(win)

    options = [stimuli["audio"]["associated"], stimuli["audio"]["distractor"]]
    correct_audio = "1" if options[0] == stimuli["audio"]["associated"] else "2"
    random.shuffle(options)

    for snd in options:
        show_fixation(win)
        snd.play()
        core.wait(STIMULUS_DURATION)

    response_audio = prompt_response(win, "Press 1 if FIRST sound matches; 2 if SECOND.")
    show_feedback(win, response_audio == correct_audio)

def show_instructions(win):
    txt = visual.TextStim(win,
        text=(
            "This is a practice trial.\n\n"
            "You will see or hear a target, then choose which option matches it.\n"
            "Use the 1 and 2 keys to respond.\n\n"
            "Press SPACEBAR to begin."
        ),
        color="white", height=0.06
    )
    txt.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--participant", type=int, required=True, help="Participant number")
    args = parser.parse_args()

    win = visual.Window(fullscr=False, color="black", units="norm")
    stimuli = load_stimuli()

    show_instructions(win)

    if args.participant % 2 == 0:
        run_av_practice(win, stimuli)
        run_aa_practice(win, stimuli)
    else:
        run_aa_practice(win, stimuli)
        run_av_practice(win, stimuli)

    end = visual.TextStim(win, text="Practice complete.\n\nPress SPACE to exit.", color="white", height=0.06)
    end.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

    win.close()
    core.quit()

if __name__ == "__main__":
    main()