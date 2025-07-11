print("Script started")

import os
import numpy as np
from scipy.io.wavfile import write as write_wav
from PIL import Image, ImageDraw
from psychopy import visual, core

# Set up directories
os.makedirs("practice_sounds", exist_ok=True)
os.makedirs("practice_shapes", exist_ok=True)

# Generate simple tones for practice audio stimuli
def generate_tone(frequency, duration=0.5, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = 0.5 * np.sin(2 * np.pi * frequency * t)
    tone = np.int16(tone * 32767)
    return tone

# Create three audio files: target, associated, distractor
def create_practice_sounds():
    freqs = [440, 550, 660]  # Hz: A4, C#5, E5
    labels = ["target", "associated", "distractor"]
    for freq, label in zip(freqs, labels):
        sound = generate_tone(freq)
        write_wav(f"practice_sounds/{label}.wav", 44100, sound)

# Create three PNG images: target, associated, distractor (colored circles)
def create_practice_shapes():
    output_dir = "practice_shapes"
    os.makedirs(output_dir, exist_ok=True)

    win = visual.Window(size=(300, 300), color='white', units='pix', winType='pyglet')

    target = visual.Circle(win, radius=50.0, edges=128, fillColor='black', lineColor='black')
    associated = visual.Rect(win, width=100, height=100, fillColor='black', lineColor='black')

    vertices = [[-50, -50], [0, 50], [50, -50]]  # Plain Python list

    distractor = visual.ShapeStim(win, fillColor='black', lineColor='black', closeShape=True)
    distractor.vertices = vertices  # assign after creation

    shapes = {
        "target": target,
        "associated": associated,
        "distractor": distractor
    }

    for name, stim in shapes.items():
        stim.draw()
        win.flip()
        core.wait(0.2)

        file_path = os.path.join(output_dir, f"{name}.png")
        win.getMovieFrame()
        win.saveMovieFrames(file_path)
        win.flip()
        core.wait(0.1)

    win.close()
    print("Shapes saved to", output_dir)

create_practice_sounds()
create_practice_shapes()