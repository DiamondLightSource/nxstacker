from nxstacker.parser.parser import parse
from nxstacker.utils.experiment import select_tomo_expt


def tomojoin_entry():
    """Entry point for tomojoin."""
    args = parse()
    tomojoin(**args)

def tomojoin(experiment_type, facility=None, proj_dir=None, nxtomo_dir=None,
             include_scan=None, include_proj=None, include_angle=None,
             raw_dir=None, *, sort_by_angle=False, pad_to_max=True,
             compress=False, **kwargs):
    """Combine projections to produce an NXtomo file.

    Parameters
    ----------
    experiment_type : str

    proj_dir : Path

    nxtomo_dir : Path

    include_scan : list

    include_proj : list

    include_angle : list

    facility : str

    raw_dir : Path
    """
    # initiate instance for experiment
    tomo_expt = select_tomo_expt(experiment_type, facility, proj_dir,
                                 nxtomo_dir, include_scan, include_proj,
                                 include_angle, raw_dir,
                                 sort_by_angle=sort_by_angle,
                                 pad_to_max=pad_to_max, compress=compress,
                                 **kwargs)

    tomo_expt.find_all_projections()

    # associate projections with projection angles
    tomo_expt.extract_projections_details()

    # stack the projections as NXtomo
    tomo_expt.stack_projection()
