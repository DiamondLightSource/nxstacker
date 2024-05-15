from collections.abc import Sequence
from pathlib import Path

import yaml

SPECS_DIR = Path(__file__).parent / "specs"


class AccumulatedDict(dict):
    """A dictionary which joins their values when merging."""

    def __or__(self, other):
        if not isinstance(other, dict):
            return NotImplemented

        new = dict(self)
        for k, v in other.items():
            original = self.get(k)

            if original is None or isinstance(original, str):
                new[k] = v
            elif isinstance(original, list):
                new[k].extend(list(v))
            else:
                original_list = [original]
                new[k] = [*original_list, v]

        return new

    def __ior__(self, other):
        for k, v in other.items():
            original = self.get(k)

            if original is None or isinstance(original, str):
                self[k] = v
            elif isinstance(original, list):
                self[k].extend(list(v))
            else:
                original_list = [original]
                self[k] = [*original_list, v]
        return self


class SpecsAccumulator:
    """A descriptor to join values from YAML accumulatively."""

    def __init__(self):
        """Initialise the name of descriptor as "specs"."""
        self.name = "specs"

    def __get__(self, obj, objtype=None):
        return obj.__dict__.get(self.name, [])

    def __set__(self, obj, value):
        if not isinstance(value, list):
            value = [value]

        if obj.__dict__.get(self.name) is None:
            obj.__dict__[self.name] = value
        else:
            obj.__dict__[self.name].extend(value)

        # update _specs_dict in the instance
        if obj.__dict__.get("_specs_dict") is None:
            obj.__dict__["_specs_dict"] = AccumulatedDict()

        for spec in value:
            try:
                f = spec.open()
            except FileNotFoundError:
                msg = (
                    f"The facility specification file '{spec.resolve()}' "
                    "cannot be found."
                )
                raise FileNotFoundError(msg) from None
            else:
                obj.__dict__["_specs_dict"] |= yaml.safe_load(f)
                f.close()

    def __delete__(self, obj):
        obj.__dict__[self.name] = []
        obj.__dict__["_specs_dict"] = AccumulatedDict()


class FacilityInfo:
    """Hold directory structure and hdf5 paths of a facility."""

    name = "unknown"
    specs = SpecsAccumulator()

    def __init__(self):
        """Initialise the information common to different facility."""
        self._specs_dict = AccumulatedDict()
        self.specs = SPECS_DIR / "common.yaml"

        self.source_type = "Synchrotron X-ray Source"
        self.source_name = "Diamond Light Source"
        self.source_name_short = "DLS"
        self.source_probe = "x-ray"

    def populate_attr(self):
        """Define attributes from a dict."""
        for attr_name, attr_val in self.specs_dict.items():
            # get the current value of the attribute
            current_val = self.__dict__.get(attr_name)

            if current_val is None or isinstance(current_val, str):
                # set it if is currently not defined
                # it will overwrite if it is a string
                self.__dict__[attr_name] = attr_val
            elif isinstance(current_val, Sequence):
                # extend it if it is a sequence
                self.__dict__[attr_name].extend(list(attr_val))
            else:
                # if not, make the content from yaml as list and extent
                # it
                val_list = list(current_val)
                self.__dict__[attr_name] = val_list + list(attr_val)

    @property
    def specs_dict(self):
        """Return the accumulated specs dictionary."""
        return self._specs_dict

    def __str__(self):
        return f"'{self.name}' information"

    def __repr__(self):
        cls_name = type(self).__name__
        return f"{cls_name}()"
