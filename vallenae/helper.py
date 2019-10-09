import matplotlib.pyplot as plt
import os
from typing import Union, Tuple


def cm2inch(x_cm: float, y_cm: float = None) -> Union[Tuple[float, float], float]:
    """
    Convert cm to inch. Cartesian coordinates are possible, therefore two
    arguments, e.g. like
      v_cm = (x, y)
      v_inch = cm2inch(*v_cm)

    :param x_cm: x-coordinate in cm
    :param y_cm: y-coordinate in cm
    :returns A tuple of the corresponding coordinates in inch units.
    """
    fac = 1 / 2.54
    if y_cm:
        return fac * x_cm, fac * y_cm
    else:
        return fac * x_cm


def save_figure(
    image_dir: str, file_name: str, file_ending: str = "png", dpi: int = 300
) -> None:
    """
    Just saves the figure to the specified directory.
    Use it after some call to matplotlib.pyplot.plot(...)

    :param image_dir: Here the image file should be saved.
    :param file_name: The name of the file without file ending.
    :param file_ending: The file-ending; determines the file format.
    Should be one of {'png', 'pdf', 'eps'}.
    :param dpi: dips per inch of the graphic to be saved. Defaults to 300.
    """
    try:
        file_path = os.path.join(image_dir, file_name + "." + file_ending)
        plt.savefig(file_path, format=file_ending, dpi=dpi)
    except Exception as e:
        raise e
    else:
        print("Saved figure " + file_ending, file_name)
    return None


def assert_coll(coll):
    try:
        iter(coll)
    except TypeError:
        raise AssertionError("is not iterable")


def assert_string_coll(coll):

    try:
        iter(coll)
    except TypeError:
        raise AssertionError("is not iterable")
    assert type(coll) is list
    for item in coll:
        assert type(item) is str


def assert_int_coll(some_list):
    assert type(some_list) is list
    for item in some_list:
        assert type(item) is int


def assert_int_paris_coll(some_list):
    assert type(some_list) is list
    for sublist in some_list:
        assert type(sublist) is list
        assert len(sublist) == 2
        for item in sublist:
            assert type(item) is int
