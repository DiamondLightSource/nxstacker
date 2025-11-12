from datetime import datetime, timezone

import numpy as np

from nxstacker.utils.model import ExperimentFacility, FixedValue


class NXtomoMetadata:
    """Hold metadata of a NXtomo file."""

    facility = ExperimentFacility()
    projections = FixedValue()
    ignore_raw = FixedValue()

    def __init__(self, projections, facility, *, ignore_raw=False):
        """Initialisse metadata of a NXtomo file.

        Parameters
        ----------
        projections : list
            the list of projection files
        facility : FacilityInfo, str or None
            the facility. It could be of the class FacilityInfo, which
            already contains the details, or a str, where an instance of
            FacilityInfo is initialised, or None, where the
            corresponding facility is deduced from given directories.
        ignore_raw : bool, optional
            whether to ignore metadata obtained from the raw files because
            of their unavailability or speed. If this is True,
            scan_list/proj_list and angle_list must be provided as those
            information are no longer obtained from raw files. Default to
            False.

        """
        self.projections = list(projections)
        self.facility = facility
        self.ignore_raw = ignore_raw

        self.title = "title"
        self.sample_description = "sample description"
        self.rotation_angle = np.arange(len(self.projections))
        self.detector_distance = 1
        self.x_pixel_size = 1
        self.y_pixel_size = 1
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.end_time = datetime.now(timezone.utc).isoformat()

        self.start_end_id_scan()

    def start_end_id_scan(self):
        """Determine the start and end scan ID.

        Set the attribute is_scan_single to indicate a projection list
        with the same scan ID.

        """
        if (start := self.projections[0].id_scan) == (
            end := self.projections[-1].id_scan
        ):
            self.is_scan_single = True
        else:
            self.is_scan_single = False

        self.scan_start = start
        self.scan_end = end

    def to_dict(self):
        """Return the metadata as a dictionary."""
        d = {
            "title": self.title,
            "sample_description": self.sample_description,
            "rotation_angle": self.rotation_angle,
            "detector_distance": self.detector_distance,
            "x_pixel_size": self.x_pixel_size,
            "y_pixel_size": self.y_pixel_size,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }
        return d


class MetadataPtycho(NXtomoMetadata):
    """Represent metadata for a ptycho-tomo experiment."""

    def __init__(self, projections, facility, *, ignore_raw=False):
        """Initialise the ptychography metadata."""
        super().__init__(projections, facility, ignore_raw=ignore_raw)

    def fetch_metadata(self):
        """Find the metadata of the current projections and facility."""
        self.title = self.title_from_scan()
        self.sample_description = self.description_from_scan()
        self.x_pixel_size, self.y_pixel_size = self.find_pixel_size()
        if not self.ignore_raw:
            self.detector_distance = self.find_detector_dist()
            self.rotation_angle = self.find_rotation_angle()
            self.start_time = self.start_time_from_scan()
            self.end_time = self.end_time_from_scan()

    def title_from_scan(self):
        """Determine the tile from scan ID."""
        if self.is_scan_single:
            return f"{self.scan_start}"
        return f"{self.scan_start}-{self.scan_end}"

    def description_from_scan(self):
        """Determine the description of the sample from projection."""
        if descr := self.projections[0].description:
            # all should have the same description, take the first
            return descr

        raw_dir = self.projections[0].raw_dir

        return f"Tomography experiment at {raw_dir} with {self.title}"

    def find_rotation_angle(self):
        """Find rotation angle."""
        match self.facility.name:
            case "i14":
                file_finder = self.facility.nxs_file
            case "i08-1":
                file_finder = self.facility.nxs_file
            case "i13-1":
                file_finder = self.facility.pty_tomo_file
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        rotation_angles = np.empty_like(self.projections, dtype=float)
        for k, p in enumerate(self.projections):
            rot_f = file_finder(p)
            rotation_angles[k] = self.facility.rotation_angle(rot_f, p)

        return rotation_angles

    def find_detector_dist(self):
        """Find sample-detector distance."""
        match self.facility.name:
            case "i14":
                file_finder = [self.facility.nxs_file]
            case "i08-1":
                # constant for i08-1
                return self.facility.sample_detector_dist()
            case "i13-1":
                # there can be two places for the sample detector
                # distance, the projection file itself or the .nxs
                file_finder = [lambda x: x.file_path, self.facility.nxs_file]
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        # take the average from all metadata in the projections
        total = 0
        for p in self.projections:
            for finder in file_finder:
                dist_f = finder(p)

                try:
                    dist = self.facility.sample_detector_dist(dist_f)
                except TypeError:
                    # the exception raised when trying to do None[...]
                    continue
                else:
                    total += dist
                    break

        distance = total / len(self.projections)
        return distance

    def find_pixel_size(self):
        """Find pixel size."""
        # for ptychography, the pixel size is the real-space dimension
        # in the reconstruction, and this should be retrieved from the
        # projection file
        total = 0
        for p in self.projections:
            total += p.pixel_size
        pixel_size = total / len(self.projections)

        return pixel_size, pixel_size

    def start_time_from_scan(self):
        """Find start time."""
        match self.facility.name:
            case "i14":
                file_finder = self.facility.nxs_file
            case "i08-1":
                file_finder = self.facility.nxs_file
            case "i13-1":
                file_finder = self.facility.position_file
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        # take the start time of the first scan in the projections
        start_proj = self.projections[0]

        start_time_f = file_finder(start_proj)
        start_time = self.facility.start_time(start_time_f, start_proj)

        return start_time

    def end_time_from_scan(self):
        """Find end time."""
        match self.facility.name:
            case "i14":
                file_finder = self.facility.nxs_file
            case "i08-1":
                file_finder = self.facility.nxs_file
            case "i13-1":
                file_finder = self.facility.position_file
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        # take the end time of the last scan in the projections
        end_proj = self.projections[-1]

        end_time_f = file_finder(end_proj)
        end_time = self.facility.end_time(end_time_f, end_proj)

        return end_time


