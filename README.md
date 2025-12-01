# u8g2 to BDF Converter

A Python tool to convert u8g2 fonts (embedded in C/H source files) to Glyph Bitmap Distribution Format (BDF).

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

```bash
python3 u8g2_to_bdf.py <input_file.c> -o <output_file.bdf>
```

### Example

To convert the provided example font:

```bash
python3 u8g2_to_bdf.py u8g2_font_logisoso16_tn.c -o u8g2_font_logisoso16_tn.bdf
```

## Implementation Details

The converter handles the u8g2 font format specification, including:
- Variable bit-width fields.
- Excess-K (biased) signed value encoding for coordinates.
- LSB-first bit stream decoding.
- RLE bitmap decompression.

## Limitations

- Currently supports the standard u8g2 format.
- "Jump Table" (u8g2 v2.23+) is not explicitly parsed but should be skipped if the font data follows the standard offset structure.
- Only tested with the provided example font.
