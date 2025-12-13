# u8g2 to BDF to u8g2 Converter

A Python tool to convert u8g2 fonts (embedded in C/H source files) to Glyph Bitmap Distribution Format (BDF) and vice versa, with full Unicode support including extended Latin characters and Polish diacritics.

## Features

- **Bidirectional conversion**: u8g2 ↔ BDF with full fidelity
- **Unicode support**: Handles characters beyond ASCII (0-127)
  - Latin-1 Supplement (128-255)
  - Latin Extended-A (0x100-0x17F) - Polish, Czech, Hungarian, etc.
  - Latin Extended-B (0x180-0x24F)
  - Any Unicode codepoint supported by u8g2
- **PostScript character names**: Automatic mapping for ENCODING -1 characters
  - Supports U+XXXX format (e.g., U+0104)
  - Supports uni+XXXX format
  - Supports PostScript names (aogonek, cacute, lslash, etc.)
- **Space character preservation**: Keeps space (U+0020) even when empty
- **RLE compression**: Optimal run-length encoding with automatic m0/m1 parameter selection
- **Jump table support**: Handles u8g2 v2.23+ jump tables for Unicode blocks

## Requirements

- Python 3.x
- No external dependencies (uses standard library)

## Setup

### Linux / macOS

1.  Clone or download the repository.
2.  (Optional) Create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  Run the script directly.

### Windows

1.  Clone or download the repository.
2.  (Optional) Create a virtual environment:
    ```cmd
    python -m venv venv
    venv\Scripts\activate
    ```
3.  Run the script using `python`.

## Usage

### Convert u8g2 C file to BDF

```bash
python3 u8g2_to_bdf.py u8g2_font_logisoso16_tn.c -o output.bdf
```

This will decode the u8g2 font and generate a BDF file with:
- All ASCII characters (0-127)
- Extended Latin characters (128-255)
- Unicode characters > 255 (Latin Extended-A, etc.)

### Convert BDF file to u8g2 C format

```bash
python3 u8g2_to_bdf.py input.bdf -e -o output.c
```

This will encode the BDF font to u8g2 format, automatically detecting:
- Characters with ENCODING >= 0 (standard Unicode)
- Characters with ENCODING -1 and name U+XXXX
- Characters with ENCODING -1 and PostScript names

**Optional: Specify Unicode range to export**

```bash
python3 u8g2_to_bdf.py input.bdf -e -m "32-126,260-263,321-322" -o output.c
```

### Command Line Options

**For decoding (u8g2 to BDF):**
- `input_file`: The u8g2 C source file to convert
- `-o, --output`: Output BDF file path (default: output.bdf)

**For encoding (BDF to u8g2):**
- `input_file`: The BDF file to convert
- `-e, --encode`: Enable BDF to u8g2 encoding mode
- `-o, --output`: Output C file path (default: output.c)
- `-m, --map`: Unicode range to export (e.g., "32-126,260-263" for basic ASCII + Polish Ą,ą,Ć,ć)

## Implementation Details

### Decoding (u8g2 to BDF)

- **Block 1 Parsing**: Decodes glyphs with Unicode <= 255 (1-byte encoding)
- **Block 2 Parsing**: Decodes glyphs with Unicode > 255 (2-byte encoding)
- **Jump Table Detection**: Automatically detects and skips u8g2 v2.23+ jump tables
- **Bit Reading**: Uses LSB-first bit order for reading u8g2 font data
- **RLE Decompression**: Decodes run-length encoded glyph bitmaps using m0/m1 parameters
- **Signed Values**: Handles Excess-K encoding for signed glyph metrics (x, y offsets)
- **BDF Generation**: Creates valid BDF font files with proper bounding boxes and metrics
- **Statistics**: Reports glyph count by Unicode range

### Encoding (BDF to u8g2)

- **Unicode Detection**: Three methods for determining character encoding:
  1. ENCODING >= 0: Direct Unicode value
  2. ENCODING -1 with U+XXXX or uni+XXXX format
  3. ENCODING -1 with PostScript name (e.g., aogonek → U+0105)
- **PostScript Mapping**: Built-in dictionary with 100+ common character names
  - Polish: aogonek, cacute, eogonek, lslash, nacute, oacute, sacute, zacute, zdotaccent
  - Other Latin: aacute, ccedilla, ntilde, oslash, scaron, etc.
  - Special characters: space, exclam, dollar, at, etc.
