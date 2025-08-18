import numpy as np
import matplotlib.pyplot as plt
import os
import json
from scipy.interpolate import CubicSpline  # Replace interp1d
import pandas as pd

# ---------------- SETTINGS -----------------
SAVE_DIR = "generated_associated_shapes"
os.makedirs(SAVE_DIR, exist_ok=True)

RANDOM_SEED = 42  # <<<<<<<< Add this line for reproducibility

np.random.seed(RANDOM_SEED)  # Set global random seed for reproducibility

n_shapes = 10  # Updated to generate 10 shapes
image_size = 4
resolution = 600
color = "black"
FREE