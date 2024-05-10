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

def remove_phase_ramp(arr, radius=0.5, niter=1, *, use_weight=True,
                      modulus_weight=False):
    """Remove the phase ramp.

    This is taken from PtychographyTools.

    Parameters
    ----------
    arr : ndarray
        the complex object
    radius : float, optional
        the radius from the centre where the weight will be applied.
        Default to 0.5
    niter : int, optional
        the phase ramp is removed iteratively and this is the number of
        iterations. Default to 1.
    use_weight : bool, optional
        whether weight is used in phase removal. Default to True.
    modulus_weight : bool, optional
        if weight is used, whether the weight is from its modulus.
        Default to False.

    Returns
    -------
    cplx_img : ndarray
        the complex 2D array with phase ramp removed
    """
    cplx_img = arr.copy()

    if use_weight:
        weight = ramp_weight(cplx_img, radius=radius,
                             modulus_weight=modulus_weight)
    else:
        weight = None

    for _ in range(niter):
        # remove repeatedly
        cplx_img = rmphaseramp(cplx_img, weight=weight)

    return cplx_img

def ramp_weight(cplx_img, radius=0.5, *, modulus_weight=False):
    """Return the weight used in phase ramp removal (taken from PtyPy)."""
    if modulus_weight:
        w = np.abs(cplx_img)
    else:
        ny, nx = cplx_img.shape
        xx, yy = np.meshgrid(np.arange(nx) - nx//2, np.arange(ny) - ny//2)
        w = np.sqrt(xx**2 + yy**2) < (radius * (nx + ny) / 4)

    return w

def rmphaseramp(a, weight=None):
    """Remove the phase ramp in a two-dimensional complex array.

    This is taken from PtyPy.

    Parameters
    ----------
    a : ndarray
        input image as complex 2D-array.

    weight : ndarray, optional
        the weighting array. Default to None.

    Returns
    -------
    out : ndarray
        Modified 2D-array, ``out=a*p``
    """

    ph = np.exp(1j*np.angle(a))
    [gx, gy] = np.gradient(ph)
    gx = -np.real(1j*gx/ph)
    gy = -np.real(1j*gy/ph)

    if weight is not None:
        nrm = weight.sum()
        agx = (gx*weight).sum() / nrm
        agy = (gy*weight).sum() / nrm
    else:
        agx = gx.mean()
        agy = gy.mean()

    xx, yy = np.indices(a.shape)
    p = np.exp(-1j*(agx*xx + agy*yy))

    out = a * p

    return out
