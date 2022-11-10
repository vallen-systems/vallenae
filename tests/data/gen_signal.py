from pathlib import Path

import numpy as np

SIGNALFILE = Path(__file__).resolve().parent / "signal.txt"
SAMPLES = 1024
FS = int(10e6)
DT_NS = 1e9 / FS

if __name__ == "__main__":
    signal = 2 * np.random.rand(SAMPLES) - 1

    with open(SIGNALFILE, mode="w", encoding="utf-8") as f:
        f.write(f"{DT_NS:f}\n")
        f.write(f"{SAMPLES:d}\n")

        for value in signal:
            f.write(f"{value:f}\n")
