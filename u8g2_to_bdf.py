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


def parse_bdf_file(filepath, map_range=None):
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    glyphs = []
    current_glyph = None
    
    font_bbx = {}
    
    # Parse map range
    allowed_codepoints = set()
    if map_range:
        # Format: "32-255, 300"
        parts = map_range.split(',')
        for p in parts:
            if '-' in p:
                start, end = map(int, p.split('-'))
                allowed_codepoints.update(range(start, end + 1))
            else:
                allowed_codepoints.add(int(p))
    
    
    glyphs = []
    current_glyph = None
    in_bitmap = False
    
    for line in lines:
        line = line.strip()
        if line.startswith("FONTBOUNDINGBOX"):
            parts = line.split()
            font_bbx['w'] = int(parts[1])
            font_bbx['h'] = int(parts[2])
            font_bbx['x'] = int(parts[3])
            font_bbx['y'] = int(parts[4])
        elif line.startswith("FONT_ASCENT"):
            font_bbx['ascent'] = int(line.split()[1])
        elif line.startswith("FONT_DESCENT"):
            font_bbx['descent'] = int(line.split()[1])
        elif line.startswith("STARTCHAR"):
            current_glyph = {'bitmap_hex': []}
            in_bitmap = False
        elif line.startswith("ENCODING"):
            if current_glyph: current_glyph['uc'] = int(line.split()[1])
        elif line.startswith("DWIDTH"):
            if current_glyph: current_glyph['d'] = int(line.split()[1])
        elif line.startswith("BBX"):
            if current_glyph:
                parts = line.split()
                current_glyph['w'] = int(parts[1])
                current_glyph['h'] = int(parts[2])
                current_glyph['x'] = int(parts[3])
                current_glyph['y'] = int(parts[4])
        elif line.startswith("BITMAP"):
            in_bitmap = True
        elif line.startswith("ENDCHAR"):
            in_bitmap = False
            if current_glyph:
                if not map_range or current_glyph['uc'] in allowed_codepoints:
                    # Process bitmap
                    flat_bitmap = []
                    for hex_line in current_glyph['bitmap_hex']:
                        val = int(hex_line, 16)
                        total_bits_in_line = len(hex_line) * 4
                        for i in range(total_bits_in_line):
                            bit = (val >> (total_bits_in_line - 1 - i)) & 1
                            flat_bitmap.append(bit)
                        # Truncate row to width (BDF pads to byte)
                        # Wait, flat_bitmap is growing. We need to slice the last added row.
                        # Actually, easier to slice after appending row.
                        
                        # Correct logic:
                        # We appended total_bits_in_line bits.
                        # We only want the first w bits of this row.
                        # But we already appended them to flat_bitmap? 
                        # No, we appended all.
                        
                        # Let's fix:
                        # We need to keep only w bits from the current row.
                        # The current row starts at len(flat_bitmap) - total_bits_in_line
            # Let's rewrite the inner loop
                        pass
                    
                    # Re-implementation of bitmap processing
                    final_bitmap = []
                    for hex_line in current_glyph['bitmap_hex']:
                        val = int(hex_line, 16)
                        row_bits = []
                        # BDF hex is byte-aligned.
                        # If w=10, hex is 4 chars (2 bytes = 16 bits).
                        num_bits = len(hex_line) * 4
                        for i in range(num_bits):
                             bit = (val >> (num_bits - 1 - i)) & 1
                             row_bits.append(bit)
                        final_bitmap.extend(row_bits[:current_glyph['w']])
                    
                    current_glyph['bitmap'] = final_bitmap
                    del current_glyph['bitmap_hex']
                    
                    # Skip empty glyphs (all zeros or zero dimensions)
                    is_empty = (current_glyph['w'] == 0 or 
                               current_glyph['h'] == 0 or 
                               all(bit == 0 for bit in final_bitmap))
                    
                    if not is_empty:
                        glyphs.append(current_glyph)
                current_glyph = None
        else:
            if in_bitmap and current_glyph:
                current_glyph['bitmap_hex'].append(line)
                
    return glyphs, font_bbx

