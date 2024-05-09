import numpy as np
from skimage.restoration import unwrap_phase as unwrap


def unwrap_phase(phase):
    """Unwrap the phase.

    Parameters
    ----------
    phase : ndarray
        the phase image

    Returns
    -------
    unwrapped : ndarray
        the unwrapped phase image
    """
    unwrapped = unwrap(phase)

    # reverse the sign of phase when the % of positive is less than half
    if np.count_nonzero(unwrapped > 0) / unwrapped.size < 0.5:
        unwrapped *= -1

    return unwrapped