- **Empty Glyph Handling**: Filters out empty glyphs but preserves space character
- **BDF Parsing**: Reads BDF font files and extracts glyph metrics and bitmap data
- **RLE Compression**: Compresses glyph bitmaps using optimal m0/m1 parameters
  - Tests all combinations (m0: 2-8, m1: 2-7) to find the most compact encoding
  - Normalizes run lengths to fit within bit field constraints
  - Implements unary repeat encoding for consecutive identical pairs
- **Block Organization**: Separates glyphs into Block 1 (≤255) and Block 2 (>255)
- **Bit Writing**: Uses LSB-first bit order matching u8g2 format
- **Variable Bit Widths**: Calculates optimal bit widths for glyph properties (W, H, X, Y, D)
- **Header Generation**: Creates 23-byte u8g2 font header with all required parameters
- **C Source Output**: Generates properly formatted C source files with octal-escaped strings
- **Statistics**: Reports glyph count by Unicode range

## Unicode Support

### Supported Character Ranges

The tool fully supports bidirectional conversion for:

- **ASCII (0x00-0x7F)**: Basic Latin
- **Latin-1 (0x80-0xFF)**: Western European characters
- **Latin Extended-A (0x100-0x17F)**: Central/Eastern European characters
  - Polish: Ą ą Ć ć Ę ę Ł ł Ń ń Ó ó Ś ś Ź ź Ż ż
  - Czech, Hungarian, Romanian, Croatian, etc.
- **Latin Extended-B (0x180-0x24F)**: Additional Latin characters
- **Any Unicode**: The format supports any Unicode codepoint

### PostScript Character Names

Built-in support for common PostScript names used in BDF files:

| PostScript Name | Unicode | Character |
|----------------|---------|-----------|
| Aogonek | 0x0104 | Ą |
| aogonek | 0x0105 | ą |
| Cacute | 0x0106 | Ć |
| cacute | 0x0107 | ć |
| Eogonek | 0x0118 | Ę |
| eogonek | 0x0119 | ę |
| Lslash | 0x0141 | Ł |
| lslash | 0x0142 | ł |
| Nacute | 0x0143 | Ń |
| nacute | 0x0144 | ń |
| Oacute | 0x00D3 | Ó |
| oacute | 0x00F3 | ó |
| Sacute | 0x015A | Ś |
| sacute | 0x015B | ś |
| Zacute | 0x0179 | Ź |
| zacute | 0x017A | ź |
| Zdotaccent | 0x017B | Ż |
| zdotaccent | 0x017C | ż |

Plus many more for other Latin Extended characters and special symbols.

## Examples

### Converting a font with Polish characters

```bash
# BDF to u8g2 (encoding)
python3 u8g2_to_bdf.py polish_font.bdf -e -o polish_font.c

# Output:
# Parsing BDF file: polish_font.bdf
# Parsed 108 glyphs from BDF:
#   ASCII (0-127): 90 glyphs
#   Latin-1 (128-255): 2 glyphs
#   Latin Extended-A (0x100-0x17F): 16 glyphs
# Parsed 108 glyphs.
# Optimal RLE: m0=2, m1=2
# Written to polish_font.c

# u8g2 to BDF (decoding)
python3 u8g2_to_bdf.py polish_font.c -o polish_font_decoded.bdf

# Output:
# Parsing C file: polish_font.c
# Read 1088 bytes of font data.
# Parsed 108 glyphs:
#   ASCII (0-127): 90 glyphs
#   Latin-1 (128-255): 2 glyphs
#   Latin Extended-A (0x100-0x17F): 16 glyphs
# Written to polish_font_decoded.bdf
```

## Limitations

- Currently supports the standard u8g2 format (BBX Mode 0, 1, 2, 3).
- Jump table (u8g2 v2.23+) is detected and handled for Unicode blocks.
- Tested with fonts containing ASCII, Latin-1, and Latin Extended-A characters.
- Character filtering preserves space (U+0020) even when empty.

## Format Documentation

See `format/U8G2_FORMAT.md` for detailed information about the u8g2 font format structure.
