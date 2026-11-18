#!/usr/bin/env python3
"""
survey.py
=========

Online version of practice_fmri_task.py. Runs a small web server on YOUR laptop,
opens a public https tunnel to it, and prints a link you can send to participants.
Every trial is sent back to your laptop the moment it ends and appended to

    ./participant_data_fmri/sub-<ID>/sub-<ID>_practice.csv

(the same folder and the same columns as the PsychoPy practice script).

Keep this file in the fMRI folder, next to fmri_task.py, green_tick.png and red_cross.png.

Usage
    python survey.py                      # tunnel: cloudflared if installed, else ngrok
    python survey.py --tunnel ngrok
    python survey.py --tunnel none        # local only: http://localhost:8000

Tunnel tools (install one)
    cloudflared  (no account; new link every start)   macOS: brew install cloudflared
    ngrok        (free account + `ngrok config add-authtoken <token>` once)

Your laptop must stay on, awake and running this script while participants do the task.
Stop with Ctrl+C.

Same as the lab version: 3 practice shapes (circle/square/triangle), 3 pure tones
(330/523/784 Hz) with a per-participant mapping (identical to the PsychoPy version for
the same ID), 18 trials per block, 7 = MATCH, 4 = NO MATCH, 3 s response window,
"Too slow!" for late presses, all presses saved, jittered ISI/ITI, Escape quits.

Differences: there is no experimenter at the keyboard, so after each block the
participant chooses R (practise again) or SPACE (finish), up to MAX_BLOCKS blocks.
Browser timing is frame-locked (requestAnimationFrame) but not lab-grade; expect a few
tens of ms of extra, device-dependent latency in RTs and audio onset.
"""

import argparse
import csv
import datetime
import importlib.machinery
import importlib.util
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

# --- Task settings (taken from fmri_task.py when it is in this folder) -----------------
DEFAULTS = dict(
    STIM_DUR=2.0, FEEDBACK_DUR=0.75, RESPONSE_WINDOW=3.0,
    ISI_MEAN=2.50, ISI_MIN=1.5, ISI_MAX=4.5,
    ITI_MEAN=2.25, ITI_MIN=0.5, ITI_MAX=5.0, JITTER_QUANTUM=0.05,
    KEY_LEFT="4", KEY_RIGHT="7", MATCH_KEY="7", NOMATCH_KEY="4",
    DATA_DIR="./participant_data_fmri",
    FEEDBACK_CORRECT_IMG="green_tick.png", FEEDBACK_INCORRECT_IMG="red_cross.png",
)
S = dict(DEFAULTS)
_task_path = os.path.join(HERE, "fmri_task.py")
if os.path.isfile(_task_path):
    try:
        _loader = importlib.machinery.SourceFileLoader("fmri_task_shared", _task_path)
        _spec = importlib.util.spec_from_loader("fmri_task_shared", _loader)
        _T = importlib.util.module_from_spec(_spec)
        _loader.exec_module(_T)
        for k in S:
            S[k] = getattr(_T, k, S[k])
        print("Using task settings from fmri_task.py")
    except Exception as e:  # e.g. numpy missing - the defaults above are identical
        print("Could not load fmri_task.py (%s); using built-in settings." % e)

PRACTICE_TONES_HZ = [330, 523, 784]
SHAPE_NAMES = ["circle", "square", "triangle"]
TRIALS_PER_SHAPE = 6
GOOD_ACCURACY = 0.75
MAX_BLOCKS = 4                 # participant can repeat the block up to this many times
TONE_VOLUME = 0.5              # 0-1, browser output gain (participants set their own volume)

FIELDS = ["participant", "block", "trial", "shape", "tone_hz", "is_match",
          "correct_response", "response_status", "response_key", "response", "rt",
          "accuracy", "missed", "late_response_key", "late_response", "late_rt",
          "late_accuracy", "n_presses", "all_presses", "iti", "isi", "wall_time"]

_write_lock = threading.Lock()


