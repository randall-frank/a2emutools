from enum import IntEnum
import os.path
import stat
import struct
from typing import Any, Tuple


class ContainerFormat(IntEnum):
    # Container format enums
    RAW: int = 0  # .do .dsk, .po, .hdv
    FILE_2MG: int = 1  # .2mg
    LOCAL_FS: int = 2  # the local file system


class SectorOrder(IntEnum):
    # Sector ordering enums: these follow the 2mg convention
    DOS33: int = 0  # DOS 3.3 raw sector order (track_num*16*256+sector_num*256=offset)
    PRODOS: int = 1  # ProDOS sequential block order (block_num*512=offset)
    NIB: int = 2  # Raw disk bits...
    NONE: int = 3  # Used by ContainerFormat.LOCAL_FS


class Flags2MG(IntEnum):
    # flags for 2mg file format
    LOCKED: int = 1 << 31
    ISVOLNUM: int = 1 << 8
    VOLNUM_MASK: int = 255


class FileSystemType(IntEnum):
    """
    This is the Apple 2 file system that is present on the
    disk image.   At present, DOS3.3 and ProDOS are supported.
    Potential future expansions could include Apple Pascal, DOS3.2,
    CP/M (see CiderPress?).
    """

    DOS33: int = 0  # DOS3.3 filesystem
    PRODOS: int = 1  # ProDOS filesystem
    NATIVE: int = 2  # Used by ContainerFormat.LOCAL_FS
    UNKNOWN: int = 3  # Unable to determine the filesystem