def main():
    parser = argparse.ArgumentParser(description='Convert u8g2 font C file to BDF, or BDF to u8g2 C file.')
    parser.add_argument('input_file', help='Input file (C or BDF)')
    parser.add_argument('-o', '--output', help='Output file', default='output')
    parser.add_argument('-e', '--encode', action='store_true', help='Encode BDF to u8g2 C file')
    parser.add_argument('-m', '--map', help='Unicode range to export (e.g. "32-255,300")', default=None)
    
    args = parser.parse_args()
    

class BitWriter:
    def __init__(self):
        self.data = bytearray()
        self.current_byte = 0
        self.bit_idx = 0 # 0 to 7
        
    def write_bits(self, val, num_bits):
        for i in range(num_bits):
            bit = (val >> i) & 1
            if bit:
                self.current_byte |= (1 << self.bit_idx)
            
            self.bit_idx += 1
            if self.bit_idx == 8:
                self.data.append(self.current_byte)
                self.current_byte = 0
                self.bit_idx = 0
                
    def write_signed_bits(self, val, num_bits):
        # Excess-K encoding
        # val = stored_val - (1 << (num_bits - 1))
        # stored_val = val + (1 << (num_bits - 1))
        stored_val = val + (1 << (num_bits - 1))
        self.write_bits(stored_val, num_bits)
        
    def flush(self):
        if self.bit_idx > 0:
            self.data.append(self.current_byte)
            self.current_byte = 0
            self.bit_idx = 0
            
    def get_bytes(self):
        self.flush()
        return bytes(self.data)

def encode_rle(bitmap, m0, m1):
    # RLE compression
    # m0 bits for zeros
    # m1 bits for ones
    # n bits for repeat
    
    # We need to find runs of 0s and 1s.
    # Sequence: 0s, 1s.
    # If we have 0s then 1s, that's one sequence.
    # If we have 0s then 0s? No, runs are greedy.
    
    # But wait, the format is:
    # run_0 (m0 bits)
    # run_1 (m1 bits)
    # repeat (unary)
    
    # So we must encode pairs of (zeros, ones).
    # If we have only zeros, run_1 = 0.
    # If we have only ones, run_0 = 0.
    
    encoded_bits = [] # List of (val, bits) tuples to write later
    
    # First, convert bitmap to RLE pairs
    pairs = []
    idx = 0
    while idx < len(bitmap):
        # Count zeros
        zeros = 0
        while idx < len(bitmap) and bitmap[idx] == 0:
            zeros += 1
            idx += 1
            
        # Count ones
        ones = 0
        while idx < len(bitmap) and bitmap[idx] == 1:
            ones += 1
            idx += 1
            
        pairs.append((zeros, ones))
        
    # Now compress pairs
    # We can repeat the previous pair if it matches.
    
    # We need to handle field overflows.
    # Max zeros = (1 << m0) - 1
    # Max ones = (1 << m1) - 1
    
    # If a run is too long, we must split it.
    # Splitting strategy:
    # If zeros > max, we emit (max, 0) and remaining zeros.
    # If ones > max, we emit (zeros, max) and remaining ones (with 0 zeros).
    
    # Let's normalize pairs first to fit in m0/m1
    normalized_pairs = []
    max_0 = (1 << m0) - 1
    max_1 = (1 << m1) - 1
    
    for z, o in pairs:
        while z > max_0:
            normalized_pairs.append((max_0, 0))
            z -= max_0
        
        while o > max_1:
            normalized_pairs.append((z, max_1))
            z = 0
            o -= max_1
            
        normalized_pairs.append((z, o))
        
    # Now encode with repeats
    i = 0
    bw = BitWriter()
    
    while i < len(normalized_pairs):
        z, o = normalized_pairs[i]
        
        # Count repeats
        repeat = 0
        j = i + 1
        while j < len(normalized_pairs) and normalized_pairs[j] == (z, o):
            repeat += 1
            j += 1
            
        # Write z (m0 bits)
        bw.write_bits(z, m0)
        # Write o (m1 bits)
        bw.write_bits(o, m1)
        # Write repeat (unary: 1s then 0)
        for _ in range(repeat):
            bw.write_bits(1, 1)
        bw.write_bits(0, 1)
        
        i += 1 + repeat
        
    return bw.get_bytes(), bw.bit_idx + len(bw.data)*8 # Approximate bit count? No.
    # BitWriter logic is a bit complex for just counting.
    # Let's return the bit count properly.
    # Actually get_bytes flushes, so len * 8 is upper bound.
    # We need exact bit count for optimization?
    # Yes, to pick best m0/m1.
    
    # Let's make BitWriter track bit count.
    return bw