# --- Same logic as practice_fmri_task.py / fmri_task.py --------------------------------
def sanitize_id(pid):
    return re.sub(r"[^A-Za-z0-9]", "", str(pid))[:40]


def seed_from_id(pid):
    return zlib.crc32(("victr-xmodal-" + pid).encode()) & 0x7FFFFFFF


def tone_mapping(pid):
    """Same seeded shuffle as practice_fmri_task.py, so a given ID gets the same mapping."""
    rng = random.Random(seed_from_id(pid) + 1)
    tones = PRACTICE_TONES_HZ[:]
    rng.shuffle(tones)
    return tones


def make_block(rng):
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


def _truncexp_scale(mean_excess, width):
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
    q = S["JITTER_QUANTUM"]
    width = hi - lo
    s = _truncexp_scale(mean - lo, width)
    lo_s, hi_s = int(round(lo / q)), int(round(hi / q))
    steps = []
    for _ in range(n):
        u = rng.random()
        x = lo - s * math.log(1 - u * (1 - math.exp(-width / s)))
        steps.append(min(max(int(round(x / q)), lo_s), hi_s))
    target = int(round(n * mean / q))
    guard = 0
    while sum(steps) != target and guard < 100000:
        guard += 1
        k = rng.randrange(n)
        if sum(steps) < target and steps[k] < hi_s:
            steps[k] += 1
        elif sum(steps) > target and steps[k] > lo_s:
            steps[k] -= 1
    return [round(st * q, 3) for st in steps]


def new_block(pid):
    rng = random.Random()
    trials = make_block(rng)
    itis = sample_jitters(len(trials), S["ITI_MEAN"], S["ITI_MIN"], S["ITI_MAX"], rng)
    isis = sample_jitters(len(trials), S["ISI_MEAN"], S["ISI_MIN"], S["ISI_MAX"], rng)
    tones = tone_mapping(pid)
    return dict(tones_hz=tones, trials=[
        dict(shape=s, tone_idx=t, tone_hz=tones[t], is_match=m, iti=itis[i], isi=isis[i])
        for i, (s, t, m) in enumerate(trials)])


# --- Saving ------------------------------------------------------------------------------
def save_trial(d):
    pid = sanitize_id(d.get("participant", ""))
    if not pid:
        raise ValueError("missing participant ID")
    folder = os.path.join(S["DATA_DIR"], "sub-%s" % pid)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "sub-%s_practice.csv" % pid)

    match_key = S["MATCH_KEY"]
    is_match = int(d["is_match"])
    resp, late = d.get("response_key") or None, d.get("late_response_key") or None
    rt, late_rt = d.get("rt"), d.get("late_rt")
    presses = d.get("presses") or []
    tones = tone_mapping(pid)

    def label(k):
        return "" if k is None else ("match" if k == match_key else "nomatch")

    acc = "" if resp is None else int((resp == match_key) == bool(is_match))
    row = dict(
        participant=pid, block=int(d["block"]), trial=int(d["trial"]),
        shape=SHAPE_NAMES[int(d["shape"])], tone_hz=tones[int(d["tone_idx"])],
        is_match=is_match, correct_response="match" if is_match else "nomatch",
        response_status="on_time" if resp else ("late" if late else "none"),
        response_key=resp or "", response=label(resp),
        rt="" if rt is None else round(float(rt), 4), accuracy=acc, missed=int(resp is None),
        late_response_key=late or "", late_response=label(late),
        late_rt="" if late_rt is None else round(float(late_rt), 4),
        late_accuracy="" if late is None else int((late == match_key) == bool(is_match)),
        n_presses=len(presses),
        all_presses=";".join("%s@%.4f" % (k, float(t)) for t, k in presses),
        iti=round(float(d["iti"]), 3), isi=round(float(d["isi"]), 3),
        wall_time=datetime.datetime.now().isoformat(timespec="seconds"))

    with _write_lock:
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
            if new:
                w.writeheader()
            w.writerow(row)

    answer = "match" if is_match else "no match"
    given = "-" if resp is None else ("match" if resp == match_key else "no match")
    if resp is None:
        result = ("TOO SLOW (pressed at %.2f s)" % late_rt) if late else "TOO SLOW (no press)"
    else:
        result = "correct" if acc else "WRONG"
    print("  sub-%s b%d %2d  %-8s + %3d Hz   answer %-8s  response %-8s  RT %-5s  %s"
          % (pid, row["block"], row["trial"], row["shape"], row["tone_hz"], answer, given,
             "-" if rt is None else "%.2f" % float(rt), result), flush=True)


