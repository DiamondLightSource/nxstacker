import logging


def create_logger(level=None, name=None):
    """Create a logger.

    Parameters
    ----------
    level : int, optional
        the logging leve. Default to None, and set to 10, logging.INFO.
    name : str, optional
        the name of the logger. Default to None, and set to the name of
        the file.

    Returns
    -------
    logger : logging.Logger
        the logger

    """
    if level is None:
        level = logging.INFO
    if name is None:
        name = __name__

    # create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    return logger
