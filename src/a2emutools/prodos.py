from datetime import datetime
import struct
from typing import List, Optional, Tuple, Union

from a2emutools.container_formats import DiskImage
from a2emutools.filesystem import DirObj, FileObj, FileSystem

# ref:  https://www.kreativekorp.com/miscpages/a2info/filetypes.shtml
ProDOSFiletypesMap = dict(
    UNK=b"x00",
    BAD=b"x01",
    PCD=b"x02",
    PTX=b"x03",
    TXT=b"x04",
    PDA=b"x05",
    BIN=b"x06",
    FNT=b"x07",
    BA3=b"x09",
    DA3=b"x0A",
    WPF=b"x0B",
    SOS=b"x0C",
    DIR=b"x0F",
    RPD=b"x10",
    RPI=b"x11",
    AFD=b"x12",
    AFM=b"x13",
    AFR=b"x14",
    SCL=b"x15",
    PFS=b"x16",
    ADB=b"x19",
    AWP=b"x1A",
    ASP=b"x1B",
    TDM=b"x20",
    IPS=b"x21",
    UPV=b"x22",
    # 3SD=b'x29',
    # 8SC=b'x2A',
    # 8OB=b'x2B',
    # 8IC=b'x2C',
    # 8LD=b'x2D',
    P8C=b"x2E",
    OCR=b"x41",
    FTD=b"x42",
    GWP=b"x50",
    GSS=b"x51",
    GDB=b"x52",
    DRW=b"x53",
    GDP=b"x54",
    HMD=b"x55",
    EDU=b"x56",
    STN=b"x57",
    HLP=b"x58",
    COM=b"x59",
    CFG=b"x5A",
    ANM=b"x5B",
    MUM=b"x5C",
    ENT=b"x5D",
    DVU=b"x5E",
    PRE=b"x60",
    NCF=b"x66",
    BIO=b"x6B",
    DVR=b"x6D",
    # PRE=b'x6E',
    HDV=b"x6F",
    GES=b"x80",
    GEA=b"x81",
    GEO=b"x82",
    GED=b"x83",
    GEF=b"x84",
    GEP=b"x85",
    GEI=b"x86",
    GEX=b"x87",
    GEV=b"x89",
    GEC=b"x8B",
    GEK=b"x8C",
    GEW=b"x8D",
    WP=b"xA0",
    GSB=b"xAB",
    TDF=b"xAC",
    BDF=b"xAD",
    SRC=b"xB0",
    OBJ=b"xB1",
    LIB=b"xB2",
    S16=b"xB3",
    RTL=b"xB4",
    EXE=b"xB5",
    PIF=b"xB6",
    TIF=b"xB7",
    NDA=b"xB8",
    CDA=b"xB9",
    TOL=b"xBA",
    DRV=b"xBB",
    LDF=b"xBC",
    FST=b"xBD",
    DOC=b"xBF",
    PNT=b"xC0",
    PIC=b"xC1",
    ANI=b"xC2",
    PAL=b"xC3",
    OOG=b"xC5",
    SCR=b"xC6",
    CDV=b"xC7",
    FON=b"xC8",
    FND=b"xC9",
    ICN=b"xCA",
    MUS=b"xD5",
    INS=b"xD6",
    MDI=b"xD7",
    SND=b"xD8",
    DBM=b"xDB",
    LBR=b"xE0",
    ATK=b"xE2",
    R16=b"xEE",
    PAR=b"xEF",
    CMD=b"xF0",
    OVL=b"xF1",
    UD2=b"xF2",
    UD3=b"xF3",
    UD4=b"xF4",
    BAT=b"xF5",
    UD6=b"xF6",
    UD7=b"xF7",
    PRG=b"xF8",
    P16=b"xF9",
    INT=b"xFA",
    IVR=b"xFB",
    BAS=b"xFC",
    VAR=b"xFD",
    REL=b"xFE",
    SYS=b"xFF",
)


class ProDOSFileObj(FileObj):
    def __init__(self, file_system: "FileSystem", name: str, parent: "DirObj") -> None:
        super().__init__(file_system, name, parent)

    def _read_info(self):
        pass

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
        self._type: str = "ProDOS"

    def create_file(self, name: str, filetype: str) -> Optional["FileObj"]:
        return None

    def create_directory(self, name: str) -> Optional["DirObj"]:
        raise RuntimeError("Subdirectories are not supported on this filesystem.")

    def children(self) -> List[Union["DirObj", "FileObj"]]:
        return []

    def delete(self):
        pass


class ProDOSFileSystem(FileSystem):
    volume_directory_header_format = "<ic15c8cHHcccccHHH"

    @staticmethod
    def is_format(container: "DiskImage") -> bool:
        # Try to read the ProDOS Volume Directory from block 2.
        raw_block = container.read_block(2)
        tmp = struct.unpack(ProDOSFileSystem.volume_directory_header_format, raw_block)
        # tmp[0] = unknown 4 bytes
        storage_type = int(tmp[1])
        # The first block must be type 'f'
        if (storage_type & 0xF0) != 0xF0:
            return False
        name_length = storage_type & 0x0F
        volume_name = tmp[2]
        volume_name = volume_name[:name_length]
        # tmp[3] = reserved 8 bytes
        # date_date = tmp[5]  # 2 bytes
        # date_time = tmp[6]  # 2 bytes
        # VERSION ProDOS 1.0 version is 0.
        prodos_version = int(tmp[7])
        if prodos_version != 0:
            return False
        # tmp[8] = MIN_VERSION
        # tmp[9] = ACCESS
        # tmp[10] = ENTRY_LENGTH = $27
        if int(tmp[10]) != 0x27:
            return False
        # tmp[11] = ENTRIES_PER_BLOCK = $0D?
        # tmp[12] = FILE_COUNT
        # tmp[13] = BIT_MAP_POINTER
        # tmp[14] = TOTAL_BLOCKS
        return True

    @staticmethod
    def timestamp_to_datetime(date_date: int, date_time: int) -> "datetime":
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

    @property
    def root(self) -> "DirObj":
        return DirObj(self)

    def flush(self) -> None:
        pass

    def initialize(self) -> None:
        pass

    def info(self) -> str:
        s = f"{self.type}\n"
        s += f"Container={self.container.container_name}"
        return s

    def ext_to_filetype(self, ext: str) -> bytes:
        if ext.startswith("pd_"):
            t = int(ext[2:])
            return bytes(t)
        return ProDOSFiletypesMap.get(ext, ProDOSFiletypesMap["BIN"])

    def filetype_to_ext(self, ftype: bytes) -> str:
        for key, value in ProDOSFiletypesMap.items():
            if value == ftype[0]:
                return key
        return f"pd_{int(ftype[0]):03d}"