class DiskImage:
    # General byte signature our app will use
    app_signature_2mg: bytes = b"a2em"
    # 2MG format info
    # 64 bytes in the header
    magic_2mg: bytes = b"2IMG"
    header_struct_format_2mg: str = "<4s4shhIiiii8i"

    # Conversion tables from blocks to sectors and reverse.  These are
    # used to support different FileSystemType in conjunction with
    # different SectorOrder schemes in containers.

    # A track is 8 sequential blocks.  These 8 blocks are built from these
    # consecutive pairs of sectors.
    block_sectors = (
        (0x00, 0x0E),  # block 0
        (0x0D, 0x0C),  # block 1
        (0x0B, 0x0A),  # block 2
        (0x09, 0x08),  # block 3
        (0x07, 0x06),  # block 4
        (0x05, 0x04),  # block 5
        (0x03, 0x02),  # block 6
        (0x01, 0x0F),  # block 7
    )
    # Given a sector, this is the relative block number and offset within the block of the sector
    sector_blocks = (
        (0x00, 0),  # sector 0
        (0x07, 0),  # sector 1
        (0x06, 256),  # sector 2
        (0x06, 0),  # sector 3
        (0x05, 256),  # sector 4
        (0x05, 0),  # sector 5
        (0x04, 256),  # sector 6
        (0x04, 0),  # sector 7
        (0x03, 256),  # sector 8
        (0x03, 0),  # sector 9
        (0x02, 256),  # sector a
        (0x02, 0),  # sector b
        (0x01, 256),  # sector c
        (0x01, 0),  # sector d
        (0x00, 256),  # sector e
        (0x07, 256),  # sector f
    )

    def __init__(self, filename: str, pathname: str = "") -> None:
        # This is based on the 2MG header, we use the same fields for
        # all the other containers
        self._2mgheader_size: int = 64
        self._2mgheader_version: int = 1

        # General features
        self._volume_number: int = 0
        self._file_locked: bool = False
        self._pathname: str = pathname
        self._container_name: str = filename

        # what type of container is open
        self._container_format: ContainerFormat = ContainerFormat.RAW

        # the sector order of the data in self._file_data
        self._sector_order: SectorOrder = SectorOrder.DOS33
        self._file_data: bytearray = bytearray()
        self._filesystem: FileSystemType = FileSystemType.DOS33

        # Two options:
        # 1) name of container
        # 2) directory name (for the local filesystem rooted at filename)
        if os.path.isdir(filename):
            #
            self._container_format = ContainerFormat.LOCAL_FS
            self._sector_order = SectorOrder.NONE
            self._filesystem = FileSystemType.NATIVE
        else:
            # Read the container
            self.read_container(filename)

        from a2emutools import known_filesystems

        # build the file system interface object
        self._fs_object: "Any" = known_filesystems[self._filesystem](self)  # type: ignore

    @property
    def filesystem(self) -> "Any":  # type: ignore
        return self._fs_object

    @property
    def data(self) -> bytearray:
        return self._file_data

    @data.setter
    def data(self, data: bytearray) -> None:
        self._file_data = data

    @property
    def pathname(self) -> str:
        return self._pathname

    @property
    def container_name(self) -> str:
        return self._container_name

    @property
    def sector_order(self) -> SectorOrder:
        return self._sector_order

    @property
    def volume_number(self) -> int:
        return self._volume_number

    @volume_number.setter
    def volume_number(self, volnum: int) -> None:
        if self._filesystem != SectorOrder.DOS33:
            raise RuntimeError("Unable to set volume number on non-DOS 3.3 volume")
        self._volume_number = volnum

    @property
    def locked(self) -> bool:
        return self._file_locked

    @locked.setter
    def locked(self, lock_value: bool) -> None:
        self._file_locked = lock_value

    @property
    def num_blocks(self) -> int:
        return len(self._file_data) // 512

    @property
    def num_tracks(self) -> int:
        return len(self._file_data) // (256 * self.num_sectors)

    @property
    def num_sectors(self) -> int:
        return 16

    def _track_sector_to_block(self, track: int, sector: int) -> Tuple[int, int]:
        """
        Given a track and sector number, return with the block number and what half
        of the block the sector belongs to.  Assume that the data is in ProDOS block
        order.

        Parameters
        ----------
        track : int
            The track number
        sector : int
            The sector number

        Returns
        -------
        int, int
            The block number and the offset (0 or 256) into the block.

        """
        local_block, offset = self.sector_blocks[sector]
        block = track * 8 + local_block
        return block, offset

    def read_sector(self, track: int, sector: int) -> bytearray:
        """
        Return the 256 bytes at a specific track and sector.

        Parameters
        ----------
        track : int
            The track number
        sector : int
            The sector number

        Returns
        -------
        bytearray
            The 256 bytes stored at that sector
        """
        if (track < 0) or (track >= self.num_tracks):
            raise RuntimeError(f"Invalid track number: {track}")
        if (sector < 0) or (sector >= self.num_sectors):
            raise RuntimeError(f"Invalid sector number: {sector}")
        if self._sector_order == SectorOrder.DOS33:
            offset = track * (16 * 256) + (sector * 256)
            return self._file_data[offset : offset + 256]
        blocknum, local_offset = self._track_sector_to_block(track, sector)
        offset = blocknum * 512 + local_offset
        return self._file_data[offset : offset + 256]

    def write_sector(self, track: int, sector: int, data: bytearray) -> None:
        """
        Change the contents of the specified sector to the 256 bytes passed in 'data'.

        Parameters
        ----------
        track : int
            The track number
        sector : int
            The sector number
        data : bytearray
            The data to place in the specified sector
        """
        if len(data) != 256:
            raise RuntimeError("The data block must be 256 bytes long")
        if (track < 0) or (track >= self.num_tracks):
            raise RuntimeError(f"Invalid track number: {track}")
        if (sector < 0) or (sector >= self.num_sectors):
            raise RuntimeError(f"Invalid sector number: {sector}")
        if self._sector_order == SectorOrder.DOS33:
            offset = track * (16 * 256) + (sector * 256)
            self._file_data[offset : offset + 256] = data[0:256]
            return
        blocknum, local_offset = self._track_sector_to_block(track, sector)
        offset = blocknum * 512 + local_offset
        self._file_data[offset : offset + 256] = data[0:256]

    def _block_to_track_sectors(self, blocknum: int) -> Tuple[int, int, int]:
        """
        Convert a block number into the track and sector pair (low, high) that
        would be used to rebuild the block from a pair of sectors.  This
        allows for access to a ProDOS filesystem stored in an image that was
        generated in DOS sector order (e.g. a ProDOS volume in a DOS 3.3 .dsk file).

        Parameters
        ----------
        blocknum: int
            The block number to convert

        Returns
        -------
        (int, int, int)
            The track number and the two sector numbers (low and high)
        """
        track = blocknum // 8  # 8 blocks per track
        sectors = self.block_sectors[blocknum % 8]
        return track, sectors[0], sectors[1]

    def read_block(self, blocknum: int) -> bytearray:
        """
        Given a block number, return the 512 bytes corresponding to that block.

        Parameters
        ----------
        blocknum : int
            The block number

        Returns
        -------
        bytearray
            The contents of the block

        """
        if (blocknum < 0) or (blocknum >= self.num_blocks):
            raise RuntimeError(f"Invalid block number: {blocknum}")
        if self._sector_order == SectorOrder.PRODOS:
            offset = blocknum * 512
            return self._file_data[offset : offset + 512]
        # convert block number into track, (sector lo, sector hi)
        track, sector_low, sector_high = self._block_to_track_sectors(blocknum)
        offset0 = track * (256 * 16) + sector_low * 256
        offset1 = track * (256 * 16) + sector_high * 256
        return self._file_data[offset0 : offset0 + 256] + self._file_data[offset1 : offset1 + 256]

    def write_block(self, blocknum: int, data: bytearray) -> None:
        """
        Save the passed block (512 bytes) into the current image.

        Parameters
        ----------
        blocknum : int
            The block number
        data : bytearray
            The block data (512 bytes)
        """
        if len(data) != 512:
            raise RuntimeError("The data block must be 512 bytes long")
        if (blocknum < 0) or (blocknum >= self.num_blocks):
            raise RuntimeError(f"Invalid block number: {blocknum}")
        if self._sector_order == SectorOrder.PRODOS:
            offset = blocknum * 512
            self._file_data[offset : offset + 512] = data
            return
        # convert block number into track, (sector lo, sector hi)
        track, sector_low, sector_high = self._block_to_track_sectors(blocknum)
        offset0 = track * (256 * 16) + sector_low * 256
        offset1 = track * (256 * 16) + sector_high * 256
        self._file_data[offset0 : offset0 + 256] = data[0:256]
        self._file_data[offset1 : offset1 + 256] = data[256:512]

    def read_container(self, filename: str) -> None:
        """
        Read the specified file data into memory and do a basic
        parameter setup: format check, fields, etc

        Parameters
        ----------
        filename: str
            The filename to read.
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".2mg":
            self._container_format = ContainerFormat.FILE_2MG
            with open(filename, "rb") as f:
                header = f.read(self._2mgheader_size)
                data_offset, data_length = self._parse_header(header)
                f.seek(data_offset)
                self._file_data = bytearray(f.read(data_length))
        elif ext in (".po", ".hdv"):
            with open(filename, "rb") as f:
                self._file_data = bytearray(f.read())
            self._volume_number = 0
            self._set_locked_by_stat(filename)
            self._container_format = ContainerFormat.RAW
            self._sector_order = SectorOrder.PRODOS
        elif ext in (".do", ".dsk"):
            with open(filename, "rb") as f:
                self._file_data = bytearray(f.read())
            self._volume_number = 254
            self._set_locked_by_stat(filename)
            self._container_format = ContainerFormat.RAW
            self._sector_order = SectorOrder.DOS33
        else:
            raise RuntimeError(f"Unsupported file format extension: {ext}")
        # Figure out what filesystem is stored in the container image bits (self._file_data)
        self._guess_data_format()

    def _guess_data_format(self) -> None:
        from a2emutools.dos33 import DOS33FileSystem
        from a2emutools.filesystem import FileSystem
        from a2emutools.prodos import ProDOSFileSystem

        # we have a container and the sector order (for low level sector/block access) is
        # set in self._data_format.  We still need to figure out what filesystem (DOS3.3 or ProDOS)
        # is there.
        if ProDOSFileSystem.is_format(self):
            self._filesystem = FileSystemType.PRODOS
        elif DOS33FileSystem.is_format(self):
            self._filesystem = FileSystemType.DOS33
        elif FileSystem.is_format(self):
            self._filesystem = FileSystemType.NATIVE
        else:
            self._filesystem = FileSystemType.UNKNOWN

    def _set_locked_by_stat(self, filename: str) -> None:
        """
        Set the _file_locked member using the OS level file
        writeable bit as a proxy

        Parameters
        ----------
        filename: str
            The filename to use to set the flag from
        """
        stats = os.stat(filename)
        perm = stat.S_IMODE(stats.st_mode)
        self._file_locked = True
        # Use owner as proxy
        if perm & stat.S_IWUSR:
            self._file_locked = False

    def save_container(self, filename: str) -> None:
        if self._container_format == ContainerFormat.LOCAL_FS:
            raise RuntimeError("The local filesystem does not support container saving.")
        with open(filename, "wb") as f:
            # for non-2mg containers build_header returns an empty bytearray
            header = self._build_header()
            if len(header):
                f.write(header)
            f.write(self._file_data)

    def _build_header(self) -> bytearray:
        if self._container_format != ContainerFormat.FILE_2MG:
            return bytearray()
        flags: int = 0
        if self._file_locked:
            flags |= Flags2MG.LOCKED
        if self._volume_number > 0:
            flags |= Flags2MG.ISVOLNUM
            flags |= self._volume_number & Flags2MG.VOLNUM_MASK
        num_blocks = 0
        if self._sector_order == SectorOrder.PRODOS:
            num_blocks = len(self.data) // 512
        header = bytearray(self._2mgheader_size)
        struct.pack_into(
            self.header_struct_format_2mg,
            header,
            0,
            self.magic_2mg,
            self.app_signature_2mg,
            self._2mgheader_size,
            self._2mgheader_version,
            self._sector_order,
            flags,
            num_blocks,
            self._2mgheader_size,
            len(self.data),
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        return header

    def _parse_header(self, data: bytes) -> Tuple[int, int]:
        """
        Parse a .2mg header.  Fill in the values like self._sector_order
        and flags like locking and the volume number.  Return the size
        of the reported data payload.

        Parameters
        ----------
        data: bytes
            The header bytes

        Returns
        -------
        int, int
            The offset to the data payload and the size of the data payload in bytes
        """
        tmp = struct.unpack(self.header_struct_format_2mg, data)
        if tmp[0] != self.magic_2mg:
            raise RuntimeError("Input file is not in .2img format (invalid magic).")
        # [1]    self.app_signature_2mg,
        if tmp[2] != self._2mgheader_size:
            raise RuntimeError("Unknown .2mg header size.")
        if tmp[3] != self._2mgheader_version:
            raise RuntimeError("Unknown .2mg header version.")
        self._sector_order = tmp[4]
        # handle flags
        flags = tmp[5]
        self._file_locked = (flags & Flags2MG.LOCKED) != 0
        self._volume_number = 0
        if flags & Flags2MG.ISVOLNUM:
            self._volume_number = flags & Flags2MG.VOLNUM_MASK
        # [6]    Number of blocks
        data_offset = tmp[7]
        data_size = tmp[8]
        return data_offset, data_size


container_extensions = {
    ".po": ContainerFormat.RAW,
    ".do": ContainerFormat.RAW,
    ".dsk": ContainerFormat.RAW,
    ".hdv": ContainerFormat.RAW,
    ".2mg": ContainerFormat.FILE_2MG,
}


def create_image(name: str) -> "DiskImage":
    container_name, pathname, _ = parse_pathname(name)
    image = DiskImage(container_name, pathname=pathname)
    return image


def parse_pathname(name: str) -> Tuple[str, str, "ContainerFormat"]:
    """
    Given an encoded string, return the name of the local container
    (or directory) and the path inside the container.  It will also
    return the container format: raw, 2mg, native.

    If the ContainerFormat is NATIVE, then the first string in the
    tuple will be the directory name that will serve as the container
    root.

    Pathname specification:

    Native container/filesystem
    /foo/bar or C:/foo/bar -> filename 'bar' in directory container 'foo'

    If a directory name, then the file name is ''.

    Container files:
    /foo/file{.dsk,.po,.do,.2mg,.hdv}:/path
    C:/foo/file{.dsk,.po,.do,.2mg,.hdv}:/path

    ext is the tuple: ('.dsk', '.po', '.do', '.hdv', '.2mg')
    Detect using: endswith '{ext' or contains:  '{ext}:/'

    Parameters
    ----------
    name: str
        The string name to be parsed.

    Returns
    -------
    (str, str, ContainerFormat)
        The first string is the path to the container. The second is
        the filename/path to the object in the container.  The third
        value is the type of container.

    Raises
    ------
    RuntimeError
        If the string cannot be parsed or the containers do not
        exist.

    """
    # The fallback is a non-existent file in the LOCAL_FS
    container_name = os.path.dirname(name)
    pathname = os.path.basename(name)
    container_type = ContainerFormat.LOCAL_FS

    # If the whole thing is a physical directory, that is the simplest case
    # Use the local filesystem rooted at the directory.
    if os.path.isdir(name):
        return name, "", ContainerFormat.LOCAL_FS

    # It could just be a raw container file, no path in the container
    if os.path.isfile(name):
        _, ext = os.path.splitext(name)
        if ext in container_extensions:
            return name, "", container_extensions[ext]

    # split into "container" and "path", but container must exist
    # path need not.
    for ext in container_extensions.keys():
        # Look for 'foo.{ext}:/'
        tag = f"{ext}:/"
        idx = name.find(tag)
        if idx > 0:
            pathname = name[idx + len(tag) :]
            container_name = name[: idx + len(tag) - 2]
            container_type = container_extensions[ext]
            # the container file must exist (and be a file)
            if os.path.isfile(container_name):
                return container_name, pathname, container_type

    # Local filesystem fallback case: the directory still must exist, but the
    # pathname can be set, but non-existent.
    if not os.path.isdir(container_name):
        raise RuntimeError(
            f"A directory named {container_name} could not be found (local filesystem)"
        )
    return container_name, pathname, container_type
