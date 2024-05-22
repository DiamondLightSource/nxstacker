# nxstacker

[TOC]

*nxstacker* is an utility to stack projections from different experiments into
a NeXus-compliance file, such as NXtomo and NXstxm. It currently supports the
beamlines i08-1, i13-1 and i14 in Diamond Light Source.

## Installation

After cloning the repository, you can install with pip:

```console
python -m pip install .
```

## Usage

The key function you would be interacting with is *tomojoin*. A command-line
interface is also provided.

### General

#### Get help

For ptycho-tomography,

```console
tomojoin ptycho --help
```

For xrf-tomography,

```console
tomojoin xrf --help
```

#### Get version

```console
tomojoin --version
```

#### Get a NXtomo file from ptycho-tomography experiment

```python
from nxstacker.tomojoin import tomojoin

nxtomo_files = tomojoin(
    "ptychography",
    proj_dir="/i14/dir/projections/stored",
    nxtomo_dir="/tmp/",
    from_scan="275019-275199",
    save_phase=True,
    save_modulus=True,
    save_complex=True,
    median_norm=True,
    unwrap_phase=True,
    remove_ramp=True,
)
```

or via the CLI:

```console
tomojoin ptycho --proj-dir "/i14/dir/projections/stored" --nxtomo-dir
"/tmp" --from-scan 275019-275199 --save-phase --save-modulus --save-complex
--remove-ramp --median-norm --unwrap-phase
```

The above shows an example of producing NXtomo files (the successfully saved
files are returned and stored in the `nxtomo_files`) from a ptycho-tomography
experiment in *i14*.

If the projection files follow a particular naming pattern, e.g.
"/i14/dir/projections/stored/proj\_275019.hdf5",
"/i14/dir/projections/stored/proj\_275020.hdf5" and
"/i14/dir/projections/stored/proj\_275021.hdf5" etc., you can use
`proj_file` with a placeholder `%(scan)`:

```python
from nxstacker.tomojoin import tomojoin

nxtomo_files = tomojoin(
    "ptychography",
    proj_file="/i14/dir/projections/stored/proj_%(scan).hdf5",
    ...
)
```

or via the CLI:

```console
tomojoin ptycho --proj-file "/i14/dir/projections/stored/proj_%(scan).hdf5" ...
```

The `from_scan` string is of the format \<START\>[-\<END\>[:\<STEP\>]], e.g.
"100-105" means 100, 101, 102, 103, 104, 105, "100-105:2" means 100, 102, 104.
They can be chained, e.g. "100-103,110,120-122" means 100, 101, 102, 103, 110,
120, 121, 122. Similarly, you can use `from_proj` for projection numbers and
`from_angle` for rotation angles.

Alternatively, you can provide the scan numbers from a single-columned text
file and use the parameter `scan_list`. Similarly, you can use `proj_list` for
projection numbers and `angle_list` for rotation angles.

To exclude certain scan numbers, you can use `exclude_scan`, it follows the
format of \<START\>[-\<END\>[:\<STEP\>]]. Similarly, you can use `exclude_proj`
for projection numbers and `exclude_angle` for rotation angles.

See API for more information about the arguments.

#### Get a NXtomo file from XRF-tomography experiment

```python
from nxstacker.tomojoin import tomojoin

nxtomo_files = tomojoin(
    "xrf",
    proj_dir="/i14/dir/projections/stored",
    nxtomo_dir="/tmp/",
    from_scan="275019-275199",
    transition="V-Ka,Pt-La",
)
```

or via the CLI:

```console
tomojoin xrf --proj-dir "/i14/dir/projections/stored" --nxtomo-dir
"/tmp" --from-scan 275019-275199 --transition V-Ka,Pt-La
```

`transition` is a comma-delimited list of transitions. The specified
transition must be present in the projection files.

See API for more information about the arguments.

## API

### nxstacker.tomojoin

#### `tomojoin`

There are 20 parameters for this function, excluding parameters specific to a
particular type of experiment.

- *experiment_type*

the type of experiment, such as "ptycho" or "xrf". This must be specified.

- *facility*

the facility, such as "i08-1", "i13-1" or "i14".
If it is left as `None`, it will be dedcued. The utility usually does a good
job in guessing the facility, but if it struggles, please provide this.

- *proj_dir*

the directory where the projections are stored. If it is `None`,
the current working directory is used.

- *proj_file*

the projection file with placeholder %(scan) from *include_scan*
and %(proj) from *include_proj*. If it is `None`, it will search in *proj_dir*.
If the name of the projection files follow a pattern, it is recommended to use
this as it avoids going through files and directories when searching in
*proj_dir*.

- *nxtomo_dir*

the directory where the NXtomo files will be saved. If it is `None`,
the current working directory is used.

- *from_scan*

the string specification of scan identifier with the format
\<START\>[-\<END\>[:\<STEP\>]]. If it is `None`, it is empty.

- *scan_list*

the text file with single-column scan identifier to be included.
If it is `None`, it is empty.

- *exclude_scan*

the scan to be excluded. If it is `None`, nothing is excluded.

- *from_proj*

the projection number string specification, see `from_scan`.

- *proj_list*

the text file with single-column projection numbers to be included.
If it is `None`, it is empty.

- *exclude_proj*

the projection to be excluded. If it is `None`, nothing is excluded.

- *from_angle*

the rotation angle string specification, see `from_scan`.

- *angle_list*

the text file with single-column rotation angle to be included.
If it is `None`, it is empty.

- *exclude_angle*

the rotation angle to be excluded. If it is `None`, nothing is excluded.

- *raw_dir*

the directory where the raw data are stored. For most of the time this can be
left as `None` as the raw directory is inferred from the projection files, but
it is useful when the original raw directory is invalid.

- *sort_by_angle*

whether to sort the projections by their rotation angles. Default to False.

- *pad_to_max*

whether to pad the individual projection if it is not at the maximum size of
the stack. Default to True. If it is False and there is inconsistent size,
RuntimeError is raised.

- *compress*

whether to apply compression (Blosc) to the NXtomo file. Default to False.

- *quiet*

whether to suppress log message. Default to False.

- *dry_run*

whether to perform a dry-run. Default to False.

Parameters specific to `ptycho`/`ptychography`:

- *save_complex*

whether to save the complex number representation of the reconstruction to a
NXtomo file. Default to False.

- *save_modulus*

whether to save the modulus of the reconstruction to a NXtomo file. Default to
False.

- *save_phase*

whether to save the phase of the reconstruction to a NXtomo file. Default to
True.

- *remove_ramp*

whether to remove phase ramp. Currently it is not implemented. Default to
False.

- *median_norm*

whether to shift the phase by its median. Default to False.

- *unwrap_phase*

whether to unwrap phase. Default to False.

- *rescale*

whether to rescale the reconstruction. Currently it is not implemented.
Default to False.

Parameters specific to `xrf`:

- *transition*

a comma-delimited list of transition to be saved. It must be present in the
projection file. E.g. "W-La,Ca-Ka"

## Acknowledgements

The motivation of this utility is to unify the efforts of various tools
developed in different beamlines at Diamond Light Source. Benedikt Daurer's
[PtychographyTools](https://github.com/DiamondLightSource/PtychographyTools)
and Yousef Moazzam's
[scripts for i14](https://github.com/yousefmoazzam/tomo-utils/) provide a lot
of inspirations to this utility.

## Licence

MIT
