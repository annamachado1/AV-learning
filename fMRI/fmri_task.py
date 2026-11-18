#!/usr/bin/env python3
"""
crossmodal_fmri_task.py
=======================

In-scanner MATCH / NO-MATCH crossmodal (shape-sound) learning task.
Adapted from the behavioural 2IFC pilot (feature_mapping_isi.py) for the VICTR
fMRI proposal "Neural Mechanisms of Crossmodal Feature Learning in Adolescence
and Adulthood" (Section D, Figure 3).

Trial structure (all times relative to the first scanner trigger of the run)
    ITI fixation  (jittered, mean 2.25 s, range 0.5-5.0 s)
    shape + sound (2.0 s, simultaneous onset)
    ISI fixation  (jittered, mean 2.5 s, range 1.5-4.5 s)
    Response window: 3.0 s from stimulus onset (into the ISI). Later first presses get
    "Too slow!" feedback; every press is still saved with its RT.
    feedback      (0.75 s: correct / incorrect / too slow)

Session design
    6 shape-sound pairings, 6 runs x 36 trials = 216 trials (~4.8 min per run).
    216 trials is the length used in the parameter-recovery simulation for the
    surprise-gated model (kappa recovered as well as at 300 trials).
    Each shape and each sound appears 36 times (6 per run).
    50 % matched trials (18 per run, 18 per pairing).
    Each sound has two foil shapes, A and B. In each phase one is COMMON and the other
    RARE (the "foil swap"; SWAP_FOILS_AFTER_RUN = 2):
        runs 1-2: per sound  6 match (50 %), 4 foil A (33 %, common), 2 foil B (17 %, rare)
        runs 3-6: per sound 12 match (50 %), 9 foil B (38 %, common), 3 foil A (12 %, rare)
        session : per sound 18 match, 7 foil A, 11 foil B
    The swap makes the surprise of each foil pairing change over the session instead
    of settling into a fixed value per pairing. Correct pairs never change.
    Every run keeps exactly 18 matches and 6 of every shape and every sound.
    Foil assignments are rotated (Latin structure) so every shape is foil A for exactly
    one sound and foil B for exactly one other sound.
    -> 18 possible shape-sound combinations (n = 18 in the surprise estimator).
    Two trial-wise surprise values are logged: the proposal's cumulative count
    (surprise_IS) and a forgetting version (surprise_IS_leaky, SURPRISE_DECAY).
    Jitter sequences are chosen per run by a design-efficiency simulation that
    minimises the correlation between stimulus- and feedback-locked regressors.

Outputs (./participant_data_fmri/sub-<ID>/)
    sub-<ID>_design.json        design, foil map, button mapping, seeds, timing scores
    sub-<ID>_schedule.csv       the full pre-generated 216-trial schedule (re-used on restart)
    sub-<ID>_trials.csv         one row per presented trial (appended live, crash-safe)
    sub-<ID>_runs.csv           one row per run attempt (status, accuracy, triggers, drops)
    events/sub-<ID>_task-crossmodal_run-XX[_attempt-N]_events.tsv   BIDS-style events
    sub-<ID>_soundcheck.csv     sound check: each beep, heard or missed, RT

The practice block is a separate script, practice_task.py, run before the scan.

Usage
    python crossmodal_fmri_task.py                  # run the experiment (dialog box)
    python crossmodal_fmri_task.py --design-only 01 # build + summarise a schedule, no PsychoPy

Keys (configure below for your button box / trigger box)
    trigger  : '~' (the ` / ~ key)
    response : '4' = left index = NO MATCH, '7' = right index = MATCH (same for everyone)
    escape   : abort current run (data so far are saved) -> experimenter menu
    Between runs: SPACE = next run, R = repeat the run just played, Q = quit
"""

import os
import sys
import re
import csv
import json
import math
import zlib
import random
import argparse
import datetime

import numpy as np

# =============================================================================
# CONFIGURATION
# =============================================================================

# --- Stimuli -----------------------------------------------------------------
# Which 6 of the 10 pilot pairings (shape_XX.png <-> sound_XX.wav) to use.
# PLACEHOLDER: evenly spread across the parametric continuum. Replace with the
# six pairings chosen for the fMRI study.
STIM_INDICES = [1, 3, 5, 6, 8, 10]
IMAGE_DIR = "./generated_shapes"
AUDIO_DIR = "./generated_sounds"
FEEDBACK_CORRECT_IMG = "green_tick.png"
FEEDBACK_INCORRECT_IMG = "red_cross.png"
DATA_DIR = "./participant_data_fmri"
TASK_LABEL = "crossmodal"

# --- Session structure (Proposal Section D) ----------------------------------
N_RUNS = 6
TRIALS_PER_RUN = 36
P_MATCH = 0.50            # proportion of matched trials (per sound and per run)
COMMON_FOIL_PROP = 0.36   # proportion of each sound's trials with its common foil
RARE_FOIL_PROP = 0.14     # proportion of each sound's trials with its rare foil
COUNTERBALANCE_FOILS = True   # randomise (per participant) which shape is whose foil
MATCH_FOIL_DIFFICULTY = True  # only draw arrangements with one fixed set of foil distances
                              # (identical for every participant; common & rare matched)
SWAP_FOILS_AFTER_RUN = 2      # common <-> rare foil roles swap after this run (None = never)
SURPRISE_DECAY = 0.98         # per-trial memory factor for the forgetting surprise estimator
COMMON_FOIL_OFFSET = 1        # cyclic offsets defining the Latin foil structure
RARE_FOIL_OFFSET = 4          # (1, 4) allows exact 5-per-run balance of every shape & sound

# Sequence constraints within a run
MAX_SAME_STATUS_RUN = 3   # max consecutive matched (or mismatched) trials
NO_REPEAT_SHAPE = True    # no identical shape on consecutive trials
NO_REPEAT_SOUND = True    # no identical sound on consecutive trials

# --- Timing (seconds) ----------------------------------------------------------
STIM_DUR = 2.0
FEEDBACK_DUR = 0.75
RESPONSE_WINDOW = 3.0      # from stimulus onset. A first press within it is the answer;
                           # a first press after it (before feedback) gets "Too slow!" but is
                           # still saved with its RT. Must close >= 0.1 s before earliest feedback.
ISI_MEAN, ISI_MIN, ISI_MAX = 2.50, 1.5, 4.5
ITI_MEAN, ITI_MIN, ITI_MAX = 2.25, 0.5, 5.0
JITTER_QUANTUM = 0.05      # jitters are multiples of this
LEAD_IN = 6.0              # fixation after the first trigger, before trial 1's ITI
LEAD_OUT = 12.0            # fixation after the last feedback (captures the HRF tail)
STOP_SOUND_AT_OFFSET = True  # cut the sound at shape offset if the wav is longer than STIM_DUR

# --- Design-efficiency simulation ----------------------------------------------
TR = 1.395
N_TIMING_CANDIDATES = 1000  # jitter sets evaluated per run

# --- Hardware -----------------------------------------------------------------
# The ` / ~ key is reported under different names depending on the keyboard backend,
# so all common names are accepted as the trigger.
TRIGGER_KEYS = ["grave", "`", "~", "asciitilde", "`~", "quoteleft"]
KEY_LEFT = "4"             # left index finger  -> NO MATCH
KEY_RIGHT = "7"            # right index finger -> MATCH
MATCH_KEY = KEY_RIGHT      # fixed for all participants (no counterbalancing)
KEY_ALIASES = {"num_4": KEY_LEFT, "num_7": KEY_RIGHT}  # keypad works too (testing on a laptop)
NOMATCH_KEY = KEY_LEFT
QUIT_KEY = "escape"
SCREEN_INDEX = 0
BG_COLOR = "gray"
SHAPE_SIZE = (0.35, 0.35)  # 'height' units (square, no aspect distortion)
FEEDBACK_SIZE = (0.15, 0.15)
SOUND_VOLUME = 1.0
AUDIO_LIBS = ["ptb", "sounddevice", "pygame"]  # PTB gives flip-locked audio onsets
AUDIO_LATENCY_MODE = 3     # PTB: 3 = aggressive low latency (use 1 if the device refuses)