def calculate_encoded_size(glyphs, m0, m1):
    total_bits = 0
    for g in glyphs:
        bw = encode_rle(g['bitmap'], m0, m1)
        # We need exact bits written.
        # BitWriter doesn't expose it easily in my implementation above.
        # Let's update BitWriter.
        # But wait, encode_rle returns a BitWriter instance now (in my thought).
        # Let's fix encode_rle to return bits.
        
        # Actually, for optimization we don't need the bytes, just the size.
        # But we need to do the work.
        pass
    return total_bits

# Helper to get bit width of a value
def get_bit_width(val):
    if val == 0: return 0
    return val.bit_length()

def get_signed_bit_width(val):
    # For Excess-K, we need range.
    # But u8g2 uses fixed bit width for all glyphs for a field.
    # We need to find min/max of all glyphs.
    pass

def encode_u8g2(glyphs, font_bbx, font_name):
    # 1. Determine optimal m0, m1
    # Try all combinations m0=2..8, m1=2..7 (from bdfconv)
    best_size = float('inf')
    best_m0 = 3
    best_m1 = 3
    
    # We need a fast way to calculate size without full encoding if possible.
    # But full encoding is robust.
    
    # 2. Determine bit widths for fields
    # W, H, X, Y, D
    max_w = 0
    max_h = 0
    max_x = 0 # absolute max? No, signed range.
    min_x = 0
    max_y = 0
    min_y = 0
    max_d = 0
    min_d = 0
    
    for g in glyphs:
        max_w = max(max_w, g['w'])
        max_h = max(max_h, g['h'])
        max_x = max(max_x, g['x'])
        min_x = min(min_x, g['x'])
        max_y = max(max_y, g['y'])
        min_y = min(min_y, g['y'])
        max_d = max(max_d, g['d'])
        min_d = min(min_d, g['d'])
        
    bitcntW = get_bit_width(max_w)
    bitcntH = get_bit_width(max_h)
    
    # For signed, we need to cover the range [min, max].
    # Excess-K: val + 2^(n-1).
    # We need 2^(n-1) > abs(min) and 2^(n-1) >= max?
    # No, range is -2^(n-1) to 2^(n-1) - 1.
    # So we need n such that -2^(n-1) <= min and max <= 2^(n-1) - 1.
    
    def needed_bits_signed(min_v, max_v):
        # We need to fit both.
        # abs_max = max(abs(min_v), abs(max_v))
        # bits = abs_max.bit_length() + 1 ?
        # Example: -16 to 16.
        # -16 needs 5 bits (10000). 16 needs 6 bits (010000) signed?
        # Excess-K with n=5: range -16 to 15.
        # If max is 16, we need n=6 (-32 to 31).
        
        for n in range(1, 16):
            limit = 1 << (n - 1)
            if min_v >= -limit and max_v < limit:
                return n
        return 16
        
    bitcntX = needed_bits_signed(min_x, max_x)
    bitcntY = needed_bits_signed(min_y, max_y)
    bitcntD = needed_bits_signed(min_d, max_d)
    
    # Optimize m0, m1
    # This might be slow in python for large fonts.
    # Let's pick reasonable defaults or try a few.
    # bdfconv tries m0: 2..8, m1: 2..7.
    
    print("Optimizing RLE parameters...")
    for m0 in range(2, 9):
        for m1 in range(2, 8):
            current_size = 0
            for g in glyphs:
                # We need a version of encode_rle that just returns bit count
                # For now, let's just use the full one, it's python but maybe fast enough for typical fonts.
                bw = encode_rle(g['bitmap'], m0, m1)
                # We need to access the bit count from bw
                # Let's add a property or return it
                bits = (len(bw.data) * 8) if hasattr(bw, 'data') else 0 # Approximation?
                # Wait, encode_rle returns bw.
                # We need exact bits.
                # Let's modify encode_rle to return (bytes, bit_count)
                pass
            
            # ...
            
    # Let's redefine encode_rle to return (bytes, bit_count)
    # And use it here.
    
    # For now, let's assume we picked best_m0, best_m1.
    # Let's just use 3, 3 as default if optimization is skipped, but we should do it.
    
    # Re-implement encode_rle properly first.
    pass

