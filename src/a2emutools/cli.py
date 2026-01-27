import argparse
import logging

from a2emutools import (
    __version__,
    cmd_create,
    cmd_export,
    cmd_import,
    cmd_info,
    cmd_ls,
    cmd_mkdir,
    cmd_rm,
)

"""
Command line tool:  python -m a2emutools

Pathname specification:

Container files:
/foo/file{.dsk,.po,.do,.2mg,.hdv}
C:/foo/file{.dsk,.po,.do,.2mg,.hdv}

ext is the tuple: ('.dsk', '.po', '.do', '.hdv', '.2mg')
Detect using: endswith '{ext}'

Filenames can use NAPS specification: #XXYYYY

Where XX is the filetype code in hex and YYYY is the file's "auxflags" value in hex.

Commands:

    ls container [--prefix pfx] [--full] [--recurse]
    rm container name [name] [--prefix pfx] [--recurse]
    create container [--size size] [--bootable]
    mkdir container name [--prefix pfx] [--recurse]
    export container name [name] [--prefix pfx] [--tokenize] [--force_type type]
    import container name [name] [--prefix pfx] [--tokenize] [--force_type type]
    info container [--vtoc]

"""


def parse_k_m_number(value: str) -> int:
    """Parses a string ending in K or M into an integer."""
    value = value.upper()
    if value.endswith("K"):
        return int(float(value[:-1]) * 1024)
    elif value.endswith("M"):
        return int(float(value[:-1]) * 1024 * 1024)
    return int(value)


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )
    cmd_parsers = parser.add_subparsers(help="Commands", dest="cmd")
    cmd_parsers.required = True
    parser.add_argument("--verbose", action="store_true", default=False, help="Run in verbose mode")
    parser.add_argument("--logfile", help="Log file for verbose output", default="")

    ls_parser = cmd_parsers.add_parser("ls", help="List directory contents")
    ls_parser.add_argument("container", help="Disk image container name", default=None)
    ls_parser.add_argument(
        "--prefix", type=str, default="/", help="Filepath prefix within the container"
    )
    ls_parser.add_argument(
        "--full", action="store_true", default=False, help="Include file details"
    )
    ls_parser.add_argument(
        "--recurse", action="store_true", default=False, help="Delete recursively"
    )

    rm_parser = cmd_parsers.add_parser("rm", help="Delete a file/directory")
    rm_parser.add_argument("container", help="Disk image container name", default=None)
    rm_parser.add_argument(
        "names", help="File and directory names to delete", default=None, nargs="+"
    )
    rm_parser.add_argument(
        "--prefix", type=str, default="/", help="Filepath prefix within the container"
    )
    rm_parser.add_argument(
        "--recurse", action="store_true", default=False, help="Delete recursively"
    )

    mkdir_parser = cmd_parsers.add_parser("mkdir", help="Create a directory")
    mkdir_parser.add_argument("container", help="Disk image container name", default=None)
    mkdir_parser.add_argument("names", help="Directory names to create", default=None, nargs="+")
    mkdir_parser.add_argument(
        "--prefix", type=str, default="/", help="Filepath prefix within the container"
    )
    mkdir_parser.add_argument(
        "--recurse", action="store_true", default=False, help="Create intermediate directories"
    )

    create_parser = cmd_parsers.add_parser("create", help="Create a new disk image container")
    create_parser.add_argument("container", help="Disk image container name", default=None)
    create_parser.add_argument(
        "--size",
        type=parse_k_m_number,
        help="Volume size in bytes. K and M (e.g. 140K, 32M) are legal. Default: 140K",
        default=143360,
    )
    create_parser.add_argument(
        "--no-bootable",
        dest="bootable",
        action="store_false",
        default=True,
        help="If creating a disk image, do not make it bootable",
    )

    import_parser = cmd_parsers.add_parser("import", help="Import a file into the container")
    import_parser.add_argument("container", help="Disk image container name", default=None)
    import_parser.add_argument("names", help="Filenames to import", default=None, nargs="+")
    import_parser.add_argument(
        "--prefix", type=str, default="/", help="Filepath prefix within the container"
    )
    import_parser.add_argument(
        "--tokenize",
        dest="tokenize",
        action="store_true",
        default=False,
        help="Apply tokenization to imported files (useful for Applesoft basic files)",
    )
    import_parser.add_argument(
        "--force_type",
        type=str,
        default="",
        help="Override the natural input file type to use provided type instead",
    )

    export_parser = cmd_parsers.add_parser("export", help="Export a file from the container")
    export_parser.add_argument("container", help="Disk image container name", default=None)
    export_parser.add_argument("names", help="Filenames to export", default=None, nargs="+")
    export_parser.add_argument(
        "--prefix", type=str, default="/", help="Filepath prefix within the container"
    )
    export_parser.add_argument(
        "--tokenize",
        dest="tokenize",
        action="store_true",
        default=False,
        help="Apply detokenization to exported files (useful for Applesoft basic files",
    )
    export_parser.add_argument(
        "--force_type",
        type=str,
        default="",
        help="Override the natural input file type to use provided type instead",
    )

    info_parser = cmd_parsers.add_parser(
        "info", help="Return detailed container/filesystem information"
    )
    info_parser.add_argument("container", help="Disk image container name", default=None)
    info_parser.add_argument(
        "--vtoc", action="store_true", default=False, help="Include block/sector allocation info"
    )

    args = parser.parse_args()

    # Set up logging
    level = logging.WARNING
    if args.verbose:
        level = logging.INFO
    log = logging.getLogger("a2emutools")
    logging.basicConfig(filename=args.logfile, level=level)
    log.info(f"Command line args: {args}")

    log.info(f"Running command: {args.cmd}")
    if args.cmd == "info":
        cmd_info.cmd_info(args.container, vtoc=args.vtoc)
    elif args.cmd == "import":
        cmd_import.cmd_import(
            args.container,
            args.prefix,
            args.names,
            tokenize=args.tokenize,
            force_type=args.force_type,
        )
    elif args.cmd == "export":
        cmd_export.cmd_export(
            args.container,
            args.prefix,
            args.names,
            tokenize=args.tokenize,
            force_type=args.force_type,
        )
    elif args.cmd == "create":
        cmd_create.cmd_create(args.container, bootable=args.bootable, size=args.size)
    elif args.cmd == "mkdir":
        cmd_mkdir.cmd_mkdir(args.container, args.prefix, args.names, recurse=args.recurse)
    elif args.cmd == "rm":
        cmd_rm.cmd_rm(args.container, args.prefix, args.names, recurse=args.recurse)
    elif args.cmd == "ls":
        cmd_ls.cmd_ls(args.container, args.prefix, full=args.full, recurse=args.recurse)

    log.info("Command complete")

    exit(0)


if __name__ == "__main__":
    run()
