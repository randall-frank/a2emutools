import logging
from typing import List

from . import container_formats, filesystem  # noqa: F401

_ = logging.getLogger("a2emutools")


def cmd_rm(cont_name: str, prefix: str, names: List[str], recurse: bool = False):
    return
