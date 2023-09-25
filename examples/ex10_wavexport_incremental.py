"""
Export to WAV (incremental)
===========================

Generate WAV files from tradb. We use the `vallenae.io.TraDatabase.read_continuous_wave` method to
read the transient data as a continuous array.

This example reads and writes the data incrementally to handle big file sizes that don't fit into
memory at once.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import vallenae as vae
from soundfile import SoundFile

HERE = Path(__file__).parent if "__file__" in locals() else Path.cwd()


def export_wav_incremental(
    filename_wav: Path,
    tradb: vae.io.TraDatabase,
    channel: int,
    time_start: Optional[float] = None,
    time_stop: Optional[float] = None,
    time_block: int = 1,
):
    """
    Export data from tradb to a WAV file.

    Args:
        filename_wav: Path to the generated WAV file
        tradb: `TraDatabase` instance
        channel: Channel number
        time_start: Start reading at relative time (in seconds). Start at beginning if `None`
        time_start: Stop reading at relative time (in seconds). Read until end if `None`
        time_block: Block size in seconds
    """
    con = tradb.connection()
    if time_start is None:
        time_start = 0
    if time_stop is None:
        time_stop = con.execute("SELECT MAX(Time) FROM view_tr_data").fetchone()[0]

    samplerates = con.execute("SELECT DISTINCT(SampleRate) FROM tr_data").fetchone()
    assert len(samplerates) == 1
    samplerate = samplerates[0]

    blocks = int((time_stop - time_start) // time_block + 1)
    with SoundFile(filename_wav, "w", samplerate=samplerate, channels=1, subtype="PCM_16") as f:
        for block in range(blocks):
            time_block_start = time_start + block * time_block
            time_block_stop = min(time_start + (block + 1) * time_block, time_stop)
            y, _ = tradb.read_continuous_wave(
                channel=channel,
                time_start=time_block_start,
                time_stop=time_block_stop,
                time_axis=False,
                show_progress=False,
                raw=True,  # read as ADC values (int16)
            )
            f.write(y)
            f.flush()


def main():
    filename_tradb = HERE / "bearing" / "bearing_plain.tradb"
    # use a temporary file for this example
    with TemporaryDirectory() as tmpdir:
        with vae.io.TraDatabase(filename_tradb) as tradb:
            for channel in tradb.channel():
                filename_wav = Path(tmpdir) / f"{filename_tradb.stem}_ch{channel}.wav"
                print(f"Export channel {channel} to {filename_wav}")
                export_wav_incremental(
                    filename_wav=filename_wav,
                    tradb=tradb,
                    channel=channel,
                    time_start=0,  # read from t = 0 s
                    time_stop=None,  # read until end if None
                    time_block=1,  # read/write in block sizes of 1 s
                )

        # list all generated wav files
        print("Generated WAV files:")
        for file in Path(tmpdir).iterdir():
            print(file)


if __name__ == "__main__":
    main()
