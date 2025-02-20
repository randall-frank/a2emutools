import argparse

from a2emutools import __version__, cmd_cat, cmd_cp, cmd_info, cmd_ls, cmd_mkdir, cmd_rm

"""
Command line tool:  python -m cli

Pathname specification:

Native container/filesystem
/foo/bar or C:/foo/bar -> filename 'bar' in directory container 'foo'

If a directory name, then the file name is ''.

Container files:
/foo/file{.dsk,.po,.do,.2mg,.hdv}:/path
C:/foo/file{.dsk,.po,.do,.2mg,.hdv}:/path

ext is the tuple: ('.dsk', '.po', '.do', '.hdv', '.2mg')
Detect using: endswith '{ext' or contains:  '{ext}:/'

Commands:

    ls {pathexp} [--full] [--json] [--recurse]
    rm {pathexp} [--recurse]
    mkdir {pathexp} [--recurse]
    cp {pathexp} {pathexp} [--tokenize] [--force_type type]
    cat {pathexp} [--tokenize]
    info {pathexp} [--vtoc]

"""


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )
    parser.add_argument("--verbose", action="store_true", default=False, help="Run in verbose mode")

    cmd_parsers = parser.add_subparsers(help="Commands", dest="cmd")
    cmd_parsers.required = True

    ls_parser = cmd_parsers.add_parser("ls", help="List directory contents")
    ls_parser.add_argument("source", help="Directory or container/path to list", default=None)
    ls_parser.add_argument(
        "--json", action="store_true", default=False, help="Encode output in json"
    )
    ls_parser.add_argument(
        "--full", action="store_true", default=False, help="Include file details"
    )
    ls_parser.add_argument(
        "--recurse", action="store_true", default=False, help="Delete recursively"
    )

    rm_parser = cmd_parsers.add_parser("rm", help="Delete a file/directory")
    rm_parser.add_argument("source", help="Directory or container/path to delete", default=None)
    rm_parser.add_argument(
        "--recurse", action="store_true", default=False, help="Delete recursively"
    )

    mkdir_parser = cmd_parsers.add_parser("mkdir", help="Create a directory")
    mkdir_parser.add_argument("source", help="Directory or container/path to create", default=None)
    mkdir_parser.add_argument(
        "--recurse", action="store_true", default=False, help="Create intermediate directories"
    )

    cat_parser = cmd_parsers.add_parser("cat", help="Send file contents to stdout")
    cat_parser.add_argument("source", help="Filename or container/path to cat", default=None)
    cat_parser.add_argument(
        "--no-tokenize",
        dest="tokenize",
        action="store_false",
        default=True,
        help="No not apply detokenization to .bas files",
    )

    cp_parser = cmd_parsers.add_parser("cp", help="Copy a file from one device to another")
    cp_parser.add_argument("source", help="Filename or container/path to copy from", default=None)
    cp_parser.add_argument("target", help="Filename or container/path to copy to", default=None)
    cp_parser.add_argument(
        "--no-tokenize",
        dest="tokenize",
        action="store_false",
        default=True,
        help="No not apply detokenization to .bas files",
    )
    cp_parser.add_argument(
        "--force_type",
        type=str,
        default="",
        help="Override the natural input file type to use provided type instead",
    )

    info_parser = cmd_parsers.add_parser(
        "info", help="Return detailed container/filesystem information"
    )
    info_parser.add_argument("source", help="Container object pathname", default=None)

    info_parser.add_argument(
        "--vtoc", action="store_true", default=False, help="Include block/sector allocation info"
    )

    args = parser.parse_args()

    print(args)

    if args.cmd == "info":
        cmd_info.cmd_info(args.source, vtoc=args.vtoc, verbose=args.verbose)
    elif args.cmd == "cp":
        cmd_cp.cmd_cp(
            args.source,
            args.target,
            tokenize=args.tokenize,
            force_type=args.force_type,
            verbose=args.verbose,
        )
    elif args.cmd == "cat":
        cmd_cat.cmd_cat(args.source, tokenize=args.tokenize, verbose=args.verbose)
    elif args.cmd == "mkdir":
        cmd_mkdir.cmd_mkdir(args.source, recurse=args.recurse, verbose=args.verbose)
    elif args.cmd == "rm":
        cmd_rm.cmd_rm(args.source, recurse=args.recurse, verbose=args.verbose)
    elif args.cmd == "ls":
        cmd_ls.cmd_ls(
            args.source, full=args.full, json=args.json, recurse=args.recurse, verbose=args.verbose
        )
    exit(0)


if __name__ == "__main__":
    run()
