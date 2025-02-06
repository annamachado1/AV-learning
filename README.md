# 🎵🔶 Assessing Audiovisual Learning Plasticity with Novel Stimuli

This experiment investigates **audiovisual learning plasticity** using novel stimuli—unfamiliar shapes paired with distinct tones. Participants are exposed to **paired stimuli** and later tested on their ability to associate shapes with sounds.

## ✨ Significance Statement
This aim will identify **developmental differences** in both **semantic binding thresholds** and **cross-modal learning abilities**, offering insights into the mechanisms underlying **semantic integration** and **plasticity**. By **fine-tuning multimodal models with shared attention layers**, we will gain a **predictive framework** for understanding **when and how audiovisual pairings are formed and maintained across developmental stages**.

---

## 🧪 Experiment Design

The experiment consists of **X blocks**:

### 1️⃣ Passive Viewing Block
- Participants **see** a shape and **hear** its corresponding tone.
- No response is required—participants simply observe and listen.

### 2️⃣ Forced-Choice Matching Task
- Participants are shown a shape and hear **two tones** (one correct, one incorrect).
- They must choose which tone **matches** the shape:
  - **Press `1`** if the **first** tone matches.
  - **Press `2`** if the **second** tone matches.
- Responses and reaction times are **automatically recorded** in an Excel file.

Participants can **press `S` to skip a block** or **press `ESC` to exit** at any time.

---

## 🖥️ Installation & Setup

### 1️⃣ Clone the Repository

git clone https://github.com/yourusername/AV-learning.git

cd AV-learning

## 2️⃣ Set Up the Conda Environment

conda env create -f environment.yml

conda activate NovelStimuli

## 3️⃣ Run the Experiment

python experiment.py

---

## 🔧 Dependencies
The experiment runs in **Python 3.9** and relies on the following libraries:

PsychoPy – For stimulus presentation

NumPy, SciPy, Pandas – Data handling

Matplotlib, PIL – Image processing

Sounddevice, VLC, Pygame – Audio playback

To ensure PsychoPy works correctly, pyglet is pinned to version 1.5.27, and pyo is removed to avoid conflicts.
