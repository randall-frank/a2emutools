import logging
import sys
from typing import List

from . import container_formats, filesystem  # noqa: F401

log = logging.getLogger("a2emutools")


def cmd_import(
    cont_name: str,
    prefix: str,
    names: List[str],
    tokenize: bool = False,
    force_type: str = "",
    target_dir: str = ".",
    convert_eol: bool = False,
):
    container = container_formats.create_image(cont_name)
    fs = container.filesystem
    root = fs.find_entity(prefix)
    if root is None:
        log.error(f"Unable to find '{prefix}' in the container '{container.container_name}'")
        sys.exit(1)

    return