class MetadataXRF(NXtomoMetadata):
    """Represent metadata for a XRF-tomo experiment."""

    def __init__(self, projections, facility, *, ignore_raw=False):
        """Initialise the XRF metadata."""
        super().__init__(projections, facility, ignore_raw=ignore_raw)

    def fetch_metadata(self):
        """Find the metadata of the current projections and facility."""
        self.title = self.title_from_scan()
        self.sample_description = self.description_from_scan()
        self.rotation_angle = self.find_rotation_angle()
        self.detector_distance = self.find_detector_dist()
        self.x_pixel_size, self.y_pixel_size = self.find_pixel_size()
        self.start_time = self.start_time_from_scan()
        self.end_time = self.end_time_from_scan()

    def title_from_scan(self):
        """Determine the tile from scan ID."""
        if self.is_scan_single:
            return f"{self.scan_start}"
        return f"{self.scan_start}-{self.scan_end}"

    def description_from_scan(self):
        """Determine the description of the sample from projection."""
        if descr := self.projections[0].description:
            # all should have the same description, take the first
            return descr

        raw_dir = self.projections[0].raw_dir

        return f"Tomography experiment at {raw_dir} with {self.title}"

    def find_rotation_angle(self):
        """Find rotation angle."""
        match self.facility.name:
            case "i14":
                file_finder = self.facility.nxs_file
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        rotation_angles = np.empty_like(self.projections, dtype=float)
        for k, p in enumerate(self.projections):
            rot_f = file_finder(p)
            rotation_angles[k] = self.facility.rotation_angle(rot_f, p)

        return rotation_angles

    def find_detector_dist(self):
        """Find sample-detector distance."""
        match self.facility.name:
            case "i14":
                file_finder = [self.facility.nxs_file]
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        # take the average from all metadata in the projections
        total = 0
        for p in self.projections:
            for finder in file_finder:
                dist_f = finder(p)

                try:
                    dist = self.facility.sample_detector_dist(dist_f)
                except TypeError:
                    # the exception raised when trying to do None[...]
                    continue
                else:
                    total += dist
                    break

        distance = total / len(self.projections)
        return distance

    def find_pixel_size(self):
        """Find pixel size."""
        match self.facility.name:
            case "i14":
                file_finder = self.facility.nxs_file
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        x_px_total, y_px_total = 0, 0
        for p in self.projections:
            px_f = file_finder(p)
            x_px_total += self.facility.x_pixel_size(px_f)
            y_px_total += self.facility.y_pixel_size(px_f)

        x_pixel_size = x_px_total / len(self.projections)
        y_pixel_size = y_px_total / len(self.projections)

        return x_pixel_size, y_pixel_size

    def start_time_from_scan(self):
        """Find start time."""
        match self.facility.name:
            case "i14":
                file_finder = self.facility.nxs_file
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        # take the start time of the first scan in the projections
        start_proj = self.projections[0]

        start_time_f = file_finder(start_proj)
        start_time = self.facility.start_time(start_time_f, start_proj)

        return start_time

    def end_time_from_scan(self):
        """Find end time."""
        match self.facility.name:
            case "i14":
                file_finder = self.facility.nxs_file
            case _:
                msg = f"Facility {self.facility.name} not supported"
                raise ValueError(msg)

        # take the end time of the last scan in the projections
        end_proj = self.projections[-1]

        end_time_f = file_finder(end_proj)
        end_time = self.facility.end_time(end_time_f, end_proj)

        return end_time
