from nxstacker.experiment.ptychotomo import PtychoTomo
from nxstacker.experiment.xrftomo import XRFTomo
from nxstacker.utils.facility import choose_facility_info


def select_tomo_expt(
    experiment_type,
    facility=None,
    proj_dir=None,
    proj_file=None,
    nxtomo_dir=None,
    include_scan=None,
    include_proj=None,
    include_angle=None,
    raw_dir=None,
    *,
    sort_by_angle=False,
    pad_to_max=True,
    compress=False,
    skip_proj_file_check=False,
    ignore_raw=False,
    **kwargs,
):
    """Select the experiment for the projections.

    Parameters
    ----------
    experiment_type : str
        a string that indicates the type of experiment, e.g. "ptycho",
        "xrf".
    facility : str, optional
        a string that indicates the facility, e.g. "i14", "i08-1",
        "i13-1". Default to None, and it will be deduced.
    proj_dir : Path, optional
        the directory where it stores all the projections. Default to
        None, and it will be set to the current working directory.
    proj_file : str or None
        the projection file with placeholder %(scan) from include_scan
        and %(proj) from include_proj. Default to None.
    nxtomo_dir : Path, optional
        the directory where the NXtomo file will be saved. Default to
        None, and it will be set to the current working directory.
    include_scan : str or list, optional
        the scan to be included. If it is a str, it should be in the
        format <START>[-<END>[:<STEP>]]. Default to None, every scan
        found in the proj_dir will be included.
    include_proj : str or list, optional
        the projection to be included. If it is a str, it should be in
        the format <START>[-<END>[:<STEP>]]. Default to None, every
        projection found in the proj_dir will be included.
    include_angle : str or list, optional
        the rotation angle to be included. If it is a str, it should be
        in the format <START>[-<END>[:<STEP>]]. Default to None, every
        rotation angle will be included.
    raw_dir : Path, optional
        the directory where the raw files are saved. Default to None,
        and it will be deduced from projections.
    sort_by_angle : bool, optional
        whether to sort the projections by their angles. Default to
        False.
    pad_to_max : bool, optional
        whether to pad a projection to the maximum size of the stack.
        Default to True. If this is False and there is a projection with
        inconsistent size, it will terminate.
    compress : bool, optional
        whether to apply compression on the NXtomo file. Default to
        False.
    skip_proj_file_check : bool, optional
        whether to skip the file check when adding an hdf5 to the list
        of projection files. Usually this is true when you are doing a
        typical stacking and sure no other hdf5 files are present in
        proj_dir. Default to False.
    ignore_raw : bool, optional
        whether to ignore metadata obtained from the raw files because
        of their unavailability or speed. If this is True,
        scan_list/proj_list and angle_list must be provided as those
        information are no longer obtained from raw files. Default to
        False.
    kwargs : dict, optional
        optional arguments to different types of experiments

    Returns
    -------
    tomo_expt : TomoExpt
        the tomography experiment from a particular type of projections

    """
    # determine facility
    facility_info = choose_facility_info(
        facility, dirs=[proj_dir, proj_file, nxtomo_dir, raw_dir]
    )

    match experiment_type.lower():
        case "ptycho" | "ptychography":
            tomo_expt = PtychoTomo(
                facility_info,
                proj_dir,
                proj_file,
                nxtomo_dir,
                include_scan,
                include_proj,
                include_angle,
                raw_dir,
                sort_by_angle=sort_by_angle,
                pad_to_max=pad_to_max,
                compress=compress,
                skip_proj_file_check=skip_proj_file_check,
                ignore_raw=ignore_raw,
                **kwargs,
            )
        case "xrf":
            tomo_expt = XRFTomo(
                facility_info,
                proj_dir,
                proj_file,
                nxtomo_dir,
                include_scan,
                include_proj,
                include_angle,
                raw_dir,
                sort_by_angle=sort_by_angle,
                pad_to_max=pad_to_max,
                compress=compress,
                skip_proj_file_check=skip_proj_file_check,
                ignore_raw=ignore_raw,
                **kwargs,
            )
        case "dpc":
            pass
        case _:
            msg = f"The experiment '{experiment_type}' is not supported."
            raise ValueError(msg)

    return tomo_expt
