"""
Export to WAV
=============

Generate WAV files from tradb. We use the `vallenae.io.TraDatabase.read_continuous_wave` method to
read the transient data as a continuous array.

The signal can optionally be decimated to reduce the size of the generated WAV files
(using the `scipy.signal.decimate` function).
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import numpy as np
import vallenae as vae
from scipy import signal
from scipy.io import wavfile

HERE = Path(__file__).parent if "__file__" in locals() else Path.cwd()


def export_wav(
    filename_wav: Path,
    tradb: vae.io.TraDatabase,
    channel: int,
    time_start: Optional[float] = None,
    time_stop: Optional[float] = None,
    decimation_factor: int = 1,
):
    """
    Export data from tradb to a WAV file.

    Args:
        filename_wav: Path to the generated WAV file
        tradb: `TraDatabase` instance
        channel: Channel number
        time_start: Start reading at relative time (in seconds). Start at beginning if `None`
        time_start: Stop reading at relative time (in seconds). Read until end if `None`
        decimation_factor: Decimate signal with given factor
    """
    y, fs = tradb.read_continuous_wave(
        channel=channel,
        time_start=time_start,
        time_stop=time_stop,
        time_axis=False,
        show_progress=False,
        raw=True,  # read as ADC values (int16)
    )

    if decimation_factor > 1:
        y = signal.decimate(y, decimation_factor).astype(np.int16)
        fs //= decimation_factor

    wavfile.write(filename_wav, fs, y)


def main():
    filename_tradb = HERE / "bearing" / "bearing_plain.tradb"

    # use a temporary file for this example
    with TemporaryDirectory() as tmpdir:
        with vae.io.TraDatabase(filename_tradb) as tradb:
            for channel in tradb.channel():
                filename_wav = Path(tmpdir) / f"{filename_tradb.stem}_ch{channel}.wav"
                print(f"Export channel {channel} to {filename_wav}")
                export_wav(
                    filename_wav=filename_wav,
                    tradb=tradb,
                    channel=channel,
                    time_start=0,  # read from t = 0 s
                    time_stop=None,  # read until end if None
                    decimation_factor=5,  # custom decimation factor
                )

        # list all generated wav files
        print("Generated WAV files:")
        for file in Path(tmpdir).iterdir():
            print(file)


if __name__ == "__main__":
    main()
