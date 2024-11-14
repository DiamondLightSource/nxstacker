import os


def num_cpus(capped_at=32):
    """Return the capped number of available CPUs.

    This is to prevent using all the available CPUs when this is
    executed in an NX session, for example, while using more than 32 CPUs
    does not gain much.

    Parameters
    ----------
    capped_at : int, optional
        the maximum number of CPUs to be used. Default to 32.

    """
    capped_at = max(capped_at, 1)

    # from py3.13 there is a os.process_cpu_count function
    # can switch over once <=py3.12 support is dropped
    avail_cpus = len(os.sched_getaffinity(0))

    # capped
    return min(avail_cpus, capped_at)