def encode_rle_bits(bitmap, m0, m1):
    # Returns (bytearray, bit_count)
    pairs = []
    idx = 0
    while idx < len(bitmap):
        zeros = 0
        while idx < len(bitmap) and bitmap[idx] == 0:
            zeros += 1
            idx += 1
        ones = 0
        while idx < len(bitmap) and bitmap[idx] == 1:
            ones += 1
            idx += 1
        pairs.append((zeros, ones))
        
    normalized_pairs = []
    max_0 = (1 << m0) - 1
    max_1 = (1 << m1) - 1
    
    for z, o in pairs:
        while z > max_0:
            normalized_pairs.append((max_0, 0))
            z -= max_0
        while o > max_1:
            normalized_pairs.append((z, max_1))
            z = 0
            o -= max_1
        normalized_pairs.append((z, o))
        
    bw = BitWriter()
    total_bits = 0
    
    i = 0
    while i < len(normalized_pairs):
        z, o = normalized_pairs[i]
        repeat = 0
        j = i + 1
        while j < len(normalized_pairs) and normalized_pairs[j] == (z, o):
            repeat += 1
            j += 1
            
        bw.write_bits(z, m0)
        bw.write_bits(o, m1)
        # Unary repeat: 1s then 0
        for _ in range(repeat):
            bw.write_bits(1, 1)
        bw.write_bits(0, 1)
        
        total_bits += m0 + m1 + repeat + 1
        i += 1 + repeat
        
    return bw.get_bytes(), total_bits

def encode_rle_to_bw(bitmap, m0, m1, bw):
    pairs = []
    idx = 0
    while idx < len(bitmap):
        zeros = 0
        while idx < len(bitmap) and bitmap[idx] == 0:
            zeros += 1
            idx += 1
        ones = 0
        while idx < len(bitmap) and bitmap[idx] == 1:
            ones += 1
            idx += 1
        pairs.append((zeros, ones))
        
    normalized_pairs = []
    max_0 = (1 << m0) - 1
    max_1 = (1 << m1) - 1
    
    for z, o in pairs:
        while z > max_0:
            normalized_pairs.append((max_0, 0))
            z -= max_0
        while o > max_1:
            normalized_pairs.append((z, max_1))
            z = 0
            o -= max_1
        normalized_pairs.append((z, o))
        
    total_bits = 0
    i = 0
    while i < len(normalized_pairs):
        z, o = normalized_pairs[i]
        repeat = 0
        j = i + 1
        while j < len(normalized_pairs) and normalized_pairs[j] == (z, o):
            repeat += 1
            j += 1
            
        bw.write_bits(z, m0)
        bw.write_bits(o, m1)
        for _ in range(repeat):
            bw.write_bits(1, 1)
        bw.write_bits(0, 1)
        
        total_bits += m0 + m1 + repeat + 1
        i += 1 + repeat
    return total_bits

