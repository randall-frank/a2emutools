from datetime import datetime
from enum import IntEnum
import logging
import struct
from typing import List, Optional, Tuple, Union

from a2emutools.container_formats import DiskImage
from a2emutools.filesystem import Access, DirObj, FileObj, FileSystem

log = logging.getLogger("a2emutools")

# ref:  https://www.kreativekorp.com/miscpages/a2info/filetypes.shtml
ProDOSFiletypesMap = dict(
    UNK=b"\x00",
    BAD=b"\x01",
    PCD=b"\x02",
    PTX=b"\x03",
    TXT=b"\x04",
    PDA=b"\x05",
    BIN=b"\x06",
    FNT=b"\x07",
    BA3=b"\x09",
    DA3=b"\x0A",
    WPF=b"\x0B",
    SOS=b"\x0C",
    DIR=b"\x0F",
    RPD=b"\x10",
    RPI=b"\x11",
    AFD=b"\x12",
    AFM=b"\x13",
    AFR=b"\x14",
    SCL=b"\x15",
    PFS=b"\x16",
    ADB=b"\x19",
    AWP=b"\x1A",
    ASP=b"\x1B",
    TDM=b"\x20",
    IPS=b"\x21",
    UPV=b"\x22",
    # 3SD=b'\x29',
    # 8SC=b'\x2A',
    # 8OB=b'\x2B',
    # 8IC=b'\x2C',
    # 8LD=b'\x2D',
    P8C=b"\x2E",
    OCR=b"\x41",
    FTD=b"\x42",
    GWP=b"\x50",
    GSS=b"\x51",
    GDB=b"\x52",
    DRW=b"\x53",
    GDP=b"\x54",
    HMD=b"\x55",
    EDU=b"\x56",
    STN=b"\x57",
    HLP=b"\x58",
    COM=b"\x59",
    CFG=b"\x5A",
    ANM=b"\x5B",
    MUM=b"\x5C",
    ENT=b"\x5D",
    DVU=b"\x5E",
    PRE=b"\x60",
    NCF=b"\x66",
    BIO=b"\x6B",
    DVR=b"\x6D",
    # PRE=b'\x6E',
    HDV=b"\x6F",
    GES=b"\x80",
    GEA=b"\x81",
    GEO=b"\x82",
    GED=b"\x83",
    GEF=b"\x84",
    GEP=b"\x85",
    GEI=b"\x86",
    GEX=b"\x87",
    GEV=b"\x89",
    GEC=b"\x8B",
    GEK=b"\x8C",
    GEW=b"\x8D",
    WP=b"\xA0",
    GSB=b"\xAB",
    TDF=b"\xAC",
    BDF=b"\xAD",
    SRC=b"\xB0",
    OBJ=b"\xB1",
    LIB=b"\xB2",
    S16=b"\xB3",
    RTL=b"\xB4",
    EXE=b"\xB5",
    PIF=b"\xB6",
    TIF=b"\xB7",
    NDA=b"\xB8",
    CDA=b"\xB9",
    TOL=b"\xBA",
    DRV=b"\xBB",
    LDF=b"\xBC",
    FST=b"\xBD",
    DOC=b"\xBF",
    PNT=b"\xC0",
    PIC=b"\xC1",
    ANI=b"\xC2",
    PAL=b"\xC3",
    OOG=b"\xC5",
    SCR=b"\xC6",
    CDV=b"\xC7",
    FON=b"\xC8",
    FND=b"\xC9",
    ICN=b"\xCA",
    MUS=b"\xD5",
    INS=b"\xD6",
    MDI=b"\xD7",
    SND=b"\xD8",
    DBM=b"\xDB",
    LBR=b"\xE0",
    ATK=b"\xE2",
    R16=b"\xEE",
    PAR=b"\xEF",
    CMD=b"\xF0",
    OVL=b"\xF1",
    UD2=b"\xF2",
    UD3=b"\xF3",
    UD4=b"\xF4",
    BAT=b"\xF5",
    UD6=b"\xF6",
    UD7=b"\xF7",
    PRG=b"\xF8",
    P16=b"\xF9",
    INT=b"\xFA",
    IVR=b"\xFB",
    BAS=b"\xFC",
    VAR=b"\xFD",
    REL=b"\xFE",
    SYS=b"\xFF",
)


