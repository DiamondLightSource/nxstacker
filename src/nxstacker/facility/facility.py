from pathlib import Path

import yaml

SPECS_DIR = Path(__file__).parent / "specs"



class AccumulatedDict(dict):

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

    def __init__(self):
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
                msg = (f"The facility specification file '{spec.resolve()}' "
                        "cannot be found.")
                raise FileNotFoundError(msg) from None
            else:
                obj.__dict__["_specs_dict"] |= yaml.safe_load(f)
                f.close()

    def __delete__(self, obj):
        obj.__dict__[self.name] = []
        obj.__dict__["_specs_dict"] = AccumulatedDict()


class FacilityInfo:
    """
    """
    specs = SpecsAccumulator()

    def __init__(self):
        self._specs_dict = AccumulatedDict()
        self.specs = SPECS_DIR / "common.yaml"

        self.source_type = "Synchrotron X-ray Source"
        self.source_name = "Diamond Light Source"
        self.source_name_short = "DLS"
        self.source_probe = "x-ray"

    def populate_attr(self):
        for k, v in self.specs_dict.items():
            val  = self.__dict__.get(k)

            if val is None or isinstance(val, str):
                self.__dict__[k] = v
            elif isinstance(val, list):
                self.__dict__[k].extend(list(v))
            else:
                val_list = list(val)
                self.__dict__[k] = val_list + list(v)

    @classmethod
    def deduce_facility(cls, proj_dir, nxtomo_path):
        pass

    @property
    def specs_dict(self):
        return self._specs_dict
