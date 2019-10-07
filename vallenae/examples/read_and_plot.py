import matplotlib.pyplot as plt
import matplotlib
import os
import vallenae.core as vae
import vallenae.helper as vh

# Set this to false in order to look a little
# longer at the popup plots:
matplotlib.interactive(False)  # "True" means makes plt.show() is non-blocking


if __name__ == '__main__':

    THIS_FILE_PATH = os.path.dirname(os.path.realpath(__file__))
    PLAIN_FNAME = os.path.join(THIS_FILE_PATH, 'steel_plate/sample.tradb')
    FLAC_FNAME = os.path.join(THIS_FILE_PATH, 'steel_plate/sample_plain.tradb')
    tra_frame_flac = vae.read_tra(PLAIN_FNAME, 1, 100)
    tra_frame_plain = vae.read_tra(FLAC_FNAME, 1, 100)
    tra_idx = 4  # just an example, no magic here

    ys1, xs = vae.extract_wave(tra_frame_flac, tra_idx)
    ys1 = ys1 * 1000  # in mV
    xs = xs * 1000000  # for µs
    ys2, _ = vae.extract_wave(tra_frame_plain, tra_idx)
    ys2 = ys2 * 1000  # in mV

    _, ax = plt.subplots()
    ax.set_xlabel('Time [us]')
    ax.set_ylabel('Tansient Wave [mV]', color='g')
    ax.plot(xs, ys1)
    plt.title('Transient Wave Plot From FLAC BLOB; TRAI=' + str(tra_idx))
    plt.show()
    vh.save_figure(THIS_FILE_PATH, 'ignore_me_from_flac', 'png')
    plt.close()

    _, ax = plt.subplots()
    ax.set_xlabel('Time [us]')
    ax.set_ylabel('Tansient Wave [mV]', color='g')
    ax.plot(xs, ys2)
    plt.title('Transient Wave Plot From Plain BLOB; TRAI=' + str(tra_idx))
    plt.show()
    vh.save_figure(THIS_FILE_PATH, 'ignore_me_from_plain', 'png')
    plt.close()