# --- Sound check ---------------------------------------------------------------
SOUND_CHECK_N_BEEPS = 8            # beeps per sound-check attempt
SOUND_CHECK_GAP = (1.5, 4.0)       # random gap between beep onsets (s), so they can't be anticipated
SOUND_CHECK_WINDOW = 1.5           # a press within this time after a beep counts as "heard"
SOUND_CHECK_HZ = 523
SOUND_CHECK_TONE_DUR = 0.6



# =============================================================================
# DESIGN GENERATION (pure numpy - testable without PsychoPy)
# =============================================================================

def sanitize_id(pid):
    clean = re.sub(r"[^A-Za-z0-9]", "", str(pid))
    if not clean:
        raise ValueError("Participant ID must contain letters or digits.")
    return clean


def seed_from_id(pid):
    return zlib.crc32(("victr-xmodal-" + pid).encode()) & 0x7FFFFFFF


def derived_counts():
    n = len(STIM_INDICES)
    total = N_RUNS * TRIALS_PER_RUN
    if total % n:
        raise ValueError("Total trials must be divisible by the number of stimuli.")
    per_stim = total // n
    n_match = int(round(per_stim * P_MATCH))
    n_common = int(round(per_stim * COMMON_FOIL_PROP))
    n_rare = per_stim - n_match - n_common
    if abs(n_rare - per_stim * RARE_FOIL_PROP) >= 1 or n_rare <= 0:
        raise ValueError("Match / common / rare proportions do not sum sensibly.")
    return n, per_stim, n_match, n_common, n_rare


def _foil_arrangement(order, n):
    common = {order[k]: order[(k + COMMON_FOIL_OFFSET) % n] for k in range(n)}
    rare = {order[k]: order[(k + RARE_FOIL_OFFSET) % n] for k in range(n)}
    return common, rare


def _foil_distances(common, rare, n):
    """Sorted |index difference| between each sound's partner and its foils."""
    dc = tuple(sorted(abs(STIM_INDICES[s] - STIM_INDICES[common[s]]) for s in range(n)))
    dr = tuple(sorted(abs(STIM_INDICES[s] - STIM_INDICES[rare[s]]) for s in range(n)))
    return dc, dr


def foil_difficulty_profile(n):
    """
    Choose ONE (common, rare) foil-distance profile, the same for every participant.

    Candidates: Latin arrangements whose common and rare foils have equal mean
    distance to the correct sound. Among those, pick the profile whose common and
    rare distance distributions are most alike, then the one whose closest
    (hardest) foil is least close, then the one with most arrangements.
    Returns (profile, list of permutation orders that produce it).
    """
    from itertools import permutations
    groups = {}
    for order in permutations(range(n)):
        dc, dr = _foil_distances(*_foil_arrangement(order, n), n)
        if sum(dc) == sum(dr):
            groups.setdefault((dc, dr), []).append(order)
    if not groups:
        raise RuntimeError("No foil arrangement matches common and rare foil distances.")

    def rank(item):
        (dc, dr), orders = item
        spread_gap = sum(abs(a - b) for a, b in zip(dc, dr))
        return (spread_gap, -min(dc + dr), -len(orders))

    (profile, orders) = min(groups.items(), key=rank)
    return profile, orders


def build_foil_map(n, rng_py):
    """Return {sound_idx: shape_idx} for the common and rare foils (Latin rotation)."""
    if len({0, COMMON_FOIL_OFFSET % n, RARE_FOIL_OFFSET % n}) != 3:
        raise ValueError("Foil offsets must be distinct and non-zero (mod n).")
    if COUNTERBALANCE_FOILS and MATCH_FOIL_DIFFICULTY:
        _, orders = foil_difficulty_profile(n)
        order = list(rng_py.choice(orders))
    else:
        order = list(range(n))
        if COUNTERBALANCE_FOILS:
            rng_py.shuffle(order)
    return _foil_arrangement(order, n)


def phase_plan():
    """List of phases: dict(runs=[...], common='A'|'B'). Foil A is common first."""
    if SWAP_FOILS_AFTER_RUN is None:
        return [dict(phase=1, runs=list(range(1, N_RUNS + 1)), common="A")]
    k = int(SWAP_FOILS_AFTER_RUN)
    if not 1 <= k < N_RUNS:
        raise ValueError("SWAP_FOILS_AFTER_RUN must be between 1 and N_RUNS - 1 (or None).")
    return [dict(phase=1, runs=list(range(1, k + 1)), common="A"),
            dict(phase=2, runs=list(range(k + 1, N_RUNS + 1)), common="B")]


def build_combos(foil_a, foil_b):
    """The 18 shape-sound pairs. Pairs keep one pairing_id for the whole session;
    whether a foil pair is 'common' or 'rare' depends on the phase."""
    n = len(STIM_INDICES)
    combos = []
    for i in range(n):
        combos.append(dict(pairing_id=i, shape=i, sound=i, foil="", is_match=1))
    for s in range(n):
        combos.append(dict(pairing_id=n + s, shape=foil_a[s], sound=s, foil="A", is_match=0))
    for s in range(n):
        combos.append(dict(pairing_id=2 * n + s, shape=foil_b[s], sound=s, foil="B", is_match=0))
    return combos


def condition_of(combo, common_foil):
    if combo["is_match"]:
        return "match"
    return "mismatch_common" if combo["foil"] == common_foil else "mismatch_rare"


