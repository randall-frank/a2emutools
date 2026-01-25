import re
import sys
from typing import List

# Applesoft BASIC Tokens ($80 - $EA)
TOKENS = {
    "END": 0x80,
    "FOR": 0x81,
    "NEXT": 0x82,
    "DATA": 0x83,
    "INPUT": 0x84,
    "DEL": 0x85,
    "DIM": 0x86,
    "READ": 0x87,
    "GR": 0x88,
    "TEXT": 0x89,
    "PR#": 0x8A,
    "IN#": 0x8B,
    "CALL": 0x8C,
    "PLOT": 0x8D,
    "HLIN": 0x8E,
    "VLIN": 0x8F,
    "HGR2": 0x90,
    "HGR": 0x91,
    "HCOLOR=": 0x92,
    "HPLOT": 0x93,
    "DRAW": 0x94,
    "XDRAW": 0x95,
    "HTAB": 0x96,
    "HOME": 0x97,
    "ROT=": 0x98,
    "SCALE=": 0x99,
    "SHLOAD": 0x9A,
    "TRACE": 0x9B,
    "NOTRACE": 0x9C,
    "NORMAL": 0x9D,
    "INVERSE": 0x9E,
    "FLASH": 0x9F,
    "COLOR=": 0xA0,
    "POP": 0xA1,
    "VTAB": 0xA2,
    "HIMEM:": 0xA3,
    "LOMEM:": 0xA4,
    "ONERR": 0xA5,
    "RESUME": 0xA6,
    "RECALL": 0xA7,
    "STORE": 0xA8,
    "SPEED=": 0xA9,
    "LET": 0xAA,
    "GOTO": 0xAB,
    "RUN": 0xAC,
    "IF": 0xAD,
    "RESTORE": 0xAE,
    "&": 0xAF,
    "GOSUB": 0xB0,
    "RETURN": 0xB1,
    "REM": 0xB2,
    "STOP": 0xB3,
    "ON": 0xB4,
    "WAIT": 0xB5,
    "LOAD": 0xB6,
    "SAVE": 0xB7,
    "DEF": 0xB8,
    "POKE": 0xB9,
    "PRINT": 0xBA,
    "CONT": 0xBB,
    "LIST": 0xBC,
    "CLEAR": 0xBD,
    "GET": 0xBE,
    "NEW": 0xBF,
    "TAB(": 0xC0,
    "TO": 0xC1,
    "FN": 0xC2,
    "SPC(": 0xC3,
    "THEN": 0xC4,
    "AT": 0xC5,
    "NOT": 0xC6,
    "STEP": 0xC7,
    "+": 0xC8,
    "-": 0xC9,
    "*": 0xCA,
    "/": 0xCB,
    "^": 0xCC,
    "AND": 0xCD,
    "OR": 0xCE,
    ">": 0xCF,
    "=": 0xD0,
    "<": 0xD1,
    "SGN": 0xD2,
    "INT": 0xD3,
    "ABS": 0xD4,
    "USR": 0xD5,
    "FRE": 0xD6,
    "SCRN(": 0xD7,
    "PDL": 0x8,
    "POS": 0xD9,
    "SQR": 0xDA,
    "RND": 0xDB,
    "LOG": 0xDC,
    "EXP": 0xDD,
    "COS": 0xDE,
    "SIN": 0xDF,
    "TAN": 0xE0,
    "ATN": 0xE1,
    "PEEK": 0xE2,
    "LEN": 0xE3,
    "STR$": 0xE4,
    "VAL": 0xE5,
    "ASC": 0xE6,
    "CHR$": 0xE7,
    "LEFT$": 0xE8,
    "RIGHT$": 0xE9,
    "MID$": 0xEA,
}

# Sort keywords by length (longest first) to avoid partial matches (e.g., 'AT' in 'ATN')
KEYWORDS = sorted(TOKENS.keys(), key=len, reverse=True)


def _tokenize_line(text):
    """Converts a line of text into Applesoft bytes (handles REM and quotes)."""
    result = bytearray()
    i = 0
    in_quotes = False
    is_rem = False

    while i < len(text):
        char = text[i]

        # Handle Quotes
        if char == '"':
            in_quotes = not in_quotes
            result.append(ord(char))
            i += 1
            continue

        # If inside quotes or we already hit a REM, just copy ASCII
        if in_quotes or is_rem:
            result.append(ord(char))
            i += 1
            continue

        # Check for keywords
        found_keyword = False
        upper_text = text[i:].upper()
        for kw in KEYWORDS:
            if upper_text.startswith(kw):
                result.append(TOKENS[kw])
                i += len(kw)
                found_keyword = True
                if kw == "REM":
                    is_rem = True
                break

        if not found_keyword:
            result.append(ord(char))
            i += 1

    return result


def tokenize(lines: List[str]) -> bytearray:
    """
    Tokenizes a list of Applesoft BASIC lines into binary format.

    Parameters
    ----------
    lines : List[str]
        List of lines of Applesoft BASIC code as strings.

    Returns
    -------
    bytearray
        The tokenized binary representation of the Applesoft BASIC program.
    """

    start_address = 0x0801
    current_address = start_address
    program_bytes = bytearray()

    # ProDOS/DOS 3.3 Load Address Header ($01 $08 for $0801)
    header = bytearray([start_address & 0xFF, (start_address >> 8) & 0xFF])

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Split line number from statement
        match = re.match(r"(\d+)\s*(.*)", line)
        if not match:
            continue

        line_num = int(match.group(1))
        content = match.group(2)

        # Tokenize content
        tokenized_content = _tokenize_line(content)

        # Calculate next line pointer
        # 2 bytes (link) + 2 bytes (line#) + content length + 1 byte (null)
        line_length = 2 + 2 + len(tokenized_content) + 1
        next_line_address = current_address + line_length

        # Build binary line
        line_bin = bytearray()
        line_bin.append(next_line_address & 0xFF)  # Link Low
        line_bin.append((next_line_address >> 8) & 0xFF)  # Link High
        line_bin.append(line_num & 0xFF)  # Line # Low
        line_bin.append((line_num >> 8) & 0xFF)  # Line # High
        line_bin += tokenized_content
        line_bin.append(0x00)  # End of line

        program_bytes += line_bin
        current_address = next_line_address

    # End of program marker (00 00)
    program_bytes += bytearray([0x00, 0x00])

    return header + program_bytes


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tokenizer.py <input.txt> <output.bin>")
    else:
        try:
            with open(sys.argv[1], "r") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(-1)
        bindata = tokenize(lines)
        with open(sys.argv[2], "wb") as f:  # type: ignore
            f.write(bindata)  # type: ignore
        print(f"Successfully tokenized to {sys.argv[2]}")
