import sys, os

# find vallenae module in parent directory if not installed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import math
import matplotlib.pyplot as plt
from numba import jit, f8
import numpy as np
from numpy.linalg import norm
from numpy import arange
from scipy.optimize import differential_evolution
import time
import vallenae.core as vae
import xml.etree.ElementTree as ElementTree


@jit(f8(f8[:], f8, f8[:, :], f8[:]))
def lucy_error_fun(
    test_pos: np.ndarray,
    speed: float,
    sens_poss: np.ndarray,
    measured_delta_ts: np.ndarray,
) -> float:
    """
    This is an implementation of the LUCY computation in 2D as documented in
    the Vallen online help

    :param test_pos: Emitter position to test.
    :param speed: Assumed speed of sound in a plate-like structure.
    :param sens_poss: Sensor positions, often a 4x2 array, has to match
        the sorting of the delta-ts.
    :param measured_delta_ts: The measured time differences in seconds, has to
        match the order of the sensor positions.
    :returns: The LUCY value as a float. Ideally 0, in practice never 0,
        always positive.
    """
    m = len(measured_delta_ts)
    n = m + 1
    measured_delta_dists = speed * measured_delta_ts
    theo_dists = np.zeros(n)
    theo_delta_dists = np.zeros(m)
    for i in range(n):
        theo_dists[i] = norm(test_pos - sens_poss[i, :])
    for i in range(m):
        theo_delta_dists[i] = theo_dists[i + 1] - theo_dists[0]

    # LUCY definition taken from the vallen online help:
    lucy_val = norm(theo_delta_dists - measured_delta_dists) / math.sqrt(n - 1)
    return lucy_val


if __name__ == "__main__":

    this_file_path = os.path.dirname(os.path.realpath(__file__))
    huge_int = int(1e6)
    set_type_hit = 2
    nb_sensors = 4
    location_dimension = 2
    text_delta_y = 0.03
    text_delta_x = -0.12
    grid_delta = 0.01
    location_search_bounds = [(0.0, 0.80), (0.0, 0.80)]

    pridb_path = os.path.join(this_file_path, "steel_plate/sample.pridb")
    pri_frame = vae.read_pri(pridb_path, 1, huge_int)
    pri_hits = pri_frame[pri_frame["SetType"] == set_type_hit]

    arrival_times = []
    chan_order = []
    for index, row in pri_hits.iterrows():
        arrival_times.append(row["Time"])
        chan_order.append(int(row["Chan"] - 1))
    times = np.array(arrival_times)
    delta_ts = (times - times[0])[1:]

    tree = ElementTree.parse(os.path.join(this_file_path, "steel_plate/sample.vaex"))
    root = tree.getroot()

    xml_chans = root.findall(".//ChannelPos")
    unordered_sens_poss = np.zeros((nb_sensors, location_dimension))
    ordered_sens_poss = np.zeros((nb_sensors, location_dimension))
    for i, elem in enumerate(xml_chans):
        unordered_sens_poss[i, :] = [float(elem.get("X")), float(elem.get("Y"))]
    ordered_sens_poss = unordered_sens_poss[chan_order, :]

    speed_str = root.find(".//Location").get("Velocity")
    speed_m_per_s = float(speed_str) * 1000

    # Heatmap computation:
    # -------------------
    lucy_instance_2args = lambda x, y: lucy_error_fun(
        np.array([x, y]), speed_m_per_s, ordered_sens_poss, delta_ts
    )

    x_range = arange(
        location_search_bounds[0][0], location_search_bounds[0][1], grid_delta
    )
    y_range = x_range
    X, Y = np.meshgrid(x_range, y_range)
    Z = np.vectorize(lucy_instance_2args)(X, Y)
    plt.pcolormesh(X, Y, Z, cmap="cool")
    plt.colorbar()
    plt.title("Location Result and LUCY-Heatmap")
    plt.xlabel("x-coordinate [m]")
    plt.ylabel("y-coordinate [m]")
    # -----------------

    # Location computation
    # --------------------
    lucy_instance_single_arg = lambda pos: lucy_error_fun(
        pos, speed_m_per_s, ordered_sens_poss, delta_ts
    )

    start = time.perf_counter()
    # these are excessive search / overkill parameters:
    location_result = differential_evolution(
        lucy_instance_single_arg,
        location_search_bounds,
        popsize=40,
        polish=True,
        strategy="rand1bin",
        recombination=0.1,
        mutation=1.3,
    )

    end = time.perf_counter()
    print("Runtime for 1 call to differential_evolution(): ", end - start)
    print(location_result)

    x_res = location_result.x[0]
    y_res = location_result.x[1]
    plt.plot([x_res], [y_res], "bo")
    plt.text(
        x_res + text_delta_x,
        y_res + text_delta_y,
        "location result",
        fontsize=9,
        color="b",
    )
    # --------------------

    # Plotting the sensor positions:
    # ------------------------------
    sens_txts = [
        "S1 (x=0.6m | y=0.6m)",
        "S2 (x=0.15m | y=0.6m)",
        "S3 (x=0.15m | y=0.15m)",
        "S4 (x=0.6m | y=0.15m)",
    ]
    for i, sens_txt in enumerate(sens_txts):
        x = unordered_sens_poss[i, 0]
        y = unordered_sens_poss[i, 1]
        plt.scatter(x, y, marker="o", color="w")
        plt.text(x + text_delta_x, y + text_delta_y, sens_txt, fontsize=9, color="w")
    # ------------------------------

    plt.show()