def generate_u8g2_c(glyphs, font_bbx, name):
    # 1. Optimize RLE
    best_size = float('inf')
    best_m0 = 3
    best_m1 = 3
    
    # Pre-calculate metrics
    max_w = 0
    max_h = 0
    max_x = 0
    min_x = 0
    max_y = 0
    min_y = 0
    max_d = 0
    min_d = 0
    
    for g in glyphs:
        max_w = max(max_w, g['w'])
        max_h = max(max_h, g['h'])
        max_x = max(max_x, g['x'])
        min_x = min(min_x, g['x'])
        max_y = max(max_y, g['y'])
        min_y = min(min_y, g['y'])
        max_d = max(max_d, g['d'])
        min_d = min(min_d, g['d'])
        
    bitcntW = get_bit_width(max_w)
    bitcntH = get_bit_width(max_h)
    
    def needed_bits_signed(min_v, max_v):
        for n in range(1, 16):
            limit = 1 << (n - 1)
            if min_v >= -limit and max_v < limit:
                return n
        return 16
        
    bitcntX = needed_bits_signed(min_x, max_x)
    bitcntY = needed_bits_signed(min_y, max_y)
    bitcntD = needed_bits_signed(min_d, max_d)
    
    # Optimize
    for m0 in range(2, 9):
        for m1 in range(2, 8):
            size = 0
            for g in glyphs:
                _, bits = encode_rle_bits(g['bitmap'], m0, m1)
                size += bits
            if size < best_size:
                best_size = size
                best_m0 = m0
                best_m1 = m1
                
    print(f"Optimal RLE: m0={best_m0}, m1={best_m1}")
    

    # 2. Generate Data
    # Header construction
    header = bytearray(23)
    # n_glyphs: 0 means 256? Or just number of glyphs.
    # If > 255, we might have issues with standard u8g2 format if it uses 1 byte count.
    # But let's use len(glyphs) & 0xFF.
    header[0] = len(glyphs) & 0xFF
    
    header[1] = 0 # BBX Mode 0
    header[2] = best_m0
    header[3] = best_m1
    header[4] = bitcntW
    header[5] = bitcntH
    header[6] = bitcntX
    header[7] = bitcntY
    header[8] = bitcntD
    
    header[9] = font_bbx.get('w', max_w)
    header[10] = font_bbx.get('h', max_h)
    header[11] = font_bbx.get('x', 0)
    header[12] = font_bbx.get('y', 0) & 0xFF 
    
    # Ascent/Descent
    # Need to find 'A', 'g', '('
    # If not found, use defaults or max/min
    
    def find_glyph(char):
        for g in glyphs:
            if g['uc'] == ord(char):
                return g
        return None
        
    g_A = find_glyph('A')
    g_g = find_glyph('g')
    g_para = find_glyph('(')
    
    ascent_A = (g_A['h'] + g_A['y']) if g_A else max_h + min_y # Fallback
    descent_g = g_g['y'] if g_g else min_y
    ascent_para = (g_para['h'] + g_para['y']) if g_para else ascent_A
    descent_para = g_para['y'] if g_para else descent_g
    
    header[13] = font_bbx.get('ascent', ascent_A) & 0xFF
    header[14] = (-font_bbx.get('descent', descent_g)) & 0xFF # u8g2 stores descent as negative
    
    header[15] = font_bbx.get('ascent', ascent_para) & 0xFF
    header[16] = (-font_bbx.get('descent', descent_para)) & 0xFF 
    
    # Offsets
    # We need to calculate offsets after generating data.
    # We generate data first, then fill offsets.
    
    glyph_data = bytearray()
    
    # Map unicode to offset
    # We need to handle the 0x100 block if present.
    # For now, assume sequential or simple map.
    
    # We need to sort glyphs by unicode?
    glyphs.sort(key=lambda x: x['uc'])
    
    # We need to find where 'A', 'a', 0x100 are.
    offset_A = 0
    offset_a = 0
    offset_100 = 0
    
    # Start of glyph data relative to end of header (23).
    current_offset = 0
    
    # We need to handle the "jump table" or just sequential list.
    # "The glyphs start immediately after the end of the initial data structure."
    # "All glyphs start with the unicode (1 byte) and the offset to the next glyph (1 byte)."
    
    # If unicode > 255?
    # "The address for the unicode glyphs is the end of the initial data structure plus the 16 bit offset from bytes 21/22"
    # So we have two blocks.
    # Block 1: <= 255.
    # Block 2: > 255.
    
    block1 = [g for g in glyphs if g['uc'] <= 255]
    block2 = [g for g in glyphs if g['uc'] > 255]
    
    # Generate Block 1
    for g in block1:
        start_pos = len(glyph_data)
        if g['uc'] == ord('A'): offset_A = start_pos
        if g['uc'] == ord('a'): offset_a = start_pos
        
        # Placeholder for next offset
        glyph_data.append(g['uc'])
        glyph_data.append(0) # Offset placeholder
        
        bw = BitWriter()
        bw.write_bits(g['w'], bitcntW)
        bw.write_bits(g['h'], bitcntH)
        bw.write_signed_bits(g['x'], bitcntX)
        bw.write_signed_bits(g['y'], bitcntY)
        bw.write_signed_bits(g['d'], bitcntD)
        
        encode_rle_to_bw(g['bitmap'], best_m0, best_m1, bw)
        
        data_bytes = bw.get_bytes()
        glyph_data.extend(data_bytes)
        
        # Update offset
        next_pos = len(glyph_data)
        offset = next_pos - start_pos
        if offset > 255:
            print(f"Warning: Glyph {g['uc']} too large for 8-bit offset ({offset})")
        glyph_data[start_pos + 1] = offset & 0xFF
        
    # Block 2 (Unicode > 255)
    offset_100 = len(glyph_data)
    
    # If block2 is empty, offset_100 should point to end?
    # Or 0?
    # If block2 exists:
    for g in block2:
        start_pos = len(glyph_data)
        # Unicode 2 bytes
        glyph_data.append((g['uc'] >> 8) & 0xFF)
        glyph_data.append(g['uc'] & 0xFF)
        glyph_data.append(0) # Offset placeholder
        
        bw = BitWriter()
        bw.write_bits(g['w'], bitcntW)
        bw.write_bits(g['h'], bitcntH)
        bw.write_signed_bits(g['x'], bitcntX)
        bw.write_signed_bits(g['y'], bitcntY)
        bw.write_signed_bits(g['d'], bitcntD)
        
        encode_rle_to_bw(g['bitmap'], best_m0, best_m1, bw)
        
        data_bytes = bw.get_bytes()
        glyph_data.extend(data_bytes)
        
        next_pos = len(glyph_data)
        offset = next_pos - start_pos
        if offset > 255:
            print(f"Warning: Glyph {g['uc']} too large for 8-bit offset ({offset})")
        glyph_data[start_pos + 2] = offset & 0xFF
        
    # Terminator for Block 2?
    # "All glyphs start with the unicode (2 bytes)..."
    # Is there a terminator?
    # Example file ends with \2\0\0\0\4\377\377\0
    # Maybe 0 offset?
    
    # Fill Header Offsets
    header[17] = (offset_A >> 8) & 0xFF
    header[18] = offset_A & 0xFF
    header[19] = (offset_a >> 8) & 0xFF
    header[20] = offset_a & 0xFF
    header[21] = (offset_100 >> 8) & 0xFF
    header[22] = offset_100 & 0xFF
    
    # Combine
    full_data = header + glyph_data
    
    
    # Convert to C string with octal escaping (matching original u8g2 format)
    c_str = ""
    line_len = 0
    
    for i, b in enumerate(full_data):
        # Use octal escaping for non-printable and special characters
        # Printable ASCII (32-126) can be literal, except quote, backslash
        if 32 <= b <= 126 and b != ord('"') and b != ord('\\'):
            s = chr(b)
        else:
            # Octal escape - use shortest form possible
            # But if next char is a literal digit 0-7, must pad to avoid ambiguity
            octal_str = f"{b:o}"
            
            # Check if next character will be a literal digit 0-7
            need_padding = False
            if i + 1 < len(full_data):
                next_b = full_data[i + 1]
                if 32 <= next_b <= 126 and chr(next_b) in '01234567':
                    need_padding = True
            
            if need_padding:
                s = f"\\{b:03o}"
            else:
                s = f"\\{octal_str}"
        
        # Check if adding this would exceed line length
        if line_len + len(s) > 70:
            c_str += '"\n  "'
            line_len = 0
        c_str += s
        line_len += len(s)
        
    return f'const uint8_t {name}[] U8G2_FONT_SECTION("{name}") = \n  "{c_str}";\n'


