import sys
import re
import argparse

class BitReader:
    def __init__(self, data):
        self.data = data
        self.byte_idx = 0
        self.bit_idx = 0 # 0 to 7, 7 is MSB? No, u8g2 usually LSB first or MSB? 
        # "The data format of U8G2 fonts is based on the BDF font format. Its glyph bitmaps are compressed with a run-length-encoding algorithm"
        # "All following glyph data does not rely on byte boundaries"
        # Usually font data is read bit by bit.
        # Let's assume standard order for now, will verify.
        # u8g2_font_decode_get_unsigned_bits in u8g2 source would be the reference.
        # Looking at u8g2_font.c in the repo (not provided here, but from general knowledge/spec):
        # bits are often consumed from MSB to LSB or LSB to MSB.
        # "Glyph bitmaps are 1-Bit horizontally packed bitmaps"
        
    def read_bits(self, num_bits):
        val = 0
        for i in range(num_bits):
            if self.byte_idx >= len(self.data):
                return 0 # End of stream
            
            # LSB first
            bit = (self.data[self.byte_idx] >> self.bit_idx) & 1
            val |= (bit << i)
            
            self.bit_idx += 1
            if self.bit_idx == 8:
                self.bit_idx = 0
                self.byte_idx += 1
        return val

    def read_signed_bits(self, num_bits):
        val = self.read_bits(num_bits)
        val -= (1 << (num_bits - 1))
        return val

def parse_c_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # regex to find the array
    # const uint8_t u8g2_font_logisoso16_tn[287] U8G2_FONT_SECTION("u8g2_font_logisoso16_tn") = 
    #   "\22\0\3\3\4\5\3\5\5\11\23\0\377\20\374\20\0\0\0\0\0\1\2 \5\0\10\65*\21x\272"
    # ...
    #   "\377\377\0";
    
    # We need to extract the string content.
    # It might be split across lines.
    
    match = re.search(r'=\s*((?:"(?:[^"\\]|\\.)*"\s*)+);', content, re.DOTALL)
    if not match:
        print("Could not find font data array in file. Regex match failed.")
        print(f"Content snippet: {content[:200]}...")
        return None, None

    raw_string = match.group(1)
    # Clean up the string: remove quotes and whitespace between parts
    # "part1"
    # "part2" -> "part1part2"
    
    # This is a bit tricky because of escapes.
    # We should probably just eval it if it's safe-ish, or parse it manually.
    # Since it's C string literal syntax, python's ast.literal_eval might not work directly if it has C-specific escapes (like octal \123).
    # Python supports octal escapes in strings too.
    
    # Let's try to join them and use a custom parser or simple eval if format allows.
    # The example has "\22\0...", which is octal. Python supports this.
    
    # Remove newlines and surrounding whitespace between quotes
    combined_string = re.sub(r'"\s*"', '', raw_string)
    # Remove leading/trailing quotes
    combined_string = combined_string.strip().strip('"')
    
    # Now we have a string like \22\0\3...
    # We need to convert this to bytes.
    # We can use python's string escape decoding.
    
    # In Python 3, we can use:
    # bytes(combined_string, "utf-8").decode("unicode_escape").encode("latin1")
    # But wait, \22 is octal 22 = 18 decimal.
    # Python's unicode_escape handles octal.
    
    try:
        # We need to wrap it in quotes to make it a valid python string literal for evaluation,
        # OR just process it.
        # simpler:
        # Use a dummy byte string literal
        # b = b"\22\0..."
        
        # But we have it as a string variable.
        # Let's try:
        decoded_data = b""
        
        # Manual parsing of octal/hex escapes might be safer and robust
        i = 0
        while i < len(combined_string):
            if combined_string[i] == '\\':
                i += 1
                if i >= len(combined_string): break
                c = combined_string[i]
                if '0' <= c <= '7':
                    # Octal, up to 3 digits
                    octal_str = c
                    i += 1
                    if i < len(combined_string) and '0' <= combined_string[i] <= '7':
                        octal_str += combined_string[i]
                        i += 1
                        if i < len(combined_string) and '0' <= combined_string[i] <= '7':
                            octal_str += combined_string[i]
                            i += 1
                    decoded_data += bytes([int(octal_str, 8)])
                elif c == 'x':
                    # Hex
                    i += 1
                    hex_str = combined_string[i:i+2]
                    decoded_data += bytes([int(hex_str, 16)])
                    i += 2
                elif c == '\\':
                    decoded_data += b'\\'
                    i += 1
                elif c == '"':
                    decoded_data += b'"'
                    i += 1
                else:
                    # other escapes like \n, \r, but font data usually uses octal/hex for binary
                    # or just literal char
                    # If it's just a char escaped, take it?
                    # But wait, standard C escapes: \n \t etc.
                    # The example file only shows octal so far.
                    pass 
            else:
                decoded_data += bytes([ord(combined_string[i])])
                i += 1
                
        return decoded_data, "font_name_placeholder" # TODO extract name
        
    except Exception as e:
        print(f"Error parsing string data: {e}")
        return None, None

