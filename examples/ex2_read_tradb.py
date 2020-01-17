"""
Read and plot transient data
============================
"""

import os
import matplotlib.pyplot as plt

import vallenae as vae


HERE = os.path.dirname(__file__) if "__file__" in locals() else os.getcwd()
TRADB_FLAC = os.path.join(HERE, "steel_plate/sample_plain.tradb")
TRADB_PLAIN = os.path.join(HERE, "steel_plate/sample.tradb")
TRAI = 4  # just an example, no magic here

plt.ioff()  # Turn interactive mode off; plt.show() is blocking


def main():
    # Read waveform from uncompressed and FLAC-compressed tradb
    with vae.io.TraDatabase(TRADB_PLAIN) as tradb:
        y1, t = tradb.read_wave(TRAI)
    with vae.io.TraDatabase(TRADB_FLAC) as tradb:
        y2, t = tradb.read_wave(TRAI)

    y1 *= 1e3  # in mV
    y2 *= 1e3  # in mV
    t *= 1e6  # for µs

    # Plot waveforms
    _, (ax1, ax2) = plt.subplots(2, sharex="all", sharey="all", tight_layout=True)
    ax1.plot(t, y1)
    ax2.plot(t, y2)
    ax2.set_xlabel("Time [µs]")
    ax1.set_ylabel("Amplitude [mV]")
    ax2.set_ylabel("Amplitude [mV]")
    ax1.set_title("Transient Wave Plot from PLAIN BLOB; TRAI=" + str(TRAI))
    ax2.set_title("Transient Wave Plot from FLAC BLOB; TRAI=" + str(TRAI))
    plt.show()


if __name__ == "__main__":
    main()