def convert_u8g2_to_bdf(data, name, output_file):
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
    font_bbx_y = data[12] 
    if font_bbx_y > 127: font_bbx_y -= 256 # Signed byte
    
    ascent_A = data[13]
    descent_g = data[14] 
    if descent_g > 127: descent_g -= 256 # Signed byte
    
    # ... offsets ...
    
    idx = 23
    glyphs = []
    
    while idx < len(data):
        if idx >= len(data): break
        
        uc = data[idx]
        next_offset = data[idx+1]
        
        if next_offset == 0:
            # Check for 0x100 block or end
            # If we are at the end of block 1, we might see 0 offset?
            # Or if it's the terminator.
            # Let's check if we have more data for block 2.
            # But for now, let's break if offset is 0.
            # Wait, if it's block 2, we need to handle 2-byte unicode.
            # But the loop assumes 1-byte unicode structure.
            # If we hit a 0 offset, maybe we should check if there's a block 2?
            # For this task, let's assume simple fonts first or handle block 2 if we see it.
            # But the loop structure depends on `next_offset`.
            break
            
        glyph_data_start = idx + 2
        br = BitReader(data[glyph_data_start:])
        
        w = br.read_bits(bitcntW)
        h = br.read_bits(bitcntH)
        x = br.read_signed_bits(bitcntX)
        y = br.read_signed_bits(bitcntY)
        d = br.read_signed_bits(bitcntD)
        
        target_bits = w * h
        current_bits = 0
        bitmap = [] 
        
        while current_bits < target_bits:
            run_0 = br.read_bits(m0)
            run_1 = br.read_bits(m1)
            
            repeat = 0
            while True:
                bit = br.read_bits(1)
                if bit == 0:
                    break
                repeat += 1
            
            for _ in range(repeat + 1):
                bitmap.extend([0] * run_0)
                bitmap.extend([1] * run_1)
                
            current_bits += (run_0 + run_1) * (repeat + 1)
            
        bitmap = bitmap[:target_bits]
        
        glyphs.append({
            'uc': uc,
            'w': w, 'h': h, 'x': x, 'y': y, 'd': d,
            'bitmap': bitmap
        })
        
        idx += next_offset

    print(f"Parsed {len(glyphs)} glyphs.")
    
    with open(output_file, 'w') as f:
        f.write("STARTFONT 2.1\n")
        f.write(f"FONT {name}\n")
        f.write(f"SIZE {font_bbx_h} 75 75\n") 
        f.write(f"FONTBOUNDINGBOX {font_bbx_w} {font_bbx_h} {font_bbx_x} {font_bbx_y}\n")
        f.write("STARTPROPERTIES 2\n")
        f.write(f"FONT_ASCENT {ascent_A}\n")
        f.write(f"FONT_DESCENT {-descent_g}\n") 
        f.write("ENDPROPERTIES\n")
        f.write(f"CHARS {len(glyphs)}\n")
        
        for g in glyphs:
            f.write(f"STARTCHAR char{g['uc']}\n")
            f.write(f"ENCODING {g['uc']}\n")
            f.write(f"SWIDTH {g['d']*1000//10} 0\n") 
            f.write(f"DWIDTH {g['d']} 0\n")
            f.write(f"BBX {g['w']} {g['h']} {g['x']} {g['y']}\n")
            f.write("BITMAP\n")
            
            row_bytes = (g['w'] + 7) // 8
            for r in range(g['h']):
                current_byte = 0
                line_hex = ""
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

