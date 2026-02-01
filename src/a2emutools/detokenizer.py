import sys
from typing import List

# Applesoft BASIC Tokens ($80 - $EA)
TOKENS = {
    0x80: "END",
    0x81: "FOR",
    0x82: "NEXT",
    0x83: "DATA",
    0x84: "INPUT",
    0x85: "DEL",
    0x86: "DIM",
    0x87: "READ",
    0x88: "GR",
    0x89: "TEXT",
    0x8A: "PR#",
    0x8B: "IN#",
    0x8C: "CALL",
    0x8D: "PLOT",
    0x8E: "HLIN",
    0x8F: "VLIN",
    0x90: "HGR2",
    0x91: "HGR",
    0x92: "HCOLOR=",
    0x93: "HPLOT",
    0x94: "DRAW",
    0x95: "XDRAW",
    0x96: "HTAB",
    0x97: "HOME",
    0x98: "ROT=",
    0x99: "SCALE=",
    0x9A: "SHLOAD",
    0x9B: "TRACE",
    0x9C: "NOTRACE",
    0x9D: "NORMAL",
    0x9E: "INVERSE",
    0x9F: "FLASH",
    0xA0: "COLOR=",
    0xA1: "POP",
    0xA2: "VTAB",
    0xA3: "HIMEM:",
    0xA4: "LOMEM:",
    0xA5: "ONERR",
    0xA6: "RESUME",
    0xA7: "RECALL",
    0xA8: "STORE",
    0xA9: "SPEED=",
    0xAA: "LET",
    0xAB: "GOTO",
    0xAC: "RUN",
    0xAD: "IF",
    0xAE: "RESTORE",
    0xAF: "&",
    0xB0: "GOSUB",
    0xB1: "RETURN",
    0xB2: "REM",
    0xB3: "STOP",
    0xB4: "ON",
    0xB5: "WAIT",
    0xB6: "LOAD",
    0xB7: "SAVE",
    0xB8: "DEF",
    0xB9: "POKE",
    0xBA: "PRINT",
    0xBB: "CONT",
    0xBC: "LIST",
    0xBD: "CLEAR",
    0xBE: "GET",
    0xBF: "NEW",
    0xC0: "TAB(",
    0xC1: "TO",
    0xC2: "FN",
    0xC3: "SPC(",
    0xC4: "THEN",
    0xC5: "AT",
    0xC6: "NOT",
    0xC7: "STEP",
    0xC8: "+",
    0xC9: "-",
    0xCA: "*",
    0xCB: "/",
    0xCC: "^",
    0xCD: "AND",
    0xCE: "OR",
    0xCF: ">",
    0xD0: "=",
    0xD1: "<",
    0xD2: "SGN",
    0xD3: "INT",
    0xD4: "ABS",
    0xD5: "USR",
    0xD6: "FRE",
    0xD7: "SCRN(",
    0xD8: "PDL",
    0xD9: "POS",
    0xDA: "SQR",
    0xDB: "RND",
    0xDC: "LOG",
    0xDD: "EXP",
    0xDE: "COS",
    0xDF: "SIN",
    0xE0: "TAN",
    0xE1: "ATN",
    0xE2: "PEEK",
    0xE3: "LEN",
    0xE4: "STR$",
    0xE5: "VAL",
    0xE6: "ASC",
    0xE7: "CHR$",
    0xE8: "LEFT$",
    0xE9: "RIGHT$",
    0xEA: "MID$",
}


def detokenize(data: bytes) -> str:
    """
    Detokenizes an Applesoft BASIC program from its binary representation.

    1. Reads the binary data of an Applesoft BASIC program.
    2. Parses the line structure (link pointer, line number, content).
    3. Converts tokens back to their ASCII keyword equivalents.
    Returns the detokenized program as a string.

    Parameters
    ----------
    data : bytes
        The binary data of the Applesoft BASIC program.

    Returns
    -------
    str
        The detokenized Applesoft BASIC program as a string.
    """

    output = ""

    # we assume the 16bit length has been stripped from the data already
    offset = 0

    while offset < len(data):
        # 1. Read Link Pointer (2 bytes)
        link = data[offset] + (data[offset + 1] << 8)
        if link == 0:  # End of program
            break
        offset += 2

        # 2. Read Line Number (2 bytes)
        line_num = data[offset] + (data[offset + 1] << 8)
        offset += 2

        # 3. Read Line Content until Null byte
        line_text: List[str] = []
        while data[offset] != 0:
            byte = data[offset]
            if byte in TOKENS:
                if byte == 0xAA:  # LET token is optional
                    offset += 1
                    continue
                if line_text and line_text[-1] != " ":
                    line_text.append(" ")
                line_text.append(TOKENS[byte] + " ")
            else:
                line_text.append(chr(byte & 0x7F))  # Convert to 7-bit ASCII
            offset += 1

        # 4. Print the reconstructed line
        output += f"{line_num} {''.join(line_text)}\n"

        # Move past the null terminator
        offset += 1

    return output


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python detokenizer.py <filename>")
    else:
        try:
            with open(sys.argv[1], "rb") as f:
                data = f.read()
        except FileNotFoundError:
            print(f"Error: File '{sys.argv[1]}' not found.")
            sys.exit(-1)
        ascii_app = detokenize(data)
        print(ascii_app)
