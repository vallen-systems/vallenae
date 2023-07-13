"""
Localisation
============
"""

import math
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from xml.etree import ElementTree

import matplotlib.pyplot as plt
import numpy as np
import vallenae as vae
from numba import f8, njit
from numpy.linalg import norm
from scipy.optimize import differential_evolution

HERE = Path(__file__).parent if "__file__" in locals() else Path.cwd()
PRIDB = HERE / "steel_plate" / "sample.pridb"
SETUP = HERE / "steel_plate" / "sample.vaex"
NUMBER_SENSORS = 4


@njit(f8(f8[:], f8, f8[:, :], f8[:]))
def lucy_error_fun(
    test_pos: np.ndarray,
    speed: float,
    sens_poss: np.ndarray,
    measured_delta_ts: np.ndarray,
) -> float:
    """
    Implementation of the LUCY computation in 2D as documented in
    the Vallen online help.

    Args:
        test_pos: Emitter position to test.
        speed: Assumed speed of sound in a plate-like structure.
        sens_poss: Sensor positions, often a 4x2 array, has to match
            the sorting of the delta-ts.
        measured_delta_ts: The measured time differences in seconds, has to
            match the order of the sensor positions.

    Returns:
        The LUCY value as a float. Ideally 0, in practice never 0, always positive.
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
    return norm(theo_delta_dists - measured_delta_dists) / math.sqrt(n - 1)


def get_channel_positions(setup_file: str) -> Dict[int, Tuple[float, float]]:
    tree = ElementTree.parse(setup_file)
    nodes = tree.getroot().findall(".//ChannelPos")
    if nodes is None:
        raise RuntimeError("Can not retrieve channel positions from %s", setup_file)
    return {
        int(elem.get("Chan")): (float(elem.get("X")), float(elem.get("Y")))  # type: ignore
        for elem in nodes if elem is not None
    }


def get_velocity(setup_file: str) -> Optional[float]:
    tree = ElementTree.parse(setup_file)
    node = tree.getroot().find(".//Location")
    if node is not None:
        velocity_str = node.get("Velocity")
        if velocity_str is not None:
            return float(velocity_str) * 1e3  # convert to m/s
    raise RuntimeError("Can not retrieve velocity from %s", setup_file)


def main():
    # Consts plotting
    text_delta_y = 0.03
    text_delta_x = -0.12

    # Consts LUCY grid
    grid_delta = 0.01
    location_search_bounds = [(0.0, 0.80), (0.0, 0.80)]

    # Read from pridb
    pridb = vae.io.PriDatabase(PRIDB)
    hits = pridb.read_hits()
    pridb.close()

    channel_order = hits["channel"].to_numpy()
    arrival_times = hits["time"].to_numpy()
    delta_ts = (arrival_times - arrival_times[0])[1:]

    # Get localisation parameters from .vaex file
    velocity = get_velocity(SETUP)
    pos_dict = get_channel_positions(SETUP)

    # Order sensor positions by hit occurence
    pos_ordered = np.array([pos_dict[ch] for ch in channel_order])

    # Compute heatmap
    def lucy_instance_2args(x, y):
        return lucy_error_fun(np.array([x, y]), velocity, pos_ordered, delta_ts)

    x_range = np.arange(location_search_bounds[0][0], location_search_bounds[0][1], grid_delta)
    y_range = x_range
    x_grid, y_grid = np.meshgrid(x_range, y_range)
    z_grid = np.vectorize(lucy_instance_2args)(x_grid, y_grid)

    # Plot heatmap
    plt.figure(tight_layout=True)
    plt.pcolormesh(x_grid, y_grid, z_grid, cmap="cool")
    plt.colorbar()
    plt.title("Location Result and LUCY-Heatmap")
    plt.xlabel("x [m]")
    plt.ylabel("y [m]")

    # Compute location
    def lucy_instance_single_arg(pos):
        return lucy_error_fun(pos, velocity, pos_ordered, delta_ts)

    start = time.perf_counter()
    # These are excessive search / overkill parameters:
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
    print(f"Runtime for 1 call to differential_evolution(): {(end - start):0.4} s")
    print(location_result)

    # Plot location result
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

    # Plot sensor positions
    for channel, (x, y) in pos_dict.items():
        text = f"S{channel} (x={x:0.2f}m | y={y:0.2f}m)"
        plt.scatter(x, y, marker="o", color="w")
        plt.text(x + text_delta_x, y + text_delta_y, text, fontsize=9, color="w")

    plt.show()


if __name__ == "__main__":
    main()
