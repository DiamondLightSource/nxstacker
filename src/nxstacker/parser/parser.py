import argparse
from contextlib import suppress
from pathlib import Path

from nxstacker.parser.proj_identifier import ProjIdentifier

NIMPL = "NOT YET IMPLEMENTED"
HELP_EXPT = "the type of experiment"
HELP_VERBOSE = "show more information"
HELP_PROJ_DIR = "the directory where the projections are stored"
HELP_PROJ_FILE = "the file path with placeholder %%(scan) and/or %%(proj)"
HELP_NXTOMO_DIR = "the directory where the NXtomo file will be saved"
HELP_RAW_DIR = "the directory where the raw files are stored"
HELP_FACILITY = "the facility identifier, e.g. i14, i08-1, i13-1"
HELP_FROM_SCAN = "the scan number specifier, e.g. 100-120"
HELP_SCAN_LIST = "the file with scan numbers as the only column"
HELP_EXCLUDE_SCAN = "scan number(s) that should be excluded from"
HELP_FROM_PROJ = "the projection number specifier, e.g. 0-100"
HELP_PROJ_LIST = "the file with projection numbers as the only column"
HELP_EXCLUDE_PROJ = "projection number(s) that should be excluded from"
HELP_FROM_ANGLE = "the rotation angle specifier, e.g. -90-90:5"
HELP_ANGLE_LIST = "the file with rotation angles as the only column"
HELP_EXCLUDE_ANGLE = "rotation angle(s) that should be excluded from"
HELP_SORT_BY_ANGLE = "sort the projections by their rotation angles"
HELP_PAD_TO_MAX = "pad projection to the maximum size of the stack"
HELP_COMPRESS = "compress the NXtomo file"
HELP_SAVE_COMPLEX = "save the complex result from ptychography"
HELP_SAVE_MODULUS = "save the modulus result from ptychography"
HELP_SAVE_PHASE = "save the phase result from ptychography"
HELP_UNWRAP_PHASE = "unwrap the phase"
HELP_REMOVE_RAMP = "remove the phase ramp"
HELP_MEDI_NORM = "normalise the phase by shifting its median"
HELP_TRANSITION = (
    "a comma-delimited string of transition in the format of "
    "<ELEMENT>-<TRANSITION>"
)


def parse():
    """Parse arguments from command-line interface."""
    parser = argparse.ArgumentParser(add_help=True)
    subparsers = parser.add_subparsers(help=HELP_EXPT, dest="experiment_type")

    # shared flags among different parsers
    parser_common = _parser_common()

    # create the parser for dpc
    _parser_dpc(subparsers, parents=[parser_common])

    # create the parser for ptycho
    _parser_ptycho(subparsers, parents=[parser_common])

    # create the parser for xrf
    _parser_xrf(subparsers, parents=[parser_common])

    args = parser.parse_args()

    # get projections that should be included
    include_scan, include_proj, include_angle = _parse_identifier(args)

    # as a dict
    args_dict = vars(args)

    # remove redundant keys
    with suppress(KeyError):
        args_dict.pop("from_scan")
        args_dict.pop("scan_list")
        args_dict.pop("exclude_scan")
        args_dict.pop("from_proj")
        args_dict.pop("proj_list")
        args_dict.pop("exclude_proj")
        args_dict.pop("from_angle")
        args_dict.pop("angle_list")
        args_dict.pop("exclude_angle")

    # add useful keys
    args_dict["include_scan"] = include_scan
    args_dict["include_proj"] = include_proj
    args_dict["include_angle"] = include_angle

    return args_dict


def _parser_common():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-v", "--verbose", action="store_true", help=NIMPL)
    parser.add_argument("--dry-run", action="store_true", help=NIMPL)

    parser.add_argument(
        "--proj-dir", type=Path, default=Path(), help=HELP_PROJ_DIR
    )
    parser.add_argument("--proj-file", type=str, help=HELP_PROJ_FILE)
    parser.add_argument(
        "--nxtomo-dir", type=Path, default=Path(), help=HELP_NXTOMO_DIR
    )
    parser.add_argument("--raw-dir", type=Path, help=HELP_RAW_DIR)
    parser.add_argument("--facility", type=str, help=HELP_FACILITY)

    parser.add_argument("--from-scan", type=str, help=HELP_FROM_SCAN)
    parser.add_argument("--scan-list", type=Path, help=HELP_SCAN_LIST)
    parser.add_argument("--exclude-scan", type=str, help=HELP_EXCLUDE_SCAN)

    parser.add_argument("--from-proj", type=str, help=HELP_FROM_PROJ)
    parser.add_argument("--proj-list", type=Path, help=HELP_PROJ_LIST)
    parser.add_argument("--exclude-proj", type=str, help=HELP_EXCLUDE_PROJ)

    parser.add_argument("--from-angle", type=str, help=HELP_FROM_ANGLE)
    parser.add_argument("--angle-list", type=Path, help=HELP_ANGLE_LIST)
    parser.add_argument("--exclude-angle", type=str, help=HELP_EXCLUDE_ANGLE)

    parser.add_argument(
        "--sort-by-angle",
        action="store_true",
        default=False,
        help=HELP_SORT_BY_ANGLE,
    )
    parser.add_argument(
        "--pad-to-max", action="store_true", default=True, help=HELP_PAD_TO_MAX
    )
    parser.add_argument(
        "--compress", action="store_true", default=False, help=HELP_COMPRESS
    )

    return parser


def _parser_dpc(subparsers, **kwargs):
    subparser = subparsers.add_parser("dpc", help="for DPC", **kwargs)
    subparser.add_argument("--retrieval-method")


def _parser_xrf(subparsers, **kwargs):
    subparser = subparsers.add_parser("xrf", help="for XRF", **kwargs)
    subparser.add_argument("--transition", type=str, help=HELP_TRANSITION)


def _parser_ptycho(subparsers, **kwargs):
    subparser = subparsers.add_parser(
        "ptycho", help="for ptychography", **kwargs
    )
    subparser.add_argument(
        "--save-complex",
        action="store_true",
        default=False,
        help=HELP_SAVE_COMPLEX,
    )
    subparser.add_argument(
        "--save-modulus",
        action="store_true",
        default=False,
        help=HELP_SAVE_MODULUS,
    )
    subparser.add_argument(
        "--save-phase", action="store_true", default=True, help=HELP_SAVE_PHASE
    )
    subparser.add_argument(
        "--remove-ramp", action="store_true", default=False, help=NIMPL
    )
    subparser.add_argument(
        "--median-norm",
        action="store_true",
        default=False,
        help=HELP_MEDI_NORM,
    )
    subparser.add_argument(
        "--unwrap-phase",
        action="store_true",
        default=False,
        help=HELP_UNWRAP_PHASE,
    )
    subparser.add_argument(
        "--rescale", action="store_true", default=False, help=NIMPL
    )


def _parse_identifier(args):
    scan_pi = ProjIdentifier(
        args.from_scan, args.scan_list, args.exclude_scan, id_type=int
    )
    include_scan = scan_pi.identifiers

    proj_pi = ProjIdentifier(
        args.from_proj, args.proj_list, args.exclude_proj, id_type=int
    )
    include_proj = proj_pi.identifiers

    angle_pi = ProjIdentifier(
        args.from_angle, args.angle_list, args.exclude_angle, id_type=float
    )
    include_angle = angle_pi.identifiers

    return include_scan, include_proj, include_angle
