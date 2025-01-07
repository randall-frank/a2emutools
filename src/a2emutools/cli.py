import argparse

from a2emutools import __version__

"""
Command line tool:  python -m cli

{pathexp} - pathname
          - pathname/file{.dsk,.po,.do,.2mg,.hdv}:/path 
          -
          
Commands:

    ls {pathexp} [--full] [--json] [--info]
    rm {pathexp} [--recursive]
    mkdir {pathexp} [--all]
    cp {pathexp} {pathexp} [--tokenize] [--force_type type]
    cat {pathexp} [--tokenize]

"""

def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('-V', '--version', action='version',
                        version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument('--verbose', action='store_true', default=False, help='Run in verbose mode')

    cmd_parsers = parser.add_subparsers(help='Commands', dest='cmd')
    cmd_parsers.required = True

    ls_parser = cmd_parsers.add_parser('ls', help='List directory contents')
    ls_parser.add_argument("source", help="Directory or container/path to list", default=None)
    ls_parser.add_argument('--json', action='store_true', default=False, help='Encode output in json')
    ls_parser.add_argument('--full', action='store_true', default=False, help='Include file details')
    ls_parser.add_argument('--info', action='store_true', default=False, help='Include disk/device info')

    rm_parser = cmd_parsers.add_parser('rm', help='Delete a file/directory')
    rm_parser.add_argument("source", help="Directory or container/path to delete", default=None)
    rm_parser.add_argument('--recurse', action='store_true', default=False, help='Delete recursively')

    mkdir_parser = cmd_parsers.add_parser('mkdir', help='Create a directory')
    mkdir_parser.add_argument("source", help="Directory or container/path to create", default=None)
    mkdir_parser.add_argument('--recurse', action='store_true', default=False,
                              help='Create intermediate directories')

    cat_parser = cmd_parsers.add_parser('cat', help='Send file contents to stdout')
    cat_parser.add_argument("source", help="Filename or container/path to cat", default=None)
    cat_parser.add_argument('--no-tokenize', dest='tokenize', action='store_false', default=True,
                            help='No not apply detokenization to .bas files')

    cp_parser = cmd_parsers.add_parser('cp', help='Copy a file from one device to another')
    cp_parser.add_argument("source", help="Filename or container/path to copy from", default=None)
    cp_parser.add_argument("target", help="Filename or container/path to copy to", default=None)
    cp_parser.add_argument('--no-tokenize', dest='tokenize', action='store_false', default=True,
                           help='No not apply detokenization to .bas files')
    cp_parser.add_argument('--force_type', type=str, default="",
                           help='Override the natural input file type to use provided type instead')

    args = parser.parse_args()

    print(args)

    exit(0)


if __name__ == '__main__':
    run()
