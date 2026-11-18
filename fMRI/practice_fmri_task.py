#!/usr/bin/env python3
"""
practice_task.py
================

Pre-scan practice for the crossmodal MATCH / NO-MATCH task (crossmodal_fmri_task.py).
Run it outside the scanner, before the scan session.

What the participant does
    Same trial structure, timing, buttons and feedback as the scanner task, but with
    three PRACTICE stimuli that never appear in the real task:
        shapes: grey circle, square, triangle
        sounds: pure tones (330, 523, 784 Hz)
    Which tone belongs to which shape is randomised per participant, so the practice
    hints at no rule that could carry over to the real stimuli.

    Each block: 18 trials (each shape 6 times: 3 matched, 3 with a wrong tone), ~2.5 min.
    After each block the experimenter can repeat the block (R) or finish (SPACE).

Buttons (taken from crossmodal_fmri_task.py, so the two scripts always agree)
    7 = right index finger = MATCH
    4 = left index finger  = NO MATCH
    (keypad 4 / 7 also work, for practising on a laptop keyboard)

Live terminal output: every trial's pairing, correct answer, response, RT, and result.
Log: ./participant_data_fmri/sub-<ID>/sub-<ID>_practice.csv (one row per trial, appended).

Usage
    python practice_task.py
    Keep it in the same folder as the scanner task script. That script can have any name
    (e.g. fmri_task.py or crossmodal_fmri_task.py); this script finds it automatically.
"""

import os
import csv
import random
import datetime

import numpy as np

import sys
import importlib.util
import importlib.machinery

# --- Find the scanner task script (shared keys, timing, feedback images, data folder) ----
# Looks in THIS script's folder, whatever folder Python was started from, and accepts any
# file name: first the names listed here, then any .py file containing the task class.
TASK_SCRIPT_NAMES = ["fmri_task.py", "crossmodal_fmri_task.py"]


def _looks_like_task(path):
    try:
        if not os.path.isfile(path) or os.path.getsize(path) > 2_000_000:
            return False
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return "class CrossmodalFMRITask" in fh.read()
    except OSError:
        return False