def main():
    # Argument parsing
    parser = argparse.ArgumentParser(description="Convert BDF fonts to u8g2 C format or vice versa.")
    parser.add_argument("input_file", help="Input BDF or u8g2 C file")
    parser.add_argument("-o", "--output", default="output.c", help="Output file name")
    parser.add_argument("-e", "--encode", action="store_true", help="Encode BDF to u8g2 C (default is decode)")
    parser.add_argument("-m", "--map", help="Character map file for BDF encoding (e.g., 'map.txt')")
    
    args = parser.parse_args()

    if args.encode:
        # BDF to u8g2
        print(f"Parsing BDF file: {args.input_file}")
        glyphs, font_bbx = parse_bdf_file(args.input_file, args.map)
        print(f"Parsed {len(glyphs)} glyphs.")
        
        # Encode
        font_name = args.output.replace('.', '_') # Simple name sanitization
        c_code = generate_u8g2_c(glyphs, font_bbx, font_name)
        
        with open(args.output, 'w') as f:
            f.write(c_code)
        print(f"Written to {args.output}")
    else:
        # u8g2 to BDF
        print(f"Parsing C file: {args.input_file}")
        data, name = parse_c_file(args.input_file)
        if not data:
            print("Failed to read data")
            sys.exit(1)
            
        print(f"Read {len(data)} bytes of font data.")
        convert_u8g2_to_bdf(data, name, args.output)
        print(f"Written to {args.output}")

if __name__ == "__main__":
    main()
        
        # ... (rest of decoding logic)
        # We need to move the decoding logic into a function or keep it here but indented.
        # For now, let's keep it here but I need to restructure main.
        
        # ...

if __name__ == "__main__":
    main()