# --- Web server --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 200_000:
            raise ValueError("request too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            cfg = dict(STIM=S["STIM_DUR"], FB=S["FEEDBACK_DUR"], RW=S["RESPONSE_WINDOW"],
                       MATCH=S["MATCH_KEY"], NOMATCH=S["NOMATCH_KEY"],
                       MAX_BLOCKS=MAX_BLOCKS, VOLUME=TONE_VOLUME)
            return self._send(200, PAGE.replace("__CONFIG__", json.dumps(cfg)),
                              "text/html; charset=utf-8")
        img = {"/fb/correct.png": S["FEEDBACK_CORRECT_IMG"],
               "/fb/incorrect.png": S["FEEDBACK_INCORRECT_IMG"]}.get(path)
        if img and os.path.isfile(img):
            with open(img, "rb") as f:
                return self._send(200, f.read(), "image/png")
        self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            d = self._json()
            if self.path == "/api/start":
                pid = sanitize_id(d.get("participant", ""))
                if not pid:
                    return self._send(400, {"error": "Enter an ID using letters or digits."})
                existing = os.path.exists(os.path.join(
                    S["DATA_DIR"], "sub-%s" % pid, "sub-%s_practice.csv" % pid))
                print("\n=== sub-%s started%s ===" % (pid, " (file exists, appending)" if existing else ""),
                      flush=True)
                return self._send(200, {"participant": pid})
            if self.path == "/api/block":
                pid = sanitize_id(d.get("participant", ""))
                blk = new_block(pid)
                print("--- sub-%s PRACTICE block %s: %d trials | mapping: %s" % (
                    pid, d.get("block"), len(blk["trials"]),
                    ", ".join("%s = %d Hz" % (SHAPE_NAMES[i], blk["tones_hz"][i]) for i in range(3))),
                    flush=True)
                return self._send(200, blk)
            if self.path == "/api/trial":
                save_trial(d)
                return self._send(200, {"ok": True})
            if self.path == "/api/event":
                pid = sanitize_id(d.get("participant", ""))
                ev = str(d.get("event", ""))[:200]
                if ev == "block_end":
                    c, n = int(d.get("correct", 0)), int(d.get("n", 1))
                    print("sub-%s block %s: %d / %d correct (%.0f%%), %s too slow."
                          % (pid, d.get("block"), c, n, 100 * c / n, d.get("missed")), flush=True)
                    if c / n < GOOD_ACCURACY:
                        print("  -> below %.0f%% accuracy" % (100 * GOOD_ACCURACY), flush=True)
                else:
                    print("sub-%s: %s" % (pid, ev), flush=True)
                return self._send(200, {"ok": True})
            self._send(404, {"error": "not found"})
        except Exception as e:
            print("! error on %s: %s" % (self.path, e), flush=True)
            self._send(400, {"error": str(e)})


