def quote_iterable(iterable):
    """Produce quoted and comma-delimited string from an iterable.

    It converts, e.g. ["abc", "def", "ghi"] to
    "'abc', 'def' and 'ghi'". These are more friendly for stdout or
    stderr.

    Parameters
    ----------
    iterable : any iterable
        the iterable to be processed.

    Returns
    -------
    comma : str
        the quoted and comma-delimited string
    """
    if len(iterable) == 1:
        return f"'{next(iter(iterable))}'"

    quoted = [f"'{entry}'" for entry in iterable]
    comma = ", ".join(quoted[:-1])
    comma += f" and {quoted[-1]}"

    return comma

def unique_or_raise(iterable, companion=None, label="item", reference=None):
    """Return unique item or raise when encounters inhomogeneous item.

    Parameters
    ----------
    iterable : any iterable
        the iterable which uniquenes is to be checked.
    companion : any iterable, optional
        the iterable relates to the iterable which uniqueness is to be
        checked.  It must have the same length with the iterable above.
        This is for more relevant error message. Default to None, set to
        the same iterable above.
    label : str, optional
        the name of the item. This is for more descriptive error
        message. Default to "item".
    reference : Any, optional
        the reference to check uniqueness against. Default to None, set
        to the first item of the iterable.

    Returns
    -------
    the unique item
    """
    if companion is None:
        companion = iterable

    if len(iterable) != len(companion):
        msg = ("The companion must have the same length with the actual "
                "iterable.")
        raise ValueError(msg)

    seen = set()
    for k, item in enumerate(iterable):
        if reference is None:
            reference = item

        seen.add(item)
        if len(seen) > 1:
            msg = (f"Inhomogenous {label} for {companion[k]}. "
                   f"This has {item} but the reference is {reference}.")
            raise RuntimeError(msg)

    return seen.pop()