def _load_task_module():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)  # relative paths (stimuli, feedback images, data folder) resolve here
    me = os.path.abspath(__file__)
    candidates = [os.path.join(here, n) for n in TASK_SCRIPT_NAMES]
    # any .py file, or a file saved WITHOUT the .py extension, in this folder
    entries = sorted(os.listdir(here))
    candidates += [os.path.join(here, f) for f in entries
                   if f.endswith(".py") or "." not in f]
    # ... and one folder level down (e.g. a folder called fmri_task/ holding the script)
    for d in entries:
        sub = os.path.join(here, d)
        if os.path.isdir(sub) and not d.startswith((".", "__")) and not d.startswith(
                ("participant_data", "generated_", "analysis_output")):
            try:
                candidates += [os.path.join(sub, f) for f in sorted(os.listdir(sub))
                               if f.endswith(".py") or "." not in f]
            except OSError:
                pass
    for path in candidates:
        if os.path.abspath(path) == me or not _looks_like_task(path):
            continue
        loader = importlib.machinery.SourceFileLoader("fmri_task_shared", path)
        spec = importlib.util.spec_from_loader("fmri_task_shared", loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules["fmri_task_shared"] = module
        loader.exec_module(module)
        print("Using task settings from %s" % os.path.relpath(path, here))
        if not path.endswith(".py"):
            print("  (note: this file has no .py extension - consider renaming it to %s.py)"
                  % os.path.basename(path))
        return module
    sys.exit("Could not find the scanner task script in %s (or its subfolders).\n"
             "Put this script in the same folder as the task script (e.g. fmri_task.py).\n"
             "Python files found there: %s"
             % (here, ", ".join(f for f in entries if f.endswith(".py")) or "none"))


T = _load_task_module()

# --- Practice settings ---------------------------------------------------------
PRACTICE_TONES_HZ = [330, 523, 784]
TRIALS_PER_SHAPE = 6          # half matched, half with one of the other two tones
SHAPE_COLOR = "#e0e0e0"
GOOD_ACCURACY = 0.75          # only used for the experimenter's terminal message

# Keypad aliases, so practice also works on a laptop keyboard
KEY_ALIASES = {"num_4": T.KEY_LEFT, "num_7": T.KEY_RIGHT}


def make_block(rng):
    """18 trials: (shape, tone, is_match). No shape twice in a row."""
    n = len(PRACTICE_TONES_HZ)
    trials = []
    for s in range(n):
        others = [k for k in range(n) if k != s]
        n_match = TRIALS_PER_SHAPE // 2
        trials += [(s, s, 1)] * n_match
        wrong = (others * TRIALS_PER_SHAPE)[: TRIALS_PER_SHAPE - n_match]
        trials += [(s, w, 0) for w in wrong]
    for _ in range(10000):
        rng.shuffle(trials)
        if all(a[0] != b[0] for a, b in zip(trials, trials[1:])):
            return trials
    return trials


class Practice:
    FIELDS = ["participant", "block", "trial", "shape", "tone_hz", "is_match",
              "correct_response", "response_status", "response_key", "response", "rt",
              "accuracy", "missed", "late_response_key", "late_response", "late_rt",
              "late_accuracy", "n_presses", "all_presses", "iti", "isi", "wall_time"]

    def __init__(self, info):
        self.info = info
        self.pid = info["participant"]
        folder = os.path.join(T.DATA_DIR, "sub-%s" % self.pid)
        os.makedirs(folder, exist_ok=True)
        self.log_path = os.path.join(folder, "sub-%s_practice.csv" % self.pid)

        b = T.button_map()
        self.match_key, self.nomatch_key = b["match_key"], b["nomatch_key"]
        self.match_finger, self.nomatch_finger = b["match_finger"], b["nomatch_finger"]
        self.resp_keys = [T.KEY_LEFT, T.KEY_RIGHT] + list(KEY_ALIASES)

        visual, sound, keyboard = T.visual, T.sound, T.keyboard
        self.win = visual.Window(screen=T.SCREEN_INDEX, fullscr=info["fullscreen"],
                                 color=T.BG_COLOR, units="height", allowGUI=False)
        self.win.mouseVisible = False
        self.kb = keyboard.Keyboard()

        self.fixation = visual.TextStim(self.win, text="+", color="white", height=0.07)
        self.msg = visual.TextStim(self.win, text="", color="white", height=0.035, wrapWidth=1.2)
        self.shapes = [
            visual.Circle(self.win, radius=0.12, fillColor=SHAPE_COLOR, lineColor=None),
            visual.Rect(self.win, width=0.22, height=0.22, fillColor=SHAPE_COLOR, lineColor=None),
            visual.Polygon(self.win, edges=3, radius=0.15, fillColor=SHAPE_COLOR, lineColor=None),
        ]
        self.shape_names = ["circle", "square", "triangle"]

        # Random tone-shape mapping per participant (seeded, so it is the same on a re-run)
        rng = random.Random(T.seed_from_id(self.pid) + 1)
        self.tones_hz = PRACTICE_TONES_HZ[:]
        rng.shuffle(self.tones_hz)
        self.tone_dur = T.STIM_DUR

        self.fb_correct = self._feedback(T.FEEDBACK_CORRECT_IMG, "Correct", "#2ecc40")
        self.fb_incorrect = self._feedback(T.FEEDBACK_INCORRECT_IMG, "Incorrect", "#ff4136")
        self.fb_missed = visual.TextStim(self.win, text="Too slow!", color="yellow", height=0.06)

    def _feedback(self, img, text, color):
        if os.path.exists(img):
            return T.visual.ImageStim(self.win, image=img, size=T.FEEDBACK_SIZE)
        return T.visual.TextStim(self.win, text=text, color=color, height=0.06)

    def _tone(self, idx):
        # A fresh Sound per trial: replaying one short generated tone is unreliable.
        return T.sound.Sound(value=self.tones_hz[idx], secs=self.tone_dur, stereo=True,
                             hamming=True, volume=T.SOUND_VOLUME)

    def quit(self):
        self.win.close()
        T.core.quit()

    def show(self, text, keys):
        self.msg.text = text
        self.kb.clearEvents()
        while True:
            self.msg.draw()
            self.win.flip()
            for k in self.kb.getKeys(keyList=keys + [T.QUIT_KEY], waitRelease=False):
                if k.name == T.QUIT_KEY:
                    self.quit()
                return k.name

    def wait_drawing(self, stim, secs):
        clock = T.core.Clock()
        while clock.getTime() < secs:
            stim.draw()
            self.win.flip()
            if self.kb.getKeys(keyList=[T.QUIT_KEY], waitRelease=False):
                self.quit()

    def run_block(self, block):
        """
        Same response rules as the scanner task: the first press within RESPONSE_WINDOW
        (3 s) of stimulus onset is the answer; a first press after that but before feedback
        gets "Too slow!" and is still saved with its RT; every press is saved.
        """
        rng = random.Random()
        trials = make_block(rng)
        jrng = np.random.default_rng()
        itis = T.sample_jitters(len(trials), T.ITI_MEAN, T.ITI_MIN, T.ITI_MAX, jrng)
        isis = T.sample_jitters(len(trials), T.ISI_MEAN, T.ISI_MIN, T.ISI_MAX, jrng)
        keys = self.resp_keys + [T.QUIT_KEY]

        print("\n--- PRACTICE block %d: %d trials ---" % (block, len(trials)))
        print("    mapping: " + ", ".join("%s = %d Hz" % (self.shape_names[i], self.tones_hz[i])
                                           for i in range(len(self.shape_names))))
        n_correct = n_missed = n_late = 0
        self.wait_drawing(self.fixation, itis[0])  # first ITI; later ITIs follow each trial
        for t, (shp, tone_idx, is_match) in enumerate(trials, 1):
            isi = isis[t - 1]
            next_iti = itis[t] if t < len(trials) else 1.0
            fb_on = T.STIM_DUR + isi
            trial_end = fb_on + T.FEEDBACK_DUR + next_iti

            tone = self._tone(tone_idx)
            self.kb.clearEvents()
            self.shapes[shp].draw()
            self.win.callOnFlip(self.kb.clock.reset)  # RT clock: 0 = stimulus onset
            self.win.callOnFlip(tone.play)
            self.win.flip()

            resp = rt = late = late_rt = None
            presses, fb, tone_stopped = [], None, False
            while True:
                now = self.kb.clock.getTime()
                if now >= trial_end:
                    break
                if now >= T.STIM_DUR and not tone_stopped:
                    tone.stop()
                    tone_stopped = True
                if now < T.STIM_DUR:
                    self.shapes[shp].draw()
                elif now < fb_on:
                    self.fixation.draw()
                elif now < fb_on + T.FEEDBACK_DUR:
                    if fb is None:  # decide feedback once, at feedback onset
                        if resp is None:
                            fb = self.fb_missed
                        else:
                            fb = (self.fb_correct if (resp == self.match_key) == bool(is_match)
                                  else self.fb_incorrect)
                    fb.draw()
                else:
                    self.fixation.draw()
                self.win.flip()
                for k in self.kb.getKeys(keyList=keys, waitRelease=False):
                    if k.name == T.QUIT_KEY:
                        self.quit()
                    name = KEY_ALIASES.get(k.name, k.name)
                    presses.append((k.rt, name))
                    if resp is None and k.rt <= T.RESPONSE_WINDOW:
                        resp, rt = name, k.rt
                    elif resp is None and late is None and k.rt < fb_on:
                        late, late_rt = name, k.rt

            if resp is None:
                acc = ""
                n_missed += 1
                if late is not None:
                    n_late += 1
                    result = "TOO SLOW (pressed at %.2f s)" % late_rt
                else:
                    result = "TOO SLOW (no press)"
            else:
                acc = int((resp == self.match_key) == bool(is_match))
                n_correct += acc
                result = "correct" if acc else "WRONG"

            answer = "match" if is_match else "no match"
            given = "-" if resp is None else ("match" if resp == self.match_key else "no match")
            print("  %2d  %-8s + %3d Hz   answer %-8s  response %-8s  RT %-5s  %s"
                  % (t, self.shape_names[shp], self.tones_hz[tone_idx], answer, given,
                     "-" if rt is None else "%.2f" % rt, result))
            self._log(block, t, shp, tone_idx, is_match, resp, rt, acc, late, late_rt,
                      presses, itis[t - 1], isi)

        answered = len(trials) - n_missed
        acc_all = n_correct / len(trials)
        print("Block %d: %d / %d correct (%.0f%%), %d too slow (%d of them pressed late)."
              % (block, n_correct, len(trials), 100 * acc_all, n_missed, n_late))
        if acc_all < GOOD_ACCURACY or n_missed > 2:
            print("  -> Consider repeating: check they know which finger means MATCH, "
                  "and that they answer within 3 seconds.")
        return n_correct, len(trials), answered

    def _log(self, block, t, shp, tone_idx, is_match, resp, rt, acc, late, late_rt,
             presses, iti, isi):
        def label(k):
            return "" if k is None else ("match" if k == self.match_key else "nomatch")
        new = not os.path.exists(self.log_path)
        with open(self.log_path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.FIELDS, lineterminator="\n")
            if new:
                w.writeheader()
            w.writerow(dict(
                participant=self.pid, block=block, trial=t,
                shape=self.shape_names[shp], tone_hz=self.tones_hz[tone_idx], is_match=is_match,
                correct_response="match" if is_match else "nomatch",
                response_status="on_time" if resp else ("late" if late else "none"),
                response_key=resp or "", response=label(resp),
                rt="" if rt is None else round(rt, 4), accuracy=acc, missed=int(resp is None),
                late_response_key=late or "", late_response=label(late),
                late_rt="" if late_rt is None else round(late_rt, 4),
                late_accuracy="" if late is None else int((late == self.match_key) == bool(is_match)),
                n_presses=len(presses),
                all_presses=";".join("%s@%.4f" % (k, tt) for tt, k in presses),
                iti=round(float(iti), 3), isi=round(float(isi), 3),
                wall_time=datetime.datetime.now().isoformat(timespec="seconds")))

    def run(self):
        any_key = self.resp_keys + ["space"]
        self.show("PRACTICE\n\n"
                  "You will see a SHAPE and hear a SOUND at the same time.\n\n"
                  "Some shapes and sounds are a MATCH and some DO NOT MATCH.\n\n"
                  "If you think they MATCH, press with your %s.\n"
                  "If you think they do NOT match, press with your %s.\n\n"
                  "Try to answer as FAST AS POSSIBLE. \n\n "
                  "After a short pause you will see "
                  "whether you were right or wrong. Please try to remember the MATCHED pairings.\n\n"
                  "Press either button to continue.\n\n" % (self.match_finger, self.nomatch_finger),
                  any_key)
        self.show("The task is about to begin.\n\n"
                  "MATCH = %s\nNO MATCH = %s\n\nPress either button to begin."
                  % (self.match_finger, self.nomatch_finger), any_key)
        block = 1
        while True:
            n_correct, n_trials, _ = self.run_block(block)
            print("Experimenter: SPACE = finish practice | R = repeat block")
            choice = self.show("You got %d out of %d correct.\n\n"
                               "Please wait for the experimenter." % (n_correct, n_trials),
                               ["space", "r"])
            if choice == "space":
                break
            block += 1
            self.show("Let's practise once more.\n\nMATCH = %s\nNO MATCH = %s\n\n"
                      "Press either button to begin." % (self.match_finger, self.nomatch_finger),
                      any_key)
        self.show("Practice finished. Well done!\n\nIn the scanner you will see NEW shapes "
                  "and sounds, but the task and the buttons are the same.", ["space"])
        self.quit()


def main():
    T.import_psychopy()
    info = {"participant": "", "fullscreen": True}
    dlg = T.gui.DlgFromDict(info, title="Crossmodal task - PRACTICE",
                            order=["participant", "fullscreen"])
    if not dlg.OK:
        T.core.quit()
    info["participant"] = T.sanitize_id(info["participant"])
    Practice(info).run()


if __name__ == "__main__":
    main()