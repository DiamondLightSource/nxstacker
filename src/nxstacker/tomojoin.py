import time

from nxstacker.parser.parser import parse
from nxstacker.utils.experiment import select_tomo_expt
from nxstacker.utils.logger import logger
from nxstacker.utils.parse import parse_identifier


def tomojoin_entry():
    """Entry point for tomojoin."""
    args = parse()
    tomojoin(**args)


def tomojoin(
    experiment_type,
    facility=None,
    proj_dir=None,
    proj_file=None,
    nxtomo_dir=None,
    from_scan=None,
    scan_list=None,
    exclude_scan=None,
    from_proj=None,
    proj_list=None,
    exclude_proj=None,
    from_angle=None,
    angle_list=None,
    exclude_angle=None,
    raw_dir=None,
    *,
    sort_by_angle=False,
    pad_to_max=True,
    compress=False,
    **kwargs,
):
    """Combine projections to produce an NXtomo file.

    Parameters
    ----------
    experiment_type : str
        the type of experiment
    facility : FacilityInfo, str or None, optional
        the facility. It could be of the class FacilityInfo, which
        already contains the details, or a str, where an instance of
        FacilityInfo is initialised, or None, where the
        corresponding facility is deduced from given directories.
        Default to None.
    proj_dir : pathlib.Path, str or None
        the directory where the projections are stored. If it is
        None, the current working directory is used. Default to None.
    proj_file : str or None
        the projection file with placeholder %(scan) from include_scan
        and %(proj) from include_proj. Default to None.
    nxtomo_dir : pathlib.Path, str or None
        the directory where the NXtomo files will be saved. If it is
        None, the current working directory is used. Default to None.
    from_scan : str or None
        the string specification of scan identifier with the format
        <START>[-<END>[:<STEP>]]. Default to None, and it is empty.
    scan_list : str or None
        the text file with single-column scan identifier to be included.
        Default to None, and it is empty.
    exclude_scan : str or None
        the scan to be excluded. Default to None, and nothing is
        excluded.
    from_proj : str or None
        the projection number string specification, see 'from_scan'.
    proj_list : str or None
        the text file with single-column projection numbers to be
        included.  Default to None, and it is empty.
    exclude_proj : str or None
        the projection to be excluded. Default to None, and nothing is
        excluded.
    from_angle : str or None
        the rotation angle string specification, see 'from_scan'.
    angle_list : str or None
        the text file with single-column rotation angle to be included.
        Default to None, and it is empty.
    exclude_angle : str or None
        the rotation angle to be excluded. Default to None, and nothing
        is excluded.
    raw_dir : pathlib.Path, str or None, optional
        the directory where the raw data are stored. For most of the
        time this can be left as None as the raw directory is
        inferred from the projection files, but it is useful when
        the original raw directory is invalid. Default to None.
    sort_by_angle : bool, optional
        whether to sort the projections by their rotation angles.
        Default to False.
    pad_to_max : bool, optional
        whether to pad the individual projection if it is not at the
        maximum size of the stack. Default to True. If it is False
        and there is inconsistent size, RuntimeError is raised.
    compress : bool, optional
        whether to apply compression (Blosc) to the NXtomo file.
        Default to False.
    kwargs : dict, optional
        options for ptycho-tomography

    Returns
    -------
    a list of successfully saved NXtomo files

    """
    include_scan = parse_identifier(from_scan, scan_list, exclude_scan)
    include_proj = parse_identifier(from_proj, proj_list, exclude_proj)
    include_angle = parse_identifier(
        from_angle, angle_list, exclude_angle, id_type=float
    )

    # initiate instance for experiment
    tomo_expt = select_tomo_expt(
        experiment_type,
        facility,
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
        **kwargs,
    )

    logger.info("Start finding projections...")
    st = time.perf_counter()

    tomo_expt.find_all_projections()

    logger.info("Finished finding projections.")
    elapse = time.perf_counter() - st
    logger.info(f"The duration of finding projections: {elapse:.2f} s")
    logger.info(f"{tomo_expt.num_projections} projections have been found.")
    logger.info(
        f"The raw data directory is " f"{tomo_expt.projections[0].raw_dir}"
    )

    # associate projections with projection angles
    tomo_expt.extract_projections_details()

    # stack the projections as NXtomo
    logger.info("Start saving NXtomo file...")
    logger.info(f"The directory of the NXtomo file is {tomo_expt.nxtomo_dir}")
    st = time.perf_counter()

    tomo_expt.stack_projection()

    logger.info("Finished saving NXtomo.")
    elapse = time.perf_counter() - st
    logger.info(f"The duration of saving NXtomo file: {elapse:.2f} s")

    return tomo_expt.nxtomo_output_files