class ProDOSFileType(IntEnum):
    DELETED: int = 0
    SEEDLING: int = 1
    SAPLING: int = 2
    TREE: int = 3
    SUBDIR: int = 0x0D
    SUBDIRHDR: int = 0x0E
    VOLUMEHDR: int = 0x0F


class ProDOSFileObj(FileObj):
    def __init__(self, file_system: "FileSystem", name: str, parent: "DirObj") -> None:
        super().__init__(file_system, name, parent)
        self._file_storage: ProDOSFileType = ProDOSFileType.SEEDLING

    def setup(self, block: int = 0, index: int = 0, **kwargs) -> None:
        """Initialize the file object from the file descriptive entry."""
        raw_block = self._fs.container.read_block(block)
        offset = index * 0x27 + 4  # skip first 4 bytes and entries are $27 bytes each
        # File descriptive entry
        tmp = struct.unpack_from(ProDOSFileSystem.file_entry_format, raw_block, offset)
        # tmp[0] = STORAGE_TYPE/NAME_LENGTH (1 byte)
        storage_type = int(tmp[0]) >> 4
        self._file_storage = ProDOSFileType(storage_type)
        # tmp[1] = FILE_NAME (15 bytes)
        self.name = tmp[1]
        # tmp[2] = FILE_TYPE (1 byte)
        self._file_type = ProDOSFileSystem.filetype_to_ext(tmp[2])
        # tmp[3] = KEY_POINTER (2 bytes)
        # tmp[4] = BLOCKS_USED (2 bytes)
        # tmp[5] = EOF lo (1 byte)
        # tmp[6] = EOF mid (1 byte)
        # tmp[7] = EOF hi (1 byte)
        self._file_size = (int(tmp[7]) << 16) | (int(tmp[6]) << 8) | int(tmp[5])
        # tmp[8] = CREATION_DATE (2 bytes)
        # tmp[9] = CREATION_TIME (2 bytes)
        self._create_time = ProDOSFileSystem.timestamp_to_datetime(int(tmp[8]), int(tmp[9]))
        # tmp[10] = VERSION  (1 byte)
        # tmp[11] = MIN_VERSION (1 byte)
        # tmp[12] = ACCESS (1 byte)
        self._access = ProDOSFileSystem.access_to_enum(int(tmp[12]))
        # tmp[13] = AUX_TYPE (2 bytes)
        self._aux_bits = int(tmp[13])
        # tmp[14] = MODIFICATION_DATE
        # tmp[15] = MODIFICATION_TIME
        self._create_time = ProDOSFileSystem.timestamp_to_datetime(int(tmp[14]), int(tmp[15]))
        # tmp[16] = HEADER_POINTER

    def _read(self) -> None:
        self.data = bytearray()
        self._synced = True

    def _write(self) -> None:
        self._synced = True

    def delete(self) -> None:
        pass