# --- Tunnel ------------------------------------------------------------------------------
def start_cloudflared(port):
    proc = subprocess.Popen(["cloudflared", "tunnel", "--no-autoupdate", "--url",
                             "http://localhost:%d" % port],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url, deadline = None, time.time() + 40
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if m:
            url = m.group(0)
            break
    threading.Thread(target=lambda: [None for _ in proc.stdout], daemon=True).start()
    return proc, url


def start_ngrok(port):
    proc = subprocess.Popen(["ngrok", "http", str(port), "--log", "stdout"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while time.time() < deadline:
        time.sleep(0.5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as r:
                for t in json.load(r).get("tunnels", []):
                    if t.get("public_url", "").startswith("https://"):
                        return proc, t["public_url"]
        except Exception:
            pass
    return proc, None


def main():
    ap = argparse.ArgumentParser(description="Online practice task with a public link.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--tunnel", choices=["auto", "cloudflared", "ngrok", "none"], default="auto")
    args = ap.parse_args()

    os.makedirs(S["DATA_DIR"], exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    local = "http://localhost:%d" % args.port
    for img in (S["FEEDBACK_CORRECT_IMG"], S["FEEDBACK_INCORRECT_IMG"]):
        if not os.path.isfile(img):
            print("Note: %s not found here; text feedback will be shown instead." % img)

    tool = args.tunnel
    if tool == "auto":
        tool = "cloudflared" if shutil.which("cloudflared") else (
            "ngrok" if shutil.which("ngrok") else "none")
        if tool == "none":
            print("\nNo tunnel tool found. Install one to get a public link:\n"
                  "  cloudflared: brew install cloudflared   (or see developers.cloudflare.com)\n"
                  "  ngrok:       https://ngrok.com/download")
    proc, url = None, None
    if tool != "none":
        if not shutil.which(tool):
            sys.exit("%s is not installed or not on your PATH." % tool)
        print("Starting %s tunnel..." % tool)
        proc, url = (start_cloudflared if tool == "cloudflared" else start_ngrok)(args.port)
        if not url:
            print("Could not get a public link from %s (check its setup)." % tool)

    print("\n" + "=" * 64)
    if url:
        print("  PARTICIPANT LINK:  %s" % url)
    print("  Local test link:   %s" % local)
    print("  Data folder:       %s" % os.path.abspath(S["DATA_DIR"]))
    print("  Keep this window open and the laptop awake. Ctrl+C to stop.")
    print("=" * 64 + "\n", flush=True)

    try:
        while True:
            time.sleep(1)
            if proc and proc.poll() is not None:
                print("! The tunnel stopped. Restart survey.py to get a new link.", flush=True)
                proc = None
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.shutdown()
        if proc:
            proc.terminate()


# --- The page participants see -------------------------------------------------------------
PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Practice task</title>
<style>
  :root { --bg:#808080; --ink:#ffffff; --soft:#e6e6e6; --field:#6f6f6f; --line:#a6a6a6; --warn:#ffe066; }
  * { box-sizing:border-box; }
  html,body { margin:0; height:100%; background:var(--bg); color:var(--ink);
    font-family: Arial, Helvetica, sans-serif; }
  #stage { position:fixed; inset:0; display:none; cursor:none; }
  #screen { min-height:100%; display:flex; align-items:center; justify-content:center; padding:2rem; }
  .panel { max-width:36rem; width:100%; line-height:1.5; font-size:1.05rem; }
  h1 { font-size:1.6rem; font-weight:normal; margin:0 0 1rem; }
  p { margin:0 0 .9rem; }
  ul { margin:0 0 1.2rem; padding-left:1.2rem; }
  label { display:block; margin:1.2rem 0 .4rem; }
  input { font:inherit; font-size:1.2rem; padding:.55rem .7rem; width:100%; color:var(--ink);
    background:var(--field); border:1px solid var(--line); border-radius:4px; }
  button { font:inherit; padding:.6rem 1.1rem; margin:.4rem .5rem 0 0; color:#333; background:var(--soft);
    border:0; border-radius:4px; cursor:pointer; }
  button:focus-visible, input:focus-visible { outline:3px solid var(--warn); outline-offset:2px; }
  .err { color:var(--warn); min-height:1.5em; margin-top:.6rem; }
  .msg { text-align:center; white-space:pre-line; font-size:1.25rem; line-height:1.55; max-width:44rem; }
  kbd { border:1px solid var(--line); border-radius:3px; padding:0 .35em; }
</style></head>
<body>
<div id="screen"><div class="panel" id="intro">
  <h1>Practice: shapes and sounds</h1>
  <p>Before you start, please make sure:</p>
  <ul>
    <li>you are on a computer with a keyboard (not a phone or tablet)</li>
    <li>you are wearing headphones, in a quiet room</li>
    <li>you can spend about 5–10 minutes without interruptions</li>
  </ul>
  <button id="testTone" type="button">Play test sound</button>
  <p style="margin-top:.6rem">Set your volume so the test sound is clear and comfortable.</p>
  <label for="pid">Participant ID</label>
  <input id="pid" autocomplete="off" autocapitalize="off" spellcheck="false">
  <div class="err" id="err"></div>
  <button id="start" type="button">Start practice</button>
</div></div>
<canvas id="stage"></canvas>
<script>
const CFG = __CONFIG__;
const BG = "#808080", SHAPE = "#e0e0e0";
const screenEl = document.getElementById("screen"), canvas = document.getElementById("stage");
const ctx2d = canvas.getContext("2d");
let audio = null, PID = null, keyHandler = null, quitting = false;
const unsent = [];

const fbImg = {};
for (const k of ["correct", "incorrect"]) {
  const im = new Image(); im.onload = () => fbImg[k] = im; im.src = "/fb/" + k + ".png";
}

function ensureAudio() {
  if (!audio) audio = new (window.AudioContext || window.webkitAudioContext)();
  if (audio.state === "suspended") audio.resume();
}
function playTone(hz, secs) {
  const t0 = audio.currentTime + 0.005, ramp = 0.01;
  const osc = audio.createOscillator(), g = audio.createGain();
  osc.frequency.value = hz;
  g.gain.setValueAtTime(0, t0);
  g.gain.linearRampToValueAtTime(CFG.VOLUME, t0 + ramp);
  g.gain.setValueAtTime(CFG.VOLUME, t0 + secs - ramp);
  g.gain.linearRampToValueAtTime(0, t0 + secs);
  osc.connect(g).connect(audio.destination);
  osc.start(t0); osc.stop(t0 + secs + 0.02);
}

async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || ("Server error " + r.status));
  return j;
}
async function saveTrial(row) {
  for (let i = 0; i < 4; i++) {
    try { await post("/api/trial", row); return; } catch (e) { await sleepMs(500 * (i + 1)); }
  }
  unsent.push(row);
}
const sleepMs = ms => new Promise(r => setTimeout(r, ms));
const event = (ev, extra = {}) => post("/api/event", { participant: PID, event: ev, ...extra }).catch(() => {});

// ---- drawing (PsychoPy "height" units: 1 = window height, origin at centre) ----
function resize() {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr;
  canvas.style.width = innerWidth + "px"; canvas.style.height = innerHeight + "px";
}
addEventListener("resize", resize);
function clear() { ctx2d.fillStyle = BG; ctx2d.fillRect(0, 0, canvas.width, canvas.height); }
const U = u => u * canvas.height, cx = () => canvas.width / 2, cy = () => canvas.height / 2;
function drawText(txt, h, color) {
  clear(); ctx2d.fillStyle = color; ctx2d.textAlign = "center"; ctx2d.textBaseline = "middle";
  ctx2d.font = Math.round(U(h) * 1.35) + "px Arial, Helvetica, sans-serif";
  ctx2d.fillText(txt, cx(), cy());
}
const drawFix = () => drawText("+", 0.07, "white");
function drawShape(i) {
  clear(); ctx2d.fillStyle = SHAPE; ctx2d.beginPath();
  if (i === 0) ctx2d.arc(cx(), cy(), U(0.12), 0, 2 * Math.PI);
  else if (i === 1) ctx2d.rect(cx() - U(0.11), cy() - U(0.11), U(0.22), U(0.22));
  else {
    const r = U(0.15);
    for (let k = 0; k < 3; k++) {
      const a = -Math.PI / 2 + k * 2 * Math.PI / 3;
      ctx2d[k ? "lineTo" : "moveTo"](cx() + r * Math.cos(a), cy() + r * Math.sin(a));
    }
    ctx2d.closePath();
  }
  ctx2d.fill();
}
function drawFb(kind) {
  if (kind === "missed") return drawText("Too slow!", 0.06, "yellow");
  if (fbImg[kind]) { clear(); const s = U(0.15); ctx2d.drawImage(fbImg[kind], cx() - s / 2, cy() - s / 2, s, s); return; }
  drawText(kind === "correct" ? "Correct" : "Incorrect", 0.06, kind === "correct" ? "#2ecc40" : "#ff4136");
}

// ---- keys ----
function keyName(e) {
  if (e.code === "Digit7" || e.code === "Numpad7" || e.key === "7") return "7";
  if (e.code === "Digit4" || e.code === "Numpad4" || e.key === "4") return "4";
  if (e.key === " " || e.code === "Space") return "space";
  if (e.key === "r" || e.key === "R") return "r";
  if (e.key === "Escape") return "escape";
  return null;
}
document.addEventListener("keydown", e => {
  if (!PID || e.repeat) return;
  const k = keyName(e);
  if (!k) return;
  e.preventDefault();
  if (k === "escape") return quit();
  if (keyHandler) keyHandler(k, e.timeStamp);
});

// ---- screens ----
function message(text, keys) {
  canvas.style.display = "none"; screenEl.style.display = "flex"; screenEl.style.cursor = "none";
  screenEl.innerHTML = '<div class="msg"></div>';
  screenEl.firstChild.textContent = text;
  return new Promise(res => { keyHandler = k => { if (keys.includes(k)) { keyHandler = null; res(k); } }; });
}
function showStage() { screenEl.style.display = "none"; canvas.style.display = "block"; resize(); }
function fixFor(secs) {
  return new Promise(res => {
    const t0 = performance.now();
    (function f() { if (quitting) return; drawFix();
      if (performance.now() - t0 >= secs * 1000) res(); else requestAnimationFrame(f); })();
  });
}

function runTrial(tr, nextIti) {
  const fbOn = CFG.STIM + tr.isi, end = fbOn + CFG.FB + nextIti;
  let onset = null, resp = null, rt = null, late = null, lateRt = null, fb = null;
  const presses = [];
  keyHandler = (k, ts) => {
    if (onset === null || (k !== "4" && k !== "7")) return;
    const t = (ts - onset) / 1000;
    if (t < 0) return;
    presses.push([+t.toFixed(4), k]);
    if (resp === null && t <= CFG.RW) { resp = k; rt = t; }
    else if (resp === null && late === null && t < fbOn) { late = k; lateRt = t; }
  };
  return new Promise(res => {
    function frame(ts) {
      if (quitting) return;
      if (onset === null) {               // stimulus onset: shape drawn + tone started together
        drawShape(tr.shape); playTone(tr.tone_hz, CFG.STIM); onset = ts;
        return requestAnimationFrame(frame);
      }
      const now = (performance.now() - onset) / 1000;
      if (now >= end) { keyHandler = null; return res({ resp, rt, late, lateRt, presses }); }
      if (now < CFG.STIM) drawShape(tr.shape);
      else if (now < fbOn) drawFix();
      else if (now < fbOn + CFG.FB) {
        if (fb === null) fb = resp === null ? "missed"
          : ((resp === CFG.MATCH) === !!tr.is_match ? "correct" : "incorrect");
        drawFb(fb);
      } else drawFix();
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  });
}

async function runBlock(block) {
  const blk = await post("/api/block", { participant: PID, block });
  const T = blk.trials;
  showStage();
  await fixFor(T[0].iti);
  let correct = 0, missed = 0;
  for (let i = 0; i < T.length; i++) {
    const tr = T[i], nextIti = i + 1 < T.length ? T[i + 1].iti : 1.0;
    const r = await runTrial(tr, nextIti);
    if (r.resp === null) missed++;
    else if ((r.resp === CFG.MATCH) === !!tr.is_match) correct++;
    saveTrial({ participant: PID, block, trial: i + 1, shape: tr.shape, tone_idx: tr.tone_idx,
      is_match: tr.is_match, response_key: r.resp, rt: r.rt, late_response_key: r.late,
      late_rt: r.lateRt, presses: r.presses, iti: tr.iti, isi: tr.isi });
  }
  event("block_end", { block, correct, n: T.length, missed });
  return [correct, T.length];
}

async function finish(text) {
  await sleepMs(800);   // let the last trial's save finish
  canvas.style.display = "none"; screenEl.style.display = "flex"; screenEl.style.cursor = "auto";
  screenEl.innerHTML = '<div class="msg"></div>';
  screenEl.firstChild.textContent = text;
  if (unsent.length) {
    const p = document.createElement("p");
    p.style.marginTop = "1.5rem";
    p.textContent = "Some responses could not be sent. Please download this file and email it to the researcher: ";
    const a = document.createElement("a");
    a.textContent = "download responses"; a.style.color = "#ffe066";
    a.href = URL.createObjectURL(new Blob([JSON.stringify(unsent)], { type: "application/json" }));
    a.download = "sub-" + PID + "_practice_unsent.json";
    p.appendChild(a); screenEl.firstChild.appendChild(p);
  }
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
}
function quit() {
  if (quitting) return;
  quitting = true; keyHandler = null;
  event("quit (Escape)");
  finish("You stopped the practice.\n\nYour responses so far have been saved. You can close this tab.");
}

async function run() {
  const M = CFG.MATCH, N = CFG.NOMATCH;
  await message("PRACTICE\n\nYou will see a SHAPE and hear a SOUND at the same time.\n\n" +
    "Some shapes and sounds are a MATCH and some DO NOT MATCH.\n\n" +
    "If you think they MATCH, press " + M + " on your keyboard.\n" +
    "If you think they do NOT match, press " + N + " on your keyboard.\n\n" +
    "Try to answer as FAST AS POSSIBLE.\n\n" +
    "After a short pause you will see whether you were right or wrong. " +
    "Please try to remember the MATCHED pairings.\n\nPress " + M + " or " + N + " to continue.",
    [M, N, "space"]);
  await message("The task is about to begin.\n\nMATCH = " + M + "\nNO MATCH = " + N +
    "\n\nPress " + M + " or " + N + " to begin.", [M, N, "space"]);
  let block = 1;
  while (!quitting) {
    const [c, n] = await runBlock(block);
    if (quitting) return;
    if (block >= CFG.MAX_BLOCKS) {
      await message("You got " + c + " out of " + n + " correct.\n\nPress SPACE to continue.", ["space"]);
      break;
    }
    const choice = await message("You got " + c + " out of " + n + " correct.\n\n" +
      "Press R to practise once more, or SPACE to finish.", ["space", "r"]);
    if (choice === "space") break;
    block++;
    await message("Let's practise once more.\n\nMATCH = " + M + "\nNO MATCH = " + N +
      "\n\nPress " + M + " or " + N + " to begin.", [M, N, "space"]);
  }
  if (quitting) return;
  event("finished after " + block + " block(s)");
  quitting = true;
  finish("Practice finished. Well done!\n\nIn the scanner you will see NEW shapes and sounds, " +
    "but the task and the buttons are the same.\n\nYou can close this tab now.");
}

document.getElementById("testTone").onclick = () => { ensureAudio(); playTone(523, 1.0); };
document.getElementById("start").onclick = async () => {
  const err = document.getElementById("err");
  err.textContent = "";
  if (matchMedia("(pointer: coarse)").matches && !matchMedia("(pointer: fine)").matches) {
    err.textContent = "This task needs a computer with a keyboard. Please open the link on a laptop or desktop.";
    return;
  }
  const raw = document.getElementById("pid").value.trim();
  if (!raw) { err.textContent = "Enter your participant ID to start."; return; }
  ensureAudio();
  try {
    PID = (await post("/api/start", { participant: raw })).participant;
  } catch (e) { err.textContent = e.message; return; }
  try { await document.documentElement.requestFullscreen(); } catch (e) {}
  run();
};
document.getElementById("pid").addEventListener("keydown", e => {
  if (e.key === "Enter") document.getElementById("start").click();
});
</script>
</body></html>
"""

if __name__ == "__main__":
    main()
