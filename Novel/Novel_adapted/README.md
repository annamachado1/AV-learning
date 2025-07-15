# **Assessing Audiovisual Learning Plasticity with Novel Stimuli**

This repository contains a **PsychoPy-based experiment** designed to investigate **audiovisual learning plasticity** using **arbitrary pairings of novel auditory and visual stimuli**. Participants learn shape–sound pairings and are tested on their ability to recall and generalize these associations.

---

## 🧠 **Background**

Humans frequently encounter situations where auditory and visual information must be integrated. This experiment explores how individuals learn arbitrary audiovisual associations and how unimodal reinforcement affects cross-modal learning. By evaluating performance across **crossmodal**, **unimodal**, and **test** phases, the study aims to build a predictive framework for **how new multisensory mappings are acquired and generalized**.

---

## **Experimental Design**

The experiment is divided into **three blocks**:

### ✅ **Block 1: Crossmodal Learning**
- A **shape** is shown, followed by **two sounds** (one correct, one distractor).
- Task: Press `1` if the **first** sound matches the shape, `2` if the **second** matches.
- **Feedback provided** after each trial.

### ✅ **Block 2: Unimodal Learning**
- Two trial types:
  - **Visual–Visual:** Shape followed by two shapes (one associated, one distractor).
  - **Auditory–Auditory:** Sound followed by two sounds.
- Same forced-choice response structure as Block 1.
- **Feedback provided**.

### ✅ **Block 3: Testing**
- Mixed trials:
  - Crossmodal: Shape → two sounds
  - Visual-only: Shape → two shapes
  - Auditory-only: Sound → two sounds
- **No feedback provided**.

Participants complete practice trials before starting the main blocks. Trials are randomized, and **reaction times and accuracy are recorded**.

---

## **Stimuli**

### 👁 **Visual Stimuli**
- **Irregular polygons** (training set) for crossmodal trials.
- **Smooth blob-like shapes** for unimodal trials.
- Features:
  - Generated procedurally using parametric control for concavity, jaggedness, and lobe variations.
  - Black on white background.
  - Saved as `.png` with metadata (`shape_metadata.xlsx`).

### 👂 **Auditory Stimuli**
- **Harmonic tones** with:
  - Controlled **number of harmonics**, **spectral tilt**, and **F0**.
  - ADSR envelope for natural onset/offset.
- Variants for unimodal trials include controlled **formant filtering** for timbre variation.
- Saved as `.wav` with metadata logs (`tone_feature_log.csv`).

---

## 🔄 **Pairing Logic**
- **6 shape–tone pairs** for crossmodal learning.
- **New shape and sound pairings** for unimodal reinforcement.
- Consistent pairings across training and test phases.

---

## 💾 **Data Storage**
- Participant-specific folder created in `./participant_data/`.
- **Excel files** saved per block:
  - `block1_crossmodal_log.xlsx`
  - `block2_unimodal_log.xlsx`
  - `block3_test_log.xlsx`
- Includes **stimulus IDs, responses, reaction times, and accuracy**.

---

## **Installation & Setup**

### ✅ **Requirements**
- Python 3.8+
- [PsychoPy](https://www.psychopy.org/) (2023.2+)
- Dependencies:
  ```bash
  pip install psychopy numpy pandas
