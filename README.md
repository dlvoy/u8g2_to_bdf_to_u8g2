# u8g2 to BDF to u8g2 Converter

A Python tool to convert u8g2 fonts (embedded in C/H source files) to Glyph Bitmap Distribution Format (BDF) and vice versa.

## Features

- Extracts u8g2 font data from C source files (looking for `const uint8_t ... = "..."`).
- Decodes u8g2 font header and glyph data.
- Handles Run-Length Encoded (RLE) bitmaps.
- Generates standard BDF output compatible with font viewers and editors.

## Requirements

- Python 3.x
- No external dependencies (uses standard library).

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

### Convert BDF file to u8g2 C format

```bash
python3 u8g2_to_bdf.py input.bdf -e -o output.c
```

**Optional: Specify Unicode range to export**

```bash
python3 u8g2_to_bdf.py input.bdf -e -m "32-126,160-255" -o output.c
```

### Command Line Options

**For decoding (u8g2 to BDF):**
- `input_file`: The u8g2 C source file to convert
- `-o, --output`: Output BDF file path (default: output.bdf)

**For encoding (BDF to u8g2):**
- `input_file`: The BDF file to convert
- `-e, --encode`: Enable BDF to u8g2 encoding mode
- `-o, --output`: Output C file path (default: output.c)
- `-m, --map`: Unicode range to export (e.g., "32-126,160-255")

## Implementation Details

### Decoding (u8g2 to BDF)

- **Bit Reading**: Uses LSB-first bit order for reading u8g2 font data
- **RLE Decompression**: Decodes run-length encoded glyph bitmaps using m0/m1 parameters
- **Signed Values**: Handles Excess-K encoding for signed glyph metrics (x, y offsets)
- **BDF Generation**: Creates valid BDF font files with proper bounding boxes and metrics

### Encoding (BDF to u8g2)

- **BDF Parsing**: Reads BDF font files and extracts glyph metrics and bitmap data
- **RLE Compression**: Compresses glyph bitmaps using optimal m0/m1 parameters
  - Tests all combinations (m0: 2-8, m1: 2-7) to find the most compact encoding
  - Normalizes run lengths to fit within bit field constraints
  - Implements unary repeat encoding for consecutive identical pairs
- **Bit Writing**: Uses LSB-first bit order matching u8g2 format
- **Variable Bit Widths**: Calculates optimal bit widths for glyph properties (W, H, X, Y, D)
- **Header Generation**: Creates 23-byte u8g2 font header with all required parameters
- **C Source Output**: Generates properly formatted C source files with escaped hex strings

## Limitations

- Currently supports the standard u8g2 format.
- "Jump Table" (u8g2 v2.23+) is not explicitly parsed but should be skipped if the font data follows the standard offset structure.
- Only tested with the provided example font.