def main():
    parser = argparse.ArgumentParser(description='Convert u8g2 font C file to BDF.')
    parser.add_argument('input_file', help='Input C file containing u8g2 font')
    parser.add_argument('-o', '--output', help='Output BDF file', default='output.bdf')
    
    args = parser.parse_args()
    
    print(f"Parsing file: {args.input_file}")
    data, name = parse_c_file(args.input_file)
    if not data:
        print("Failed to read data")
        sys.exit(1)
        
    print(f"Read {len(data)} bytes of font data.")
    

    # Parse Header
    # 0: n glyphs
    # 1: bbx mode
    # 2: m0
    # 3: m1
    # 4: bitcntW
    # 5: bitcntH
    # 6: bitcntX
    # 7: bitcntY
    # 8: bitcntD
    # 9: bbx width
    # 10: bbx height
    # 11: bbx x offset
    # 12: bbx y offset
    # 13: ascent A
    # 14: descent g
    # 15: ascent (
    # 16: descent (
    # 17-18: offset A
    # 19-20: offset a
    # 21-22: offset 0x100
    
    if len(data) < 23:
        print("Data too short for header")
        return

    n_glyphs = data[0]
    bbx_mode = data[1]
    m0 = data[2]
    m1 = data[3]
    bitcntW = data[4]
    bitcntH = data[5]
    bitcntX = data[6]
    bitcntY = data[7]
    bitcntD = data[8]
    
    font_bbx_w = data[9]
    font_bbx_h = data[10]
    font_bbx_x = data[11]
    font_bbx_y = data[12] # signed?
    
    ascent_A = data[13]
    descent_g = data[14] # signed?
    
    # Offsets are 16-bit big endian usually? Or little?
    # Spec doesn't say endianness explicitly in the table, but "u8g2_font_get_word" suggests it.
    # Usually u8g2 is for 8-bit MCUs, often little endian, but let's check.
    # In the example file:
    # 17-18: \374\20 -> 0xfc 0x10. 
    # If big endian: 0xfc10 (64528) - huge.
    # If little endian: 0x10fc (4348).
    # The file size is 287 bytes. So 4348 is also too big.
    # Wait, "Array offset of glyph 'A'".
    # Maybe it's relative to something?
    # "The offsets are relative to the end of the font header."
    # Header is 23 bytes.
    # 0x10fc is still too big.
    # Let's look at the data again.
    # \22\0\3\3\4\5\3\5\5\11\23\0\377\20\374\20\0\0\0\0\0\1\2
    # 0: 22 (18 glyphs? comment says 18/527) -> Matches.
    # 1: 0 (Mode 0) -> Matches.
    # 2: 3 (m0)
    # 3: 3 (m1)
    # 4: 4 (W)
    # 5: 5 (H)
    # 6: 3 (X)
    # 7: 5 (Y)
    # 8: 5 (D)
    # 9: 11 (BBX W)
    # 10: 23 (BBX H)
    # 11: 0 (BBX X)
    # 12: 255 (-1? BBX Y) -> 0xff. Signed byte -1.
    # 13: 20 (Ascent A)
    # 14: 252 (-4? Descent g) -> 0xfc. Signed byte -4.
    # 15: 20 (Ascent ()
    # 16: 0 (Descent ()
    # 17: 0
    # 18: 0
    # 19: 0
    # 20: 0
    # 21: 0
    # 22: 1
    # Wait, the example string:
    # "\22\0\3\3\4\5\3\5\5\11\23\0\377\20\374\20\0\0\0\0\0\1\2"
    # 0: 18
    # 1: 0
    # 2: 3
    # 3: 3
    # 4: 4
    # 5: 5
    # 6: 3
    # 7: 5
    # 8: 5
    # 9: 9 (\11) -> 9? Comment says 23-230...
    # 10: 19 (\23) -> 19.
    # 11: 0
    # 12: 255 (-1)
    # 13: 16 (\20)
    # 14: 252 (\374) (-4)
    # 15: 16 (\20)
    # 16: 0
    # 17: 0
    # 18: 0
    # 19: 0
    # 20: 0
    # 21: 0
    # 22: 1
    
    # Offset 0x100 is 0x0100 (big endian) or 0x0001 (little endian)?
    # If 0x0001: 1 byte offset?
    # If 0x0100: 256 bytes offset?
    # The file is 287 bytes. 23 + 256 = 279. Possible.
    # Let's assume Big Endian for now based on 0x00 0x01 looking like 1.
    # But wait, byte 21 is 0, byte 22 is 1.
    # If Big Endian: 0x0001 = 1.
    # If Little Endian: 0x0100 = 256.
    # Given the file size, 256 seems more likely to point to something at the end (0x100 is usually not in small fonts, but maybe it points to the start of the unicode table?).
    
    # "The address for the unicode glyphs is the end of the initial data structure plus the 16 bit offset from bytes 21/22"
    # If offset is 1, then 23+1 = 24.
    # If offset is 256, then 23+256 = 279.
    
    # Let's look at byte 23 (index 23).
    # The string continues: " \5\0\10\65*\21x\272..."
    # ' ' is 32. \5 is 5.
    # 32 could be the unicode for space!
    # If so, the glyphs start immediately at 23.
    # So offset to 0x100 being 1 or 256 doesn't affect where the FIRST glyph is.
    # The first glyph is at 23.
    
    # Glyph format:
    # 0: Unicode (1 or 2 bytes?)
    # "All glyphs start with the unicode (1 byte) and the offset to the next glyph (1 byte)."
    # "All glyphs start with the unicode (2 bytes) and the offset to the next glyph (1 byte)." (for the 0x100 block?)
    
    # The spec is a bit confusing: "The glyphs start immediately after the end of the initial data structure."
    # "All glyphs start with the unicode (1 byte)..."
    # But then "The address for the unicode glyphs is the end of the initial data structure plus the 16 bit offset from bytes 21/22... All glyphs start with the unicode (2 bytes)..."
    
    # It seems there are two blocks?
    # Block 1: 0-255, 1 byte unicode.
    # Block 2: 0x100+, 2 byte unicode.
    
    # Let's try to parse sequentially from 23.
    
    idx = 23
    glyphs = []
    
    while idx < len(data):
        # Check if we are in the 0x100 block?
        # The spec says "The glyphs start immediately...".
        # Let's assume 1-byte unicode first.
        
        # But wait, 0x100 offset in header points to the 2-byte unicode block?
        # If byte 21=0, 22=1.
        # If it is Big Endian 1: 23+1 = 24. That would overlap with the first block? Unlikely.
        # If it is Little Endian 256: 23+256 = 279.
        # At 279:
        # The file ends at 287.
        # 279 is near the end.
        # Let's check bytes at 279.
        # The string ends with: ... \2\0\0\0\4\377\377\0
        # We need to see the exact bytes.
        
        # Let's just implement a loop that reads glyphs.
        # We need to know when to stop or switch mode.
        # "offset to next glyph" is key.
        
        # Glyph header:
        # Unicode (1 byte)
        # Offset (1 byte)
        
        if idx >= len(data): break
        
        uc = data[idx]
        if uc == 0: # End of block? Or just 0 char?
            # Usually 0 is not a valid char in this context or it's a terminator?
            # "Glyph bitmaps don't contain end markers"
            pass
            
        next_offset = data[idx+1]
        if next_offset == 0:
            # End of glyphs?
            break
            
        # Glyph data starts at idx + 2
        # Length is next_offset.
        # Next glyph is at idx + next_offset.
        
        # Wait, "data[off+1] has the offset to the next glyph, which is at data[off+data[off+1]]"
        # So if next_offset is 5, next glyph is at idx + 5.
        
        # Let's decode the glyph at idx.
        # Variable bit widths.
        
        glyph_data_start = idx + 2
        # The glyph data contains:
        # bitcntW bits: width
        # bitcntH bits: height
        # bitcntX bits: x offset
        # bitcntY bits: y offset
        # bitcntD bits: pitch
        # Then bitmap.
        
        # We need a BitReader starting at glyph_data_start.
        br = BitReader(data[glyph_data_start:])
        
        w = br.read_bits(bitcntW)
        h = br.read_bits(bitcntH)
        x = br.read_signed_bits(bitcntX)
        y = br.read_signed_bits(bitcntY)
        d = br.read_signed_bits(bitcntD)
        
        
        # Bitmap decoding
        # RLE.
        # m0 bits: zeros
        # m1 bits: ones
        # n bits: repeat
        
        # We need to decode w*h bits.
        target_bits = w * h
        current_bits = 0
        bitmap = [] # 0 or 1
        
        while current_bits < target_bits:
            # Read 0s
            run_0 = br.read_bits(m0)
            # Read 1s
            run_1 = br.read_bits(m1)
            # Read repeat count
            # "n Bits == 1 (to be counted) denoting the number of repetitions of the sequence"
            # "1 Bit == 0 as stop marker for each sequence"
            
            # This part is tricky.
            # We read bits until we find a 0?
            # "n Bits == 1 ... and 1 Bit == 0 as stop marker"
            # This sounds like unary encoding?
            # 0 -> 0 repeats (just the initial run)
            # 10 -> 1 repeat
            # 110 -> 2 repeats
            
            repeat = 0
            while True:
                bit = br.read_bits(1)
                if bit == 0:
                    break
                repeat += 1
            
            # The sequence is run_0 zeros then run_1 ones.
            # "repetition of the sequence"
            # Does it mean (00..11..) repeated?
            # Or just the last run?
            # "The bit array has ... m0 bits denoting number of zeros ... m1 bits denoting number of ones ... n bits ... denoting number of repetitions of the sequence"
            
            # Let's assume the sequence is (zeros, ones).
            # And we emit it 1 + repeat times?
            
            for _ in range(repeat + 1):
                bitmap.extend([0] * run_0)
                bitmap.extend([1] * run_1)
                
            current_bits += (run_0 + run_1) * (repeat + 1)
            
        # Truncate if we overshot (due to RLE block size)
        bitmap = bitmap[:target_bits]
        
        glyphs.append({
            'uc': uc,
            'w': w, 'h': h, 'x': x, 'y': y, 'd': d,
            'bitmap': bitmap
        })
        
        idx += next_offset

    print(f"Parsed {len(glyphs)} glyphs.")
    
    # Generate BDF
    with open(args.output, 'w') as f:
        f.write("STARTFONT 2.1\n")
        f.write(f"FONT {name}\n")
        f.write(f"SIZE {font_bbx_h} 75 75\n") # Point size? Guessing.
        f.write(f"FONTBOUNDINGBOX {font_bbx_w} {font_bbx_h} {font_bbx_x} {font_bbx_y}\n")
        f.write("STARTPROPERTIES 2\n")
        f.write(f"FONT_ASCENT {ascent_A}\n")
        f.write(f"FONT_DESCENT {-descent_g}\n") # BDF descent is positive usually? "Descent is the distance from the baseline to the bottom of the character. It is a positive value."
        f.write("ENDPROPERTIES\n")
        f.write(f"CHARS {len(glyphs)}\n")
        
        for g in glyphs:
            f.write(f"STARTCHAR char{g['uc']}\n")
            f.write(f"ENCODING {g['uc']}\n")
            f.write(f"SWIDTH {g['d']*1000//10} 0\n") # SWIDTH is scalable width. DWIDTH is device width.
            f.write(f"DWIDTH {g['d']} 0\n")
            f.write(f"BBX {g['w']} {g['h']} {g['x']} {g['y']}\n")
            f.write("BITMAP\n")
            
            # Convert bitmap to hex lines
            # BDF bitmap is row by row, padded to byte boundary
            row_bytes = (g['w'] + 7) // 8
            for r in range(g['h']):
                row_val = 0
                for c in range(g['w']):
                    idx = r * g['w'] + c
                    if g['bitmap'][idx]:
                        # BDF is MSB first in the byte
                        # Pixel 0 is bit 7
                        bit_pos = 7 - (c % 8)
                        row_val |= (1 << bit_pos)
                    
                    if (c + 1) % 8 == 0 or c == g['w'] - 1:
                        if (c + 1) % 8 == 0 and c != g['w'] - 1:
                             # We filled a byte, but row continues.
                             # BDF expects hex string for the whole row.
                             # Actually BDF lines are usually byte-aligned.
                             # "The bitmap data is encoded as hexadecimal data... Each line of text represents one row of the bitmap."
                             pass
                
                # We need to output the whole row as hex.
                # If width is > 8, we have multiple bytes.
                
                # Let's redo row loop
                line_hex = ""
                current_byte = 0
                for c in range(row_bytes * 8):
                    if c < g['w']:
                        idx = r * g['w'] + c
                        if g['bitmap'][idx]:
                            current_byte |= (1 << (7 - (c % 8)))
                    
                    if (c + 1) % 8 == 0:
                        line_hex += f"{current_byte:02X}"
                        current_byte = 0
                f.write(f"{line_hex}\n")
                
            f.write("ENDCHAR\n")
        
        f.write("ENDFONT\n")

if __name__ == "__main__":
    main()
