from __future__ import print_function, division, absolute_import
import math as m
import matplotlib.pyplot as plt
import matplotlib
import numba as nb
from numba import jit, f8, i4
import numpy as np
import os
from typing import Tuple
import time
import vallenae.core as vae

# Set this to false in order to look a little
# longer at the popup plots:
matplotlib.interactive(False)  # "True" means plt.show() is non-blocking


@jit(nb.types.Tuple((f8[:], f8, i4))(f8[:], i4))
def energy_ratio(arr: np.ndarray,
                 win_len: int = 100)\
        -> Tuple[np.ndarray, float, int]:
    safetye_eps = 1e-6
    n = len(arr)
    er_vals = np.zeros(n)
    l_sumsq = 0.0
    r_sumsq = 0.0
    min_val = m.inf
    min_idx = 0
    for k in range(0, win_len):
        l_sumsq += arr[k]**2
    for k in range(win_len, win_len+win_len):
        r_sumsq += arr[k]**2
    for k in range(win_len, n-win_len):
        l_sumsq += arr[k]**2
        r_sumsq += arr[k+win_len]**2
        l_sumsq -= arr[k-win_len]**2
        r_sumsq -= arr[k]**2
        er_vals[k] = r_sumsq / (safetye_eps + l_sumsq)
        if er_vals[k] < min_val:
            min_val = er_vals[k]
            min_idx = k
    return er_vals, min_val, min_idx


if __name__ == '__main__':

    THIS_FILE_PATH = os.path.dirname(os.path.realpath(__file__))

    MAX_TRA_IDX = 4
    END_SAMPLE = 2000
    WINDOW_LEN = 100
    CONVERT_SECS_2_USECS = 1000000

    tra_frame = vae.read_tra(
        os.path.join(
            THIS_FILE_PATH, 'steel_plate/sample_plain.tradb'), 1, MAX_TRA_IDX)
    ys, xs = vae.extract_wave(tra_frame, MAX_TRA_IDX, do_convert2v=True)
    ys = ys * 1000  # convert to mV

    # Try this without numba/jit to see the performance difference:
    # -------------------------------------------------------------
    start = time.perf_counter()
    er_arr, _, _ = energy_ratio(ys, WINDOW_LEN)
    end = time.perf_counter()
    print('Runtime for 1 call to energy_ratio(): ', end - start)
    # -------------------------------------------------------------

    # Code taken from the matplotlib documentation:
    fig, ax1 = plt.subplots()
    ax1.set_xlabel('Time [us]')
    ax1.set_ylabel('Tansient Wave [mV]', color='g')
    ax1.plot(CONVERT_SECS_2_USECS * xs[0:END_SAMPLE],
             ys[0:END_SAMPLE],
             color='g')
    ax1.tick_params(axis='y', labelcolor='g')
    ax2 = ax1.twinx()

    ax2.set_ylabel('Energy Ratio [/]', color='r')
    ax2.plot(CONVERT_SECS_2_USECS * xs[0:END_SAMPLE],
             er_arr[0:END_SAMPLE],
             color='r')
    ax2.tick_params(axis='y', labelcolor='r')

    fig.tight_layout()
    plt.show()
