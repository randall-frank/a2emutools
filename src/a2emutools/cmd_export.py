import logging
import os.path
from typing import List, Optional

from a2emutools.detokenizer import detokenize

from . import container_formats, filesystem  # noqa: F401

log = logging.getLogger("a2emutools")


def cmd_export(
    cont_name: str,
    prefix: str,
    names: List[str],
    tokenize: bool = False,
    add_ext: Optional[str] = None,
    target_dir: str = ".",
    convert_eol: bool = False,
    naps: bool = False,
):
    container = container_formats.create_image(cont_name)
    fs = container.filesystem
    for name in names:
        s = f"{prefix}/{name}".replace("//", "/")
        entity = fs.find_entity(s)
        if entity is None:
            log.error(f"Unable to find '{name}' in the container '{container.container_name}'")
            continue
        if isinstance(entity, filesystem.FileObj):
            log.info(f"Exporting file '{entity.path}' to '{target_dir}'")
            data = entity.data
            name = entity.name
            if naps:
                name = entity.naps_name
            out_path = os.path.join(target_dir, name)
            if add_ext is not None:
                # if specified, use the provided extension when naming output files
                # if an empty string is provided, add the container file type as the extension
                if len(add_ext) > 0:
                    out_path += add_ext
                else:
                    out_path += f".{entity.file_type}"
            if tokenize and (entity.file_type in ["BAS"]):
                s = detokenize(data)
                with open(out_path, "w") as f:
                    f.write(s)
            else:
                if convert_eol and (entity.file_type in ["TXT"]):
                    data = data.replace(b"\r", b"\n")
                with open(out_path, "wb") as f:
                    f.write(data)
            log.info(f"Exported file to '{out_path}'")
        else:
            log.warning(f"'{entity.path}' is not a file; skipping export")