class ProDOSDirObj(DirObj):
    def __init__(
        self, file_system: "FileSystem", name: str = "", parent: Optional["DirObj"] = None
    ) -> None:
        super().__init__(file_system, name, parent)
        self._parent_block: int = 0
        self._parent_index: int = 0
        self._children: List[Union["DirObj", "FileObj"]] = []

    def setup(self, block: int = 0, **kwargs) -> None:
        """Initialize the directory object from the directory or volume header entry."""
        raw_block = self._fs.container.read_block(block)
        tmp = struct.unpack_from("<HH", raw_block, 0)
        next_block = tmp[1]  # Next block in linked list (tmp[0] is prev block)
        # this can be a volume header or directory entry
        tmp = struct.unpack_from(ProDOSFileSystem.volume_header_format, raw_block, 4)
        # tmp[0] = STORAGE_TYPE/NAME_LENGTH
        storage_type = (int(tmp[0]) & 0xF0) >> 4
        # The first block must be type 'f'
        if storage_type == ProDOSFileType.VOLUMEHDR:
            # Volume header
            # A little special case for the root directory
            # tmp[0] = STORAGE_TYPE/NAME_LENGTH
            name_length = int(tmp[0]) & 0x0F
            # tmp[1] = FILE_NAME (15 bytes)
            self.name = tmp[1].decode("ascii")[:name_length]
            # tmp[2] = reserved 8 bytes
            # date_date = tmp[3]  # 2 bytes
            # date_time = tmp[4]  # 2 bytes
            self._create_time = ProDOSFileSystem.timestamp_to_datetime(int(tmp[3]), int(tmp[4]))
            self._mod_time = self._create_time
            # tmp[5] = VERSION  (1 byte) (formatted by)
            # tmp[6] = MIN_VERSION
            prodos_version = int(tmp[6])
            if prodos_version != 0:
                raise RuntimeError(f"Invalid ProDOS volume header: {tmp[6]}.")
            # tmp[7] = ACCESS
            # tmp[8] = ENTRY_LENGTH = $27
            if int(tmp[8]) != 0x27:
                raise RuntimeError(f"Invalid ProDOS entry length: {tmp[8]}.")
            # tmp[9] = ENTRIES_PER_BLOCK = $0D?
            entries_per_block = int(tmp[9])
            # tmp[10] = FILE_COUNT
            # tmp[11] = BIT_MAP_POINTER
            # tmp[12] = TOTAL_BLOCKS
        elif storage_type == ProDOSFileType.SUBDIRHDR:
            # Directory header
            tmp = struct.unpack_from(ProDOSFileSystem.directory_header_format, raw_block, 4)
            # tmp[0] = STORAGE_TYPE/NAME_LENGTH (1 byte)
            name_length = int(tmp[0]) & 0x0F
            # tmp[1] = FILE_NAME (15 bytes)
            self.name = tmp[1].decode("ascii")[:name_length]
            # tmp[2] = fixed (1 byte) == $75
            if int(tmp[2]) not in [0x75, 0x76]:
                log.warning(f"Unexpected ProDOS directory header byte: {tmp[2]}.")
            # tmp[3] = RESERVED (7 bytes)
            # tmp[4] = CREATION_DATE (2 bytes)
            # tmp[5] = CREATION_TIME (2 bytes)
            self._create_time = ProDOSFileSystem.timestamp_to_datetime(int(tmp[4]), int(tmp[5]))
            self._mod_time = self._create_time
            # tmp[6] = VERSION  (1 byte)
            # tmp[7] = MIN_VERSION (1 byte)
            # tmp[8] = ACCESS (1 byte)
            # tmp[9] = ENTRY_LENGTH (1 byte)
            # tmp[10] = ENTRIES_PER_BLOCK (1 byte)
            entries_per_block = int(tmp[10])
            # tmp[11] = FILE_COUNT (2 bytes)
            # tmp[12] = PARENT_POINTER (2 bytes)
            self._parent_block = int(tmp[12])
            # tmp[13] = PARENT_ENTRY (1 byte)
            self._parent_index = int(tmp[13])
            # tmp[14] = PARENT_ENTRY_LENGTH (1 byte)
        else:
            raise RuntimeError("Invalid ProDOS volume/directory header.")
        # Read entries into children list
        while True:
            # raw_block is the first block of the directory/volume header
            # Each block has up to $0d entries of $27 bytes each following the header info
            for index in range(entries_per_block):
                offset = 4 + 0x27 * index
                etmp = struct.unpack_from(ProDOSFileSystem.file_entry_format, raw_block, offset)
                # etmp[0] = STORAGE_TYPE/NAME_LENGTH (1 byte)
                name_length = etmp[0] & 0x0F
                # etmp[1] = FILE_NAME (15 bytes)
                name = etmp[1].decode("ascii")[:name_length]
                entry_storage_type = (etmp[0] >> 4) & 0x0F
                if entry_storage_type == ProDOSFileType.DELETED:
                    continue
                elif entry_storage_type == ProDOSFileType.SUBDIR:
                    # tmp[3] = KEY_POINTER (2 bytes)
                    key_pointer = int(etmp[3])  # init the directory object from dir vol hdr
                    dchild = ProDOSDirObj(self._fs, name, self)
                    dchild.setup(key_pointer)
                    self._children.append(dchild)
                elif entry_storage_type == ProDOSFileType.SUBDIRHDR:
                    pass  # skip subdirectory headers in listing
                elif entry_storage_type == ProDOSFileType.VOLUMEHDR:
                    pass  # skip volume headers in listing
                else:
                    fchild = ProDOSFileObj(self._fs, name, self)
                    fchild.setup(block, index)  # init the file object from file entry
                    self._children.append(fchild)
            # if there are no more blocks, we're done
            if next_block == 0:
                break
            # jump to next block in linked list
            block = next_block
            raw_block = self._fs.container.read_block(block)
            etmp = struct.unpack_from("<HH", raw_block, 0)
            next_block = etmp[1]  # Next block in linked list (etmp[0] is prev block)

    def create_file(self, name: str, filetype: str) -> Optional["FileObj"]:
        return None

    def create_directory(self, name: str) -> Optional["DirObj"]:
        raise RuntimeError("Subdirectories are not supported on this filesystem.")

    def children(self) -> List[Union["DirObj", "FileObj"]]:
        return self._children

    def delete(self):
        pass