def _allocate_phase(n_runs, common, rare, need, rng, widen=(0, 0, 0)):
    """
    Choose n_runs run patterns. A pattern gives, for every sound s, (m, c, r) = how many
    times s appears with its partner, its (phase-)common foil and its rare foil in that
    run, such that each sound and each shape appears TRIALS_PER_RUN / n times in every
    run, each run's match count is the floor or ceil of the phase average, and the phase
    totals equal `need` exactly.
    """
    from itertools import product
    n = len(STIM_INDICES)
    per_run = TRIALS_PER_RUN // n
    phase_matches = int(need[:, 0].sum())
    ok_match = {phase_matches // n_runs, -(-phase_matches // n_runs)}

    def opts(col):
        lo = int(need[:, col].min()) // n_runs
        hi = -(-int(need[:, col].max()) // n_runs)
        return [v for v in range(lo - widen[col], hi + widen[col] + 1) if v >= 0]

    rows = [(m, c, r) for m in opts(0) for c in opts(1) for r in opts(2) if m + c + r == per_run]
    pats = []
    for pat in product(rows, repeat=n):
        if sum(p[0] for p in pat) not in ok_match:
            continue
        col = [pat[j][0] for j in range(n)]
        for s in range(n):
            col[common[s]] += pat[s][1]
            col[rare[s]] += pat[s][2]
        if all(v == per_run for v in col):
            pats.append(np.array(pat))
    if not pats:
        return None
    order = [pats[i] for i in rng.permutation(len(pats))]
    pmin, pmax = np.min(pats, axis=0), np.max(pats, axis=0)

    def dfs(start, remaining, k):
        if k == 0:
            return [] if not remaining.any() else None
        if (remaining < k * pmin).any() or (remaining > k * pmax).any():
            return None
        for i in range(start, len(order)):
            if (order[i] > remaining).any():
                continue
            out = dfs(i, remaining - order[i], k - 1)
            if out is not None:
                return [order[i]] + out
        return None

    chosen = dfs(0, need, n_runs)
    return None if chosen is None else [chosen[i] for i in rng.permutation(n_runs)]


def allocate_to_runs(combos, rng, foil_a, foil_b):
    """
    Exact allocation of the session's trials to runs, phase by phase.

    Per phase, every sound gets the same counts: matches = P_MATCH of its trials,
    common foil = COMMON_FOIL_PROP (rounded), rare foil = the rest. Every run has
    TRIALS_PER_RUN * P_MATCH matches and every shape and sound exactly
    TRIALS_PER_RUN / n times.
    Returns (list of combo-id lists per run, phase_info).
    """
    n = len(STIM_INDICES)
    per_run = TRIALS_PER_RUN / n
    if per_run != int(per_run):
        raise ValueError("TRIALS_PER_RUN must be a multiple of the number of stimuli.")
    per_run = int(per_run)
    plan = phase_plan()
    idx = {(c["sound"], c["foil"]): i for i, c in enumerate(combos)}
    runs, info = [None] * N_RUNS, []
    for ph in plan:
        R = len(ph["runs"])
        total = per_run * R
        base = total * P_MATCH
        if base != int(base):
            raise ValueError("Matches per sound in a phase are not a whole number; "
                             "choose another SWAP_FOILS_AFTER_RUN (or None).")
        m = int(base)
        n_common = int(round(total * COMMON_FOIL_PROP))
        n_rare = total - m - n_common
        if n_rare <= 0:
            raise ValueError("Match / common / rare proportions do not fit a phase.")
        need = np.array([(m, n_common, n_rare)] * n)
        common = foil_a if ph["common"] == "A" else foil_b
        rare = foil_b if ph["common"] == "A" else foil_a
        pats, used = None, None
        for widen in [(0, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0)]:
            pats = _allocate_phase(R, common, rare, need, rng, widen)
            if pats is not None:
                used = widen
                break
        if pats is None:
            raise RuntimeError("No balanced run allocation exists for phase %d; "
                               "try COMMON_FOIL_OFFSET=1, RARE_FOIL_OFFSET=4." % ph["phase"])
        rare_label = "B" if ph["common"] == "A" else "A"
        for run_no, p in zip(ph["runs"], pats):
            ids = []
            for s in range(n):
                ids += [idx[(s, "")]] * int(p[s][0])
                ids += [idx[(s, ph["common"])]] * int(p[s][1])
                ids += [idx[(s, rare_label)]] * int(p[s][2])
            runs[run_no - 1] = ids
        info.append(dict(phase=ph["phase"], runs=ph["runs"], common_foil=ph["common"],
                         rare_foil=rare_label, per_sound_counts=[m, n_common, n_rare],
                         widened=list(used)))
    return runs, info


def order_run(combo_ids, combos, rng_py, max_restarts=20000):
    """Randomised greedy ordering that respects the sequence constraints."""
    def valid(seq, c):
        if seq:
            prev = combos[seq[-1]]
            if NO_REPEAT_SHAPE and prev["shape"] == combos[c]["shape"]:
                return False
            if NO_REPEAT_SOUND and prev["sound"] == combos[c]["sound"]:
                return False
        if len(seq) >= MAX_SAME_STATUS_RUN:
            status = combos[c]["is_match"]
            if all(combos[x]["is_match"] == status for x in seq[-MAX_SAME_STATUS_RUN:]):
                return False
        return True

    for _ in range(max_restarts):
        remaining = list(combo_ids)
        rng_py.shuffle(remaining)
        seq = []
        while remaining:
            cands = [k for k, c in enumerate(remaining) if valid(seq, c)]
            if not cands:
                break
            seq.append(remaining.pop(rng_py.choice(cands)))
        if not remaining:
            return seq
    raise RuntimeError("Could not order run under the sequence constraints; relax them.")


def _truncexp_scale(mean_excess, width):
    """Scale s of an exponential truncated to [0, width] whose mean is mean_excess."""
    if not 0 < mean_excess < width / 2:
        raise ValueError("Jitter mean must lie between min and the midpoint of [min, max].")

    def tmean(s):
        e = math.exp(-width / s)
        return s - width * e / (1 - e)

    lo, hi = 1e-3, 1e4
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if tmean(mid) < mean_excess:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def sample_jitters(n, mean, lo, hi, rng):
    """Truncated-exponential jitters on [lo, hi], quantised, with an exact mean."""
    q = JITTER_QUANTUM
    width = hi - lo
    s = _truncexp_scale(mean - lo, width)
    u = rng.random(n)
    x = lo - s * np.log(1 - u * (1 - math.exp(-width / s)))
    steps = np.clip(np.round(x / q), round(lo / q), round(hi / q)).astype(int)
    target = int(round(n * mean / q))
    lo_s, hi_s = int(round(lo / q)), int(round(hi / q))
    guard = 0
    while steps.sum() != target and guard < 100000:
        guard += 1
        k = rng.integers(n)
        if steps.sum() < target and steps[k] < hi_s:
            steps[k] += 1
        elif steps.sum() > target and steps[k] > lo_s:
            steps[k] -= 1
    return steps * q


def spm_hrf(t):
    """SPM canonical double-gamma HRF (peak 6 s, undershoot 16 s, ratio 1/6)."""
    t = np.asarray(t, dtype=float)

    def gpdf(x, a):
        out = np.zeros_like(x)
        pos = x > 0
        out[pos] = x[pos] ** (a - 1) * np.exp(-x[pos]) / math.gamma(a)
        return out

    h = gpdf(t, 6.0) - gpdf(t, 16.0) / 6.0
    return h / h.sum()


_KERNELS = {}


def _boxcar_kernel(duration, dt=0.01, length=40.0):
    key = round(duration, 4)
    if key not in _KERNELS:
        t = np.arange(0, length, dt)
        h = spm_hrf(t)
        box = np.ones(max(1, int(round(duration / dt))))
        _KERNELS[key] = (t, np.convolve(h, box)[: len(t)])
    return _KERNELS[key]


def _regressor(onsets, duration, scan_times):
    kt, k = _boxcar_kernel(duration)
    lag = scan_times[:, None] - np.asarray(onsets, dtype=float)[None, :]
    return np.interp(lag, kt, k, left=0.0, right=0.0).sum(axis=1)


def build_timeline(iti, isi):
    t = LEAD_IN
    stim_on, fb_on = [], []
    for k in range(len(iti)):
        t += iti[k]
        stim_on.append(t)
        t += STIM_DUR + isi[k]
        fb_on.append(t)
        t += FEEDBACK_DUR
    return np.array(stim_on), np.array(fb_on), t + LEAD_OUT


def timing_score(stim_on, fb_on, is_match, run_end):
    """
    Max |r| between the matched / mismatched stimulus regressors and the feedback
    regressor (lower = better decorrelated), plus efficiency of matched-mismatched.
    """
    n_vols = int(math.ceil(run_end / TR))
    scan_t = np.arange(n_vols) * TR
    is_match = np.asarray(is_match).astype(bool)
    xm = _regressor(stim_on[is_match], STIM_DUR, scan_t)
    xn = _regressor(stim_on[~is_match], STIM_DUR, scan_t)
    xf = _regressor(fb_on, FEEDBACK_DUR, scan_t)
    c = np.corrcoef(np.vstack([xm, xn, xf]))
    corr = float(max(abs(c[0, 2]), abs(c[1, 2])))
    X = np.column_stack([xm, xn, xf, np.ones(n_vols)])
    con = np.array([1.0, -1.0, 0.0, 0.0])
    try:
        eff = float(1.0 / (con @ np.linalg.pinv(X.T @ X) @ con))
    except np.linalg.LinAlgError:
        eff = float("nan")
    return corr, eff, n_vols


def optimise_run_timing(is_match, rng):
    best = None
    n = len(is_match)
    for _ in range(N_TIMING_CANDIDATES):
        iti = sample_jitters(n, ITI_MEAN, ITI_MIN, ITI_MAX, rng)
        isi = sample_jitters(n, ISI_MEAN, ISI_MIN, ISI_MAX, rng)
        stim_on, fb_on, run_end = build_timeline(iti, isi)
        corr, eff, n_vols = timing_score(stim_on, fb_on, is_match, run_end)
        if best is None or corr < best["corr"]:
            best = dict(iti=iti, isi=isi, stim_on=stim_on, fb_on=fb_on,
                        run_end=run_end, corr=corr, eff=eff, n_vols=n_vols)
    return best


def generate_schedule(pid):
    """Build the full session: foil map, run allocation, trial order, jitters."""
    if RESPONSE_WINDOW > STIM_DUR + ISI_MIN - 0.1:
        raise ValueError("RESPONSE_WINDOW must close at least 100 ms before the earliest feedback.")
    seed = seed_from_id(pid)
    rng = np.random.default_rng(seed)
    rng_py = random.Random(seed)
    n = len(STIM_INDICES)

    foil_a, foil_b = build_foil_map(n, rng_py)
    combos = build_combos(foil_a, foil_b)
    runs, phase_info = allocate_to_runs(combos, rng, foil_a, foil_b)
    phase_of_run = {r: ph["phase"] for ph in phase_info for r in ph["runs"]}
    common_of_run = {r: ph["common_foil"] for ph in phase_info for r in ph["runs"]}

    shape_files = [f"shape_{i:02d}.png" for i in STIM_INDICES]
    sound_files = [f"sound_{i:02d}.wav" for i in STIM_INDICES]

    schedule, run_info = [], []
    t_session = 0
    for r in range(N_RUNS):
        seq = order_run(list(runs[r]), combos, rng_py)
        is_match = [combos[c]["is_match"] for c in seq]
        timing = optimise_run_timing(is_match, rng)
        run_info.append(dict(run=r + 1, stim_feedback_max_abs_r=round(timing["corr"], 4),
                             match_vs_mismatch_efficiency=round(timing["eff"], 4),
                             run_duration_s=round(timing["run_end"], 3),
                             volumes_needed=timing["n_vols"]))
        for k, c in enumerate(seq):
            t_session += 1
            cb = combos[c]
            schedule.append(dict(
                run=r + 1, trial_in_run=k + 1, trial_in_session=t_session,
                phase=phase_of_run[r + 1], foil=cb["foil"],
                pairing_id=cb["pairing_id"], condition=condition_of(cb, common_of_run[r + 1]),
                is_match=cb["is_match"],
                shape_idx=cb["shape"], sound_idx=cb["sound"],
                shape_file=shape_files[cb["shape"]], sound_file=sound_files[cb["sound"]],
                shape_orig_index=STIM_INDICES[cb["shape"]],
                sound_orig_index=STIM_INDICES[cb["sound"]],
                sound_distance=abs(STIM_INDICES[cb["shape"]] - STIM_INDICES[cb["sound"]]),
                iti=round(float(timing["iti"][k]), 3), isi=round(float(timing["isi"][k]), 3),
                stim_onset=round(float(timing["stim_on"][k]), 3),
                feedback_onset=round(float(timing["fb_on"][k]), 3),
                run_end=round(float(timing["run_end"]), 3),
            ))

    design = dict(
        participant=pid, seed=seed,
        created=datetime.datetime.now().isoformat(timespec="seconds"),
        stimuli=[dict(shape=shape_files[i], sound=sound_files[i]) for i in range(n)],
        foil_map={sound_files[s]: dict(foil_A=shape_files[foil_a[s]],
                                       foil_B=shape_files[foil_b[s]]) for s in range(n)},
        phases=phase_info,
        combos=[dict(pairing_id=c["pairing_id"], shape=shape_files[c["shape"]],
                     sound=sound_files[c["sound"]], foil=c["foil"],
                     count=sum(1 for t in schedule if t["pairing_id"] == c["pairing_id"]))
                for c in combos],
        foil_distances=dict(zip(("foil_A", "foil_B"),
                                map(list, _foil_distances(foil_a, foil_b, n)))),
        buttons=button_map(),
        runs=run_info,
        config=dict(N_RUNS=N_RUNS, TRIALS_PER_RUN=TRIALS_PER_RUN, STIM_DUR=STIM_DUR,
                    FEEDBACK_DUR=FEEDBACK_DUR, RESPONSE_WINDOW=RESPONSE_WINDOW,
                    ISI=[ISI_MEAN, ISI_MIN, ISI_MAX], ITI=[ITI_MEAN, ITI_MIN, ITI_MAX],
                    LEAD_IN=LEAD_IN, LEAD_OUT=LEAD_OUT, TR=TR,
                    TRIGGER_KEYS=TRIGGER_KEYS, STIM_INDICES=STIM_INDICES,
                    SWAP_FOILS_AFTER_RUN=SWAP_FOILS_AFTER_RUN, SURPRISE_DECAY=SURPRISE_DECAY,
                    N_TIMING_CANDIDATES=N_TIMING_CANDIDATES),
    )
    return design, schedule


def button_map():
    """Response mapping, taken from the configuration (identical for every participant)."""
    finger = {KEY_LEFT: "LEFT index finger", KEY_RIGHT: "RIGHT index finger"}
    return dict(match_key=MATCH_KEY, nomatch_key=NOMATCH_KEY,
                match_finger=finger[MATCH_KEY], nomatch_finger=finger[NOMATCH_KEY])


SCHEDULE_INT_COLS = ["run", "phase", "trial_in_run", "trial_in_session", "pairing_id", "is_match",
                     "shape_idx", "sound_idx", "shape_orig_index", "sound_orig_index",
                     "sound_distance"]
SCHEDULE_FLOAT_COLS = ["iti", "isi", "stim_onset", "feedback_onset", "run_end"]


def write_csv(path, rows, fieldnames=None, delimiter=","):
    fieldnames = fieldnames or list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def load_schedule(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r.setdefault("phase", "1")   # schedules made before the midpoint swap existed
        r.setdefault("foil", "")
        for c in SCHEDULE_INT_COLS:
            r[c] = int(r[c])
        for c in SCHEDULE_FLOAT_COLS:
            r[c] = float(r[c])
    return rows


def summarise_design(design, schedule):
    n = len(STIM_INDICES)
    print("\n=== DESIGN SUMMARY: sub-%s (seed %d) ===" % (design["participant"], design["seed"]))
    print("Buttons: MATCH = %s (%s), NO MATCH = %s (%s)" % (
        design["buttons"]["match_key"], design["buttons"]["match_finger"],
        design["buttons"]["nomatch_key"], design["buttons"]["nomatch_finger"]))
    if "phases" in design:
        print("Foil map (sound -> foil A / foil B):")
        for snd, f in design["foil_map"].items():
            print("   %s -> %s / %s" % (snd, f["foil_A"], f["foil_B"]))
        for ph in design["phases"]:
            print("Phase %d (runs %d-%d): foil %s COMMON, foil %s RARE; per sound "
                  "[match, common, rare] = %s" % (ph["phase"], ph["runs"][0], ph["runs"][-1],
                                                  ph["common_foil"], ph["rare_foil"],
                                                  ph["per_sound_counts"]))
        fd = design["foil_distances"]
        print("Foil distances (sorted; same for every participant): A %s | B %s"
              % (fd["foil_A"], fd["foil_B"]))
    else:  # design files made before the midpoint swap existed
        print("Foil map (sound -> common / rare foil shape):")
        for snd, f in design["foil_map"].items():
            print("   %s -> %s / %s" % (snd, f.get("common_foil"), f.get("rare_foil")))
    print("\nrun  phase  match  common  rare  shapes/run        sounds/run        max|r|  vols")
    for ri in design["runs"]:
        rows = [s for s in schedule if s["run"] == ri["run"]]
        sh = np.bincount([s["shape_idx"] for s in rows], minlength=n)
        so = np.bincount([s["sound_idx"] for s in rows], minlength=n)
        cond = [s["condition"] for s in rows]
        print("%3d  %5d  %5d  %6d  %4d  %-16s  %-16s  %.3f  %4d" % (
            ri["run"], rows[0]["phase"], cond.count("match"), cond.count("mismatch_common"),
            cond.count("mismatch_rare"), sh.tolist(), so.tolist(),
            ri["stim_feedback_max_abs_r"], ri["volumes_needed"]))
    pair_tot = np.bincount([s["pairing_id"] for s in schedule], minlength=3 * n)
    print("\nSession counts per pair (6 matched | 6 foil A | 6 foil B):")
    print("  ", pair_tot[:n].tolist(), pair_tot[n:2 * n].tolist(), pair_tot[2 * n:].tolist())
    print("Shape totals:", np.bincount([s["shape_idx"] for s in schedule], minlength=n).tolist())
    print("Sound totals:", np.bincount([s["sound_idx"] for s in schedule], minlength=n).tolist())
    print("Run duration: %.2f s -> set the scanner to >= %d volumes per run (TR = %.3f s)\n" % (
        design["runs"][0]["run_duration_s"], max(r["volumes_needed"] for r in design["runs"]), TR))


# =============================================================================
# PSYCHOPY RUNTIME
# =============================================================================

visual = core = event = sound = gui = keyboard = None


def import_psychopy():
    global visual, core, event, sound, gui, keyboard
    from psychopy import prefs
    prefs.hardware["audioLib"] = AUDIO_LIBS
    prefs.hardware["audioLatencyMode"] = AUDIO_LATENCY_MODE
    if sys.platform == "darwin":
        os.environ.setdefault("QT_QPA_PLATFORM", "cocoa")
    from psychopy import visual as _v, core as _c, event as _e, sound as _s, gui as _g
    from psychopy import logging as _l
    from psychopy.hardware import keyboard as _k
    _l.console.setLevel(_l.ERROR)
    visual, core, event, sound, gui, keyboard = _v, _c, _e, _s, _g, _k


def get_session_info():
    info = {"participant": "", "start_run": 1,
            "sound_check": True, "fullscreen": True}
    dlg = gui.DlgFromDict(info, title="Crossmodal fMRI task",
                          order=["participant", "start_run",
                                 "sound_check", "fullscreen"])
    if not dlg.OK:
        core.quit()
    info["participant"] = sanitize_id(info["participant"])
    info["start_run"] = int(info["start_run"])
    if not 1 <= info["start_run"] <= N_RUNS:
        raise ValueError("start_run must be between 1 and %d" % N_RUNS)
    return info


class CrossmodalFMRITask:

    TRIAL_FIELDS = [
        "participant", "run", "phase", "attempt", "trial_in_run", "trial_in_session",
        "presentation_index", "pairing_id", "condition", "foil", "is_match",
        "shape_file", "sound_file", "shape_orig_index", "sound_orig_index", "sound_distance",
        "correct_key", "correct_response", "response_status", "response_key", "response",
        "rt", "accuracy", "missed", "late_response_key", "late_response", "late_rt",
        "late_accuracy", "n_presses", "all_presses", "n_extra_presses", "iti", "isi",
        "stim_onset_sched", "stim_onset", "stim_offset",
        "feedback_onset_sched", "feedback_onset", "feedback_offset", "feedback_shown",
        "pairing_count_before", "surprise_IS", "surprise_IS_leaky", "completed", "wall_time",
    ]
    RUN_FIELDS = ["participant", "run", "attempt", "status", "start_wall_time",
                  "n_trials_completed", "accuracy", "n_missed", "n_late", "n_triggers",
                  "last_trigger_time", "volumes_expected", "dropped_frames", "events_file"]

    def __init__(self, info, design, schedule, folder):
        self.info, self.design, self.schedule, self.folder = info, design, schedule, folder
        self.pid = info["participant"]
        self.prefix = os.path.join(folder, "sub-%s" % self.pid)
        self.trials_path = self.prefix + "_trials.csv"
        self.runs_path = self.prefix + "_runs.csv"
        self.events_dir = os.path.join(folder, "events")
        os.makedirs(self.events_dir, exist_ok=True)

        self.match_key = design["buttons"]["match_key"]
        self.nomatch_key = design["buttons"]["nomatch_key"]
        self.resp_keys = [KEY_LEFT, KEY_RIGHT] + list(KEY_ALIASES)

        self._check_files()
        self.win = visual.Window(screen=SCREEN_INDEX, fullscr=info["fullscreen"],
                                 color=BG_COLOR, units="height", allowGUI=False)
        self.win.mouseVisible = False
        fr = self.win.getActualFrameRate(nIdentical=20, nMaxFrames=120, nWarmUpFrames=20)
        self.frame_dur = 1.0 / fr if fr else 1.0 / 60.0
        print("Measured frame rate: %s Hz" % (round(fr, 2) if fr else "unknown (assuming 60)"))

        self.kb = keyboard.Keyboard()
        self.run_clock = self.kb.clock  # key RTs and flip times share one time base
        self.ptb_audio = "ptb" in str(getattr(sound, "audioLib", "")).lower()
        if not self.ptb_audio:
            print("WARNING: PTB audio backend not active (%s); audio onsets will be less precise."
                  % getattr(sound, "audioLib", "?"))

        # --- stimuli (preloaded so nothing is read from disk during a run) ---
        n = len(STIM_INDICES)
        self.fixation = visual.TextStim(self.win, text="+", color="white", height=0.07)
        self.shapes = {i: visual.ImageStim(self.win, image=os.path.join(IMAGE_DIR, f"shape_{s:02d}.png"),
                                           size=SHAPE_SIZE) for i, s in enumerate(STIM_INDICES)}
        self.sounds = {i: sound.Sound(os.path.join(AUDIO_DIR, f"sound_{s:02d}.wav"),
                                      stereo=True, volume=SOUND_VOLUME)
                       for i, s in enumerate(STIM_INDICES)}
        self.fb_correct = self._feedback_stim(FEEDBACK_CORRECT_IMG, "Correct", "#2ecc40")
        self.fb_incorrect = self._feedback_stim(FEEDBACK_INCORRECT_IMG, "Incorrect", "#ff4136")
        self.fb_missed = visual.TextStim(self.win, text="Too slow!", color="yellow", height=0.06)
        self.msg = visual.TextStim(self.win, text="", color="white", height=0.035, wrapWidth=1.2)

        # --- session-wide presentation history (for the surprise estimator) ---
        self.n_combos = len(design["combos"])
        self.pair_counts = np.zeros(self.n_combos, dtype=int)
        self.n_presented = 0
        self.leaky_counts = np.zeros(self.n_combos)
        self.leaky_total = 0.0
        if os.path.exists(self.trials_path):
            with open(self.trials_path, newline="") as f:
                for row in csv.DictReader(f):  # replay history in presentation order
                    self._update_history(int(row["pairing_id"]))
            print("Loaded %d previously presented trials from %s" % (self.n_presented, self.trials_path))

    # ---------------------------------------------------------------- helpers
    def _surprise(self, pid):
        """Cumulative (proposal) and forgetting Laplace-smoothed surprise for pair `pid`."""
        p = (1.0 + self.pair_counts[pid]) / (self.n_combos + self.n_presented)
        p_leaky = (1.0 + self.leaky_counts[pid]) / (self.n_combos + self.leaky_total)
        return -math.log(p), -math.log(p_leaky)

    def _update_history(self, pid):
        self.pair_counts[pid] += 1
        self.n_presented += 1
        self.leaky_counts *= SURPRISE_DECAY
        self.leaky_total *= SURPRISE_DECAY
        self.leaky_counts[pid] += 1.0
        self.leaky_total += 1.0

    def _check_files(self):
        missing = [p for i in STIM_INDICES for p in (
            os.path.join(IMAGE_DIR, f"shape_{i:02d}.png"),
            os.path.join(AUDIO_DIR, f"sound_{i:02d}.wav")) if not os.path.exists(p)]
        if missing:
            raise FileNotFoundError("Missing stimulus files:\n  " + "\n  ".join(missing))

    def _feedback_stim(self, img, fallback_text, color):
        if os.path.exists(img):
            return visual.ImageStim(self.win, image=img, size=FEEDBACK_SIZE)
        print("Feedback image %s not found; using text instead." % img)
        return visual.TextStim(self.win, text=fallback_text, color=color, height=0.06)

    def _future_flip(self):
        try:
            return self.win.getFutureFlipTime(clock=self.run_clock)
        except Exception:
            return self.run_clock.getTime() + self.frame_dur

    def _play_on_flip(self, snd):
        snd.stop()
        if self.ptb_audio:
            snd.play(when=self.win.getFutureFlipTime(clock="ptb"))
        else:
            self.win.callOnFlip(snd.play)

    def _append_row(self, path, fields, row, delimiter=","):
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, delimiter=delimiter, extrasaction="ignore",
                               lineterminator="\n")
            if new:
                w.writeheader()
            w.writerow(row)

    def _next_attempt(self, run):
        if not os.path.exists(self.runs_path):
            return 1
        with open(self.runs_path, newline="") as f:
            prev = [int(r["attempt"]) for r in csv.DictReader(f) if int(r["run"]) == run]
        return max(prev) + 1 if prev else 1

    def quit(self):
        for s in self.sounds.values():
            s.stop()
        self.win.close()
        core.quit()

    def show_message(self, text, keys):
        """Show text until one of `keys` is pressed. Escape quits the session."""
        self.msg.text = text
        self.kb.clearEvents()
        while True:
            self.msg.draw()
            self.win.flip()
            for k in self.kb.getKeys(keyList=keys + [QUIT_KEY], waitRelease=False):
                if k.name == QUIT_KEY:
                    self.quit()
                return k.name

    def wait_for_trigger(self, run):
        self.msg.text = ("Run %d of %d\n\nGet ready - the task will start in a moment.\n\n"
                         "Please keep your head still and look at the centre of the screen." % (run, N_RUNS))
        self.msg.draw()
        self.win.flip()
        self.kb.clearEvents()
        print("Run %d: waiting for scanner trigger (~) ... (escape to cancel)" % run)
        while True:
            for k in self.kb.getKeys(keyList=TRIGGER_KEYS + [QUIT_KEY], waitRelease=False):
                if k.name == QUIT_KEY:
                    return False
                self.run_clock.reset()  # t = 0 at the first trigger
                self.kb.clearEvents()   # drop presses made before the run started
                return True
            core.wait(0.0005, hogCPUperiod=0.0005)

    # ---------------------------------------------------------------- one run
    def run_block(self, run, attempt):
        trials = sorted([s for s in self.schedule if s["run"] == run], key=lambda s: s["trial_in_run"])
        run_end = trials[0]["run_end"]
        vols = next(r["volumes_needed"] for r in self.design["runs"] if r["run"] == run)
        start_wall = datetime.datetime.now().isoformat(timespec="seconds")

        # Timeline segments: (start time, kind, trial index)
        segs = [(0.0, "fix", None)]
        for k, tr in enumerate(trials):
            segs += [(tr["stim_onset"], "stim", k),
                     (tr["stim_onset"] + STIM_DUR, "isi", k),
                     (tr["feedback_onset"], "fb", k),
                     (tr["feedback_onset"] + FEEDBACK_DUR, "fix", k)]

        st = [dict(stim_onset=None, stim_offset=None, fb_onset=None, fb_offset=None,
                   response_key=None, rt=None, extra=0, written=False, fb_shown="",
                   presses=[], late_key=None, late_rt=None,
                   accuracy="", surprise=None, surprise_leaky=None, count_before=None,
                   presentation_index=None)
              for _ in trials]
        for x in st:
            x["presses"] = []  # own list per trial
        triggers, presses = [], []

        if not self.wait_for_trigger(run):
            return "cancelled", None
        triggers.append(0.0)
        self.win.recordFrameIntervals = True
        self.win.nDroppedFrames = 0

        seg_i, last_stim, fb_stim, status = 0, None, None, "completed"
        key_list = self.resp_keys + TRIGGER_KEYS + [QUIT_KEY]
        fd = self.frame_dur

        while True:
            t_next = self._future_flip()
            if t_next >= run_end - fd / 2:
                break
            pending = []
            while seg_i + 1 < len(segs) and t_next >= segs[seg_i + 1][0] - fd / 2:
                seg_i += 1
                _, kind, k = segs[seg_i]
                tr = trials[k] if k is not None else None
                if kind == "stim":
                    if last_stim is not None and not st[last_stim]["written"]:
                        pending.append(last_stim)  # its presses run until this onset
                    st[k]["stim_onset"] = t_next
                    last_stim = k
                    self._play_on_flip(self.sounds[tr["sound_idx"]])
                    # Laplace-smoothed running frequency of this combination (Proposal Aim 2)
                    is_cum, is_leaky = self._surprise(tr["pairing_id"])
                    st[k].update(count_before=int(self.pair_counts[tr["pairing_id"]]),
                                 surprise=is_cum, surprise_leaky=is_leaky,
                                 presentation_index=self.n_presented + 1)
                    self._update_history(tr["pairing_id"])
                elif kind == "isi":
                    st[k]["stim_offset"] = t_next
                    if STOP_SOUND_AT_OFFSET:
                        self.win.callOnFlip(self.sounds[tr["sound_idx"]].stop)
                elif kind == "fb":
                    st[k]["fb_onset"] = t_next
                    rk = st[k]["response_key"]
                    if rk is None:
                        fb_stim = self.fb_missed
                        st[k]["fb_shown"] = "too_slow" if st[k]["late_key"] else "no_response"
                    else:
                        correct = (rk == self.match_key) == bool(tr["is_match"])
                        st[k]["accuracy"] = int(correct)
                        fb_stim = self.fb_correct if correct else self.fb_incorrect
                        st[k]["fb_shown"] = "correct" if correct else "incorrect"
                elif kind == "fix" and k is not None:
                    st[k]["fb_offset"] = t_next

            kind, k = segs[seg_i][1], segs[seg_i][2]
            if kind == "stim":
                self.shapes[trials[k]["shape_idx"]].draw()
            elif kind == "fb":
                fb_stim.draw()
            else:
                self.fixation.draw()
            self.win.flip()

            for kk in pending:
                self._write_trial(run, attempt, trials[kk], st[kk], completed=1)

            for key in self.kb.getKeys(keyList=key_list, waitRelease=False, clear=True):
                if key.name == QUIT_KEY:
                    status = "aborted"
                    break
                if key.name in TRIGGER_KEYS:
                    triggers.append(key.rt)
                    continue
                if key.rt < 0:
                    continue
                key.name = KEY_ALIASES.get(key.name, key.name)
                presses.append((key.rt, key.name))
                if last_stim is not None:
                    s = st[last_stim]
                    rel = key.rt - s["stim_onset"]
                    if rel < 0:
                        continue
                    s["presses"].append((rel, key.name))
                    before_fb = s["fb_onset"] is None or key.rt < s["fb_onset"]
                    if rel <= RESPONSE_WINDOW and s["response_key"] is None:
                        s["response_key"], s["rt"] = key.name, rel          # the answer
                    elif (s["response_key"] is None and s["late_key"] is None
                          and before_fb):
                        s["late_key"], s["late_rt"] = key.name, rel        # too slow, kept
                    else:
                        s["extra"] += 1
            if status == "aborted":
                break

        for s in self.sounds.values():
            s.stop()
        self.win.recordFrameIntervals = False
        for k, s in enumerate(st):  # trials whose stimulus was shown but not logged yet
            if s["stim_onset"] is not None and not s["written"]:
                self._write_trial(run, attempt, trials[k], s,
                                  completed=int(s["fb_offset"] is not None))

        events_file = self._write_events(run, attempt, trials, st, presses)
        done = [s for s in st if s["written"] and s["fb_offset"] is not None]
        answered = [s for s in done if s["response_key"] is not None]
        acc = np.mean([s["accuracy"] for s in answered]) if answered else float("nan")
        summary = dict(participant=self.pid, run=run,
                       attempt=attempt, status=status, start_wall_time=start_wall,
                       n_trials_completed=len(done), accuracy=round(float(acc), 3),
                       n_missed=len(done) - len(answered),
                       n_late=sum(1 for x in done if x["late_key"] is not None),
                       n_triggers=len(triggers),
                       last_trigger_time=round(triggers[-1], 3), volumes_expected=vols,
                       dropped_frames=self.win.nDroppedFrames,
                       events_file=os.path.basename(events_file))
        self._append_row(self.runs_path, self.RUN_FIELDS, summary)
        return status, summary

    def _write_trial(self, run, attempt, tr, s, completed):
        def r3(x):
            return "" if x is None else round(x, 4)
        correct_key = self.match_key if tr["is_match"] else self.nomatch_key
        rk = s["response_key"]
        row = dict(
            participant=self.pid, run=run,
            phase=tr.get("phase", 1), attempt=attempt, trial_in_run=tr["trial_in_run"], trial_in_session=tr["trial_in_session"],
            presentation_index=s["presentation_index"], pairing_id=tr["pairing_id"],
            condition=tr["condition"], foil=tr.get("foil", ""), is_match=tr["is_match"],
            shape_file=tr["shape_file"], sound_file=tr["sound_file"],
            shape_orig_index=tr["shape_orig_index"], sound_orig_index=tr["sound_orig_index"],
            sound_distance=tr["sound_distance"] if not tr["is_match"] else "",
            correct_key=correct_key, correct_response="match" if tr["is_match"] else "nomatch",
            response_status="on_time" if rk else ("late" if s["late_key"] else "none"),
            response_key=rk or "",
            response="" if rk is None else ("match" if rk == self.match_key else "nomatch"),
            rt=r3(s["rt"]), accuracy=s["accuracy"], missed=int(rk is None),
            late_response_key=s["late_key"] or "",
            late_response="" if s["late_key"] is None else (
                "match" if s["late_key"] == self.match_key else "nomatch"),
            late_rt=r3(s["late_rt"]),
            late_accuracy="" if s["late_key"] is None else int(
                (s["late_key"] == self.match_key) == bool(tr["is_match"])),
            n_presses=len(s["presses"]),
            all_presses=";".join("%s@%.4f" % (kname, t) for t, kname in s["presses"]),
            n_extra_presses=s["extra"], iti=tr["iti"], isi=tr["isi"],
            stim_onset_sched=tr["stim_onset"], stim_onset=r3(s["stim_onset"]),
            stim_offset=r3(s["stim_offset"]), feedback_onset_sched=tr["feedback_onset"],
            feedback_onset=r3(s["fb_onset"]), feedback_offset=r3(s["fb_offset"]),
            feedback_shown=s["fb_shown"], pairing_count_before=s["count_before"],
            surprise_IS=r3(s["surprise"]), surprise_IS_leaky=r3(s["surprise_leaky"]),
            completed=completed,
            wall_time=datetime.datetime.now().isoformat(timespec="milliseconds"),
        )
        self._append_row(self.trials_path, self.TRIAL_FIELDS, row)
        s["written"] = True

    def _write_events(self, run, attempt, trials, st, presses):
        """BIDS-style events.tsv (onsets relative to the first trigger of the run)."""
        def na(x, nd=4):
            return "n/a" if x is None or x == "" else (round(x, nd) if isinstance(x, float) else x)
        rows = []
        for tr, s in zip(trials, st):
            if s["stim_onset"] is None:
                continue
            rk = s["response_key"]
            resp = "n/a" if rk is None else ("match" if rk == self.match_key else "nomatch")
            common = dict(trial=tr["trial_in_run"], phase=tr.get("phase", 1),
                          foil=tr.get("foil", "") or "n/a", pairing_id=tr["pairing_id"],
                          is_match=tr["is_match"], shape=tr["shape_file"], sound=tr["sound_file"],
                          response=resp, response_time=na(s["rt"]), accuracy=na(s["accuracy"]),
                          response_status="on_time" if rk else (
                              "late" if s["late_key"] else "none"),
                          late_response_time=na(s["late_rt"]),
                          surprise_IS=na(s["surprise"]),
                          surprise_IS_leaky=na(s["surprise_leaky"]))
            off = s["stim_offset"] if s["stim_offset"] is not None else s["stim_onset"] + STIM_DUR
            rows.append(dict(onset=round(s["stim_onset"], 4), duration=round(off - s["stim_onset"], 4),
                             trial_type=tr["condition"], **common))
            if s["fb_onset"] is not None:
                fo = s["fb_offset"] if s["fb_offset"] is not None else s["fb_onset"] + FEEDBACK_DUR
                rows.append(dict(onset=round(s["fb_onset"], 4), duration=round(fo - s["fb_onset"], 4),
                                 trial_type="feedback_" + s["fb_shown"], **common))
        for t, name in presses:
            rows.append(dict(onset=round(t, 4), duration=0, trial_type="button_press",
                             trial="n/a", phase="n/a", foil="n/a", pairing_id="n/a",
                             is_match="n/a", shape="n/a", sound="n/a",
                             response="match" if name == self.match_key else "nomatch",
                             response_time="n/a", accuracy="n/a", response_status="n/a",
                             late_response_time="n/a", surprise_IS="n/a",
                             surprise_IS_leaky="n/a"))
        rows.sort(key=lambda r: r["onset"])
        tag = "" if attempt == 1 else "_attempt-%d" % attempt
        path = os.path.join(self.events_dir, "sub-%s_task-%s_run-%02d%s_events.tsv"
                            % (self.pid, TASK_LABEL, run, tag))
        fields = ["onset", "duration", "trial_type", "trial", "phase", "foil", "pairing_id",
                  "is_match", "shape", "sound", "response", "response_time", "accuracy",
                  "response_status", "late_response_time", "surprise_IS", "surprise_IS_leaky"]
        if rows:
            write_csv(path, rows, fields, delimiter="\t")
        return path

    # ---------------------------------------------------------- pre-scan parts
    def sound_check(self):
        """
        Beep-detection check. Beeps come at random intervals; the participant presses
        either button whenever they hear one. Each beep and press is reported live in
        the terminal and logged to sub-<ID>_soundcheck.csv.
        """
        log_path = self.prefix + "_soundcheck.csv"
        fields = ["participant", "attempt", "beep", "onset", "heard", "rt", "false_presses_total"]
        rng = random.Random()
        attempt = 0
        while True:
            attempt += 1
            # A fresh Sound object per beep: replaying one short tone object is unreliable.
            tones = [sound.Sound(value=SOUND_CHECK_HZ, secs=SOUND_CHECK_TONE_DUR, stereo=True,
                                 hamming=True, volume=SOUND_VOLUME)
                     for _ in range(SOUND_CHECK_N_BEEPS)]
            self.show_message("SOUND CHECK\n\nYou will hear some beeps at random times.\n\n"
                              "Press EITHER button as soon as you hear each beep.\n"
                              "Do not press if you don't hear anything.\n\n"
                              "Press either button to start.", self.resp_keys + ["space"])

            onsets, t = [], 1.5
            for _ in range(SOUND_CHECK_N_BEEPS):
                onsets.append(t)
                t += rng.uniform(*SOUND_CHECK_GAP)
            end = onsets[-1] + SOUND_CHECK_WINDOW + 0.5
            played = [None] * len(onsets)
            rts = [None] * len(onsets)
            reported = [False] * len(onsets)
            false_presses = 0

            print("\n--- SOUND CHECK (attempt %d): %d beeps ---" % (attempt, len(onsets)))
            self.fixation.draw()
            self.win.flip()
            self.kb.clearEvents()
            self.kb.clock.reset()
            nxt = 0
            while self.kb.clock.getTime() < end:
                now = self.kb.clock.getTime()
                if nxt < len(onsets) and now >= onsets[nxt]:
                    tones[nxt].play()
                    played[nxt] = now
                    print("  beep %d/%d played   (t = %.2f s)" % (nxt + 1, len(onsets), now))
                    nxt += 1
                self.fixation.draw()
                self.win.flip()

                for k in self.kb.getKeys(keyList=self.resp_keys + [QUIT_KEY], waitRelease=False):
                    if k.name == QUIT_KEY:
                        self.quit()
                    hit = None
                    for j in range(nxt):
                        if (rts[j] is None and played[j] is not None
                                and played[j] <= k.rt <= played[j] + SOUND_CHECK_WINDOW):
                            hit = j
                    if hit is not None:
                        rts[hit] = k.rt - played[hit]
                        print("      -> HEARD beep %d   (button %s, RT %.2f s)"
                              % (hit + 1, k.name, rts[hit]))
                    else:
                        false_presses += 1
                        print("      ?? press with no beep   (button %s, t = %.2f s)" % (k.name, k.rt))

                now = self.kb.clock.getTime()
                for j in range(nxt):
                    if not reported[j] and rts[j] is None and now > played[j] + SOUND_CHECK_WINDOW:
                        reported[j] = True
                        print("      xx MISSED beep %d" % (j + 1))

            for tone in tones:
                tone.stop()
            n_heard = sum(r is not None for r in rts)
            print("Result: heard %d / %d beeps, %d presses without a beep."
                  % (n_heard, len(onsets), false_presses))
            for j, on in enumerate(played):
                self._append_row(log_path, fields, dict(
                    participant=self.pid, attempt=attempt, beep=j + 1,
                    onset="" if on is None else round(on, 3), heard=int(rts[j] is not None),
                    rt="" if rts[j] is None else round(rts[j], 3),
                    false_presses_total=false_presses))
            print("Experimenter: SPACE = continue | R = repeat sound check")
            choice = self.show_message("Thank you.\n\nPlease wait for the experimenter.", ["space", "r"])
            if choice == "space":
                return

    # ---------------------------------------------------------------- session
    def instructions_text(self):
        b = self.design["buttons"]
        return ("You will see a SHAPE and hear a SOUND at the same time.\n\n"
                "Some shapes and sounds are a MATCH and some DO NOT MATCH.\n\n"
                "If you think they MATCH, press with your %s.\n"
                "If you think they do NOT match, press with your %s.\n\n"
                "Try to answer as FAST AS POSSIBLE.\n\n"
                "After a short pause you will see whether you were right or wrong. "
                "Please try to remember the MATCHED pairings.\n\n"
                "These are NEW shapes and sounds, not the ones from the practice.\n\n"
                "Keep your head still and your eyes on the centre of the screen.\n\n"
                "Press either button to continue."
                % (b["match_finger"], b["nomatch_finger"]))

    def run_session(self):
        info = self.info
        if info["sound_check"]:
            self.sound_check()
        self.show_message(self.instructions_text(), self.resp_keys + ["space"])
        b = self.design["buttons"]
        self.show_message("The task is about to begin.\n\nMATCH = %s\nNO MATCH = %s\n\n"
                          "Press either button to begin."
                          % (b["match_finger"], b["nomatch_finger"]), self.resp_keys + ["space"])

        run = info["start_run"]
        while run <= N_RUNS:
            attempt = self._next_attempt(run)
            status, summary = self.run_block(run, attempt)
            if summary:
                print("Run %d (attempt %d) %s | acc %.2f | no answer in time %d (of which late %d) | "
                      "triggers %d / %d vols | dropped frames %d"
                      % (run, attempt, status, summary["accuracy"], summary["n_missed"],
                         summary["n_late"], summary["n_triggers"],
                                             summary["volumes_expected"], summary["dropped_frames"]))
            nxt = "run %d" % (run + 1) if run < N_RUNS else "finish"
            print("Experimenter: SPACE = %s | R = repeat run %d | Q = quit" % (nxt, run))
            text = ("Run %d of %d finished.\n\nPlease rest and keep still.\n"
                    "The next part will start soon." % (run, N_RUNS))
            choice = self.show_message(text, ["space", "r", "q"])
            if choice == "q":
                break
            if choice == "r":
                continue
            if run == N_RUNS:
                break
            run += 1

        self.show_message("All done!\n\nThank you. Please stay still until the scanner stops.",
                          ["space"])
        self.quit()


# =============================================================================
# MAIN
# =============================================================================

def load_or_create_design(pid, folder):
    prefix = os.path.join(folder, "sub-%s" % pid)
    design_path, sched_path = prefix + "_design.json", prefix + "_schedule.csv"
    if os.path.exists(design_path) and os.path.exists(sched_path):
        with open(design_path) as f:
            design = json.load(f)
        schedule = load_schedule(sched_path)
        print("Loaded existing design and schedule for sub-%s (restart)." % pid)
        if "phases" not in design and SWAP_FOILS_AFTER_RUN is not None:
            print("\n*** WARNING: this participant's saved schedule was made WITHOUT the foil swap. "
                  "Delete %s to rebuild it with the swap. ***\n" % folder)
        if design.get("buttons") != button_map():  # older files used a counterbalanced mapping
            design["buttons"] = button_map()
            with open(design_path, "w") as f:
                json.dump(design, f, indent=2)
            print("Updated the saved button mapping to MATCH = %s, NO MATCH = %s." % (MATCH_KEY, NOMATCH_KEY))
    else:
        print("Generating schedule for sub-%s (design-efficiency search) ..." % pid)
        design, schedule = generate_schedule(pid)
        with open(design_path, "w") as f:
            json.dump(design, f, indent=2)
        write_csv(sched_path, schedule)
    summarise_design(design, schedule)
    return design, schedule


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design-only", metavar="PID",
                    help="generate and summarise a schedule without running PsychoPy")
    args = ap.parse_args()

    if args.design_only:
        pid = sanitize_id(args.design_only)
        folder = os.path.join("./design_preview", "sub-%s" % pid)
        os.makedirs(folder, exist_ok=True)
        load_or_create_design(pid, folder)
        print("Preview written to", folder)
        return

    import_psychopy()
    info = get_session_info()
    folder = os.path.join(DATA_DIR, "sub-%s" % info["participant"])
    os.makedirs(folder, exist_ok=True)  # never deletes existing data (runs may be resumed)
    design, schedule = load_or_create_design(info["participant"], folder)
    with open(os.path.join(folder, "sub-%s_session-start_%s.json" % (
            info["participant"], datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))), "w") as f:
        json.dump(info, f, indent=2)

    task = CrossmodalFMRITask(info, design, schedule, folder)
    task.run_session()


if __name__ == "__main__":
    main()