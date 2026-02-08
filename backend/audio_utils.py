"""
Audio conversion utilities for Python 3.13+
Replaces audioop which was removed in Python 3.13
"""
import struct


def ulaw2lin(data, width):
    """
    Convert u-law audio to linear PCM
    
    Args:
        data: bytes of u-law encoded audio
        width: sample width (2 for 16-bit)
    
    Returns:
        bytes of linear PCM audio
    """
    # u-law decompression table
    ulaw_table = [
        -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
        -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
        -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
        -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
        -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
        -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
        -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
        -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
        -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
        -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
        -876, -844, -812, -780, -748, -716, -684, -652,
        -620, -588, -556, -524, -492, -460, -428, -396,
        -372, -356, -340, -324, -308, -292, -276, -260,
        -244, -228, -212, -196, -180, -164, -148, -132,
        -120, -112, -104, -96, -88, -80, -72, -64,
        -56, -48, -40, -32, -24, -16, -8, 0,
        32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
        23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
        15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
        11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
        7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
        5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
        3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
        2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
        1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
        1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
        876, 844, 812, 780, 748, 716, 684, 652,
        620, 588, 556, 524, 492, 460, 428, 396,
        372, 356, 340, 324, 308, 292, 276, 260,
        244, 228, 212, 196, 180, 164, 148, 132,
        120, 112, 104, 96, 88, 80, 72, 64,
        56, 48, 40, 32, 24, 16, 8, 0
    ]
    
    if width != 2:
        raise ValueError("Only 16-bit (width=2) is supported")
    
    # Convert u-law bytes to 16-bit PCM
    pcm_data = []
    for byte in data:
        # u-law byte to linear sample
        sample = ulaw_table[byte]
        # Pack as 16-bit signed integer (little-endian)
        pcm_data.append(struct.pack('<h', sample))
    
    return b''.join(pcm_data)


def lin2ulaw(data, width):
    """
    Convert linear PCM to u-law audio
    
    Args:
        data: bytes of linear PCM audio
        width: sample width (2 for 16-bit)
    
    Returns:
        bytes of u-law encoded audio
    """
    if width != 2:
        raise ValueError("Only 16-bit (width=2) is supported")
    
    # u-law compression
    ulaw_data = []
    
    # Process 2 bytes at a time (16-bit samples)
    for i in range(0, len(data), 2):
        if i + 1 >= len(data):
            break
            
        # Unpack 16-bit signed sample (little-endian)
        sample = struct.unpack('<h', data[i:i+2])[0]
        
        # Convert to u-law
        # This is a simplified version - production code would use proper u-law encoding
        # For now, use a linear approximation
        
        # Get sign
        sign = 0 if sample >= 0 else 0x80
        if sample < 0:
            sample = -sample
        
        # Clamp to max value
        if sample > 32635:
            sample = 32635
            
        # Find exponent and mantissa
        exp = 7
        while exp > 0:
            if sample > (33 << (exp + 2)):
                break
            exp -= 1
            
        mantissa = (sample >> (exp + 3)) & 0x0F
        
        # Construct u-law byte
        ulaw_byte = ~(sign | (exp << 4) | mantissa) & 0xFF
        ulaw_data.append(ulaw_byte)
    
    return bytes(ulaw_data)
