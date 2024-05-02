from .parser.proj_identifier import ProjIdentifier
from .experiment.ptychotomo import PtychoTomo
from .facility import FacilityInfo, I14, I13_1, I08_1


def tomojoin_entry():
    """Entry point for nxstacker.
    """
    # parse, then delegate to tomojoin
    pass

def parse():
    # parse argument


    # parse scans and wrap it as class
    # parse projs and wrap it as class
    # parse angles and wrap it as class
    pass

def set_facility(facility, proj_dir=None, nxtomo_dir=None):
    match facility:
        case "i14":
            facility_info = I14()
        case "i13-1":
            facility_info = I13_1()
        case "i08-1" | "j08":
            facility_info = I08_1()
        case None:
            facility_info = deduce_facility(proj_dir, nxtomo_dir)
        case _:
            pass

    return facility_info

def set_experiment(experiment_type, facility, proj_dir, nxtomo_dir,
                   id_scan, id_proj, id_angle, **kwargs):

    match experiment_type.lower():
        case "ptycho" | "ptychography":
            tomo_expt = PtychoTomo(proj_dir, nxtomo_dir, facility,
                                   id_scan, id_proj, id_angle, **kwargs)
        case "xrf":
            tomo_expt = XRFTomo(proj_dir, nxtomo_dir, facility,
                                id_scan, id_proj, id_angle, **kwargs)
        case "dpc":
            pass
        case _:
            pass

    return tomo_expt


def tomojoin(experiment_type, proj_dir, nxtomo_dir, id_scan=None, id_proj=None,
             id_angle=None, facility=None, **kwargs):
    """Combine projections to an NXtomo file.

    Parameters
    ----------
    experiment_type : str

    proj_dir : Path

    id_scan : ProjIdentifier

    id_proj : ProjIdentifier

    id_angle : ProjIdentifier
    """

    # determine facility
    facility = set_facility(facility, proj_dir, nxtomo_dir)

    # initiate instance for experiment
    tomo_expt = set_experiment(experiment_type, facility, proj_dir, nxtomo_dir,
                               id_scan, id_proj, id_angle,
                               **kwargs)


    # includes some sorting, unique value
    tomo_expt.find_all_projections()

    # associated every projection with a projection angle
    tomo_expt.extract_projections_details()

    # stack the projections with specified sorting
    # save the stack as NXtomo
    tomo_expt.stack_projection()
    breakpoint()
