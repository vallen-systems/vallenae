from typing import Dict

import numpy as np
from scipy import stats

import vallenae as vae


def feature_extraction(tra: vae.io.TraRecord) -> Dict[str, float]:
    """Compute random statistical features."""
    return {
        "Std": np.std(tra.data),
        "Skew": stats.skew(tra.data),
    }
