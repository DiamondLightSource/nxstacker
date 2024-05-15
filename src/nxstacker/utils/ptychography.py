import numpy as np
from skimage.restoration import unwrap_phase as unwrap


def unwrap_phase(phase):
    """Unwrap the phase.

    This is taken from PtychographyTools.

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


def remove_phase_ramp(arr):
    """Avoid licensing issue so this is idempotent for now."""
    return arr


def phase_shift(arr, shift):
    """Phase shift."""
    return arr * np.exp(1j * shift)