class ProDOSFileSystem(FileSystem):
    volume_header_format = "<B15s8sHHBBBBBHHH"  # note: past the block prev/next links
    directory_header_format = "<B15sB7sHHBBBBBHHBB"  # note: past the block prev/next links
    file_entry_format = "<B15sBHHBBBHHBBBHHHH"

    @staticmethod
    def is_format(container: "DiskImage") -> bool:
        info = ProDOSFileSystem._read_volume_directory(container)
        return info["valid"]

    @staticmethod
    def _read_volume_directory(container: "DiskImage") -> dict:
        """Read the ProDOS Volume Directory from block 2 of the container.
        Parameters
        ----------
        container : DiskImage
            The image container to read from.

        Returns
        -------
        dict
            A dictionary with volume information.
        """
        info = {"valid": False, "volume_name": ""}
        # Try to read the ProDOS Volume Directory from block 2.
        raw_block = container.read_block(2)
        tmp = struct.unpack_from(ProDOSFileSystem.volume_header_format, raw_block, 4)
        # tmp[0] = STORAGE_TYPE/NAME_LENGTH
        storage_type = tmp[0]
        # The first block must be type 'f'
        if (storage_type & 0xF0) != 0xF0:
            return info
        name_length = storage_type & 0x0F
        # tmp[1] = VOLUME_NAME (15 bytes)
        volume_name = tmp[1].decode("ascii")[:name_length]
        info["volume_name"] = volume_name
        # tmp[2] = reserved 8 bytes
        # date_date = tmp[3]  # 2 bytes
        # date_time = tmp[4]  # 2 bytes
        # tmp[5] = VERSION  (1 byte) (formatted by)
        # tmp[6] = MIN_VERSION
        prodos_version = int(tmp[6])
        if prodos_version != 0:
            return info
        # tmp[7] = ACCESS
        # tmp[8] = ENTRY_LENGTH = $27
        if int(tmp[8]) != 0x27:
            return info
        # tmp[9] = ENTRIES_PER_BLOCK = $0D?
        # tmp[10] = FILE_COUNT
        # tmp[11] = BIT_MAP_POINTER
        bitmap_start = int(tmp[11])
        info["bitmap_start"] = bitmap_start
        # tmp[12] = TOTAL_BLOCKS
        total_blocks = int(tmp[12])
        info["total_blocks"] = total_blocks
        info["valid"] = True
        return info

    @staticmethod
    def timestamp_to_datetime(date_date: int, date_time: int) -> "datetime":
        """Convert ProDOS date and time to a datetime object.
        Parameters
        ----------
        date_date : int
            The ProDOS date value.
        date_time : int
            The ProDOS time value.

        Returns
        -------
        datetime
            The corresponding datetime object.
        """
        # Date/time ProDOS bit layout
        # YYYY YYYM MMMD DDDD - year
        # 000H HHHH 00MM MMMM - time
        # Year conversion:
        # 40-99 = 1940-1999
        # 0-39 = 2000-2039
        day = date_date & 0x001F
        month = (date_date >> 5) & 0x000F
        year = (date_date >> 9) & 0x003F
        if year < 40:
            year = 2000 + year
        else:
            year = 1900 + year
        hour = (date_time >> 8) & 0x001F
        minute = date_time & 0x003F
        return datetime(year=year, month=month, day=day, hour=hour, minute=minute)

    @staticmethod
    def datetime_to_timestamp(date: "datetime") -> Tuple[int, int]:
        """Convert a datetime object to ProDOS date and time values.
        Parameters
        ----------
        date : datetime
            The datetime object to convert.
        Returns
        -------
        Tuple[int, int]
            A tuple containing the ProDOS date and time values.
        """
        year = date.year
        if year >= 2000:
            year = year - 2000
        else:
            year = year - 1900
        date_date = date.day | (date.month << 5) | (year << 9)
        date_time = date.minute | (date.hour << 8)
        return date_date, date_time

    def __init__(self, container: "DiskImage") -> None:
        super().__init__(container)
        self._type = "ProDOS"
        info = ProDOSFileSystem._read_volume_directory(container)
        self._volume_name: str = info["volume_name"]
        self._num_blocks: int = info.get("total_blocks", 0)
        self._bitmap_start: int = info.get("bitmap_start", 0)
        self._bitmap = bytearray(self._num_blocks)
        self._read_block_bitmap()
        self._root: Optional[ProDOSDirObj] = None

    def _read_block_bitmap(self) -> None:
        """Fill the block allocation bitmap from the container."""
        # first block of the bitmap
        blocknum = self._bitmap_start
        raw_block = self.container.read_block(blocknum)
        idx = 0  # first bit index
        for i in range(self._num_blocks):
            byte_idx = idx // 8
            bit_idx = idx % 8
            if raw_block[byte_idx] & (1 << bit_idx):
                self._bitmap[i] = 1
            else:
                self._bitmap[i] = 0
            idx += 1
            if idx == 512:  # next block
                blocknum += 1
                raw_block = self.container.read_block(blocknum)
                idx = 0

    @property
    def num_blocks(self) -> int:
        return self._num_blocks

    @property
    def root(self) -> "DirObj":
        if self._root is None:
            self._root = ProDOSDirObj(self)
            self._root.setup(2)  # volume header is at block 2
        return self._root

    def flush(self) -> None:
        pass

    def initialize(self) -> None:
        pass

    def info(self, vtoc: bool = False) -> str:
        s = super().info(vtoc=vtoc)
        s += f"\nVolume Name: {self.volume_name}"
        s += f"\nTotal Blocks: {self.num_blocks}"
        if vtoc:
            s += "\nBlock Allocation (*=used,.=free):\n"
            s += "      0000000000111111\n"
            s += "Blk#: 0123456789012345"
            for i in range(self.num_blocks):
                if i % 16 == 0:
                    s += f"\n{ i:04d}: "
                s += "." if self._bitmap[i] else "*"
        return s

    @staticmethod
    def ext_to_filetype(ext: str) -> bytes:
        if ext.startswith("pd_"):
            t = int(ext[2:])
            return bytes(t)
        return ProDOSFiletypesMap.get(ext, ProDOSFiletypesMap["BIN"])

    @staticmethod
    def filetype_to_ext(ftype: int) -> str:
        for key, value in ProDOSFiletypesMap.items():
            if int(value[0]) == ftype:
                return key
        return f"pd_{ftype:03d}"

    @staticmethod
    def access_to_enum(access: int) -> "Access":
        v = 0
        if access & 0x01:
            v |= Access.READ
        if access & 0x02:
            v |= Access.WRITE
        if access & 0x20:
            v |= Access.CHANGED
        if access & 0x40:
            v |= Access.RENAME
        if access & 0x80:
            v |= Access.DELETE
        return Access(v)

    @staticmethod
    def enum_to_access(access: "Access") -> int:
        v = 0
        if access & Access.READ:
            v |= 0x01
        if access & Access.WRITE:
            v |= 0x02
        if access & Access.CHANGED:
            v |= 0x20
        if access & Access.RENAME:
            v |= 0x40
        if access & Access.DELETE:
            v |= 0x80
        return v
