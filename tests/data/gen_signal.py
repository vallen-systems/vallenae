from pathlib import Path
import numpy as np

SIGNALFILE = Path(__file__).resolve().parent / "signal.txt"
SAMPLES = 1024
FS = int(10e6)
DT_NS = 1e9 / FS

if __name__ == "__main__":
    signal = 2 * np.random.rand(SAMPLES) - 1
    
    with open(SIGNALFILE, "w") as f:
        f.write("{:f}\n".format(DT_NS))
        f.write("{:d}\n".format(SAMPLES))
        
        for value in signal:
            f.write("{:f}\n".format(value))
