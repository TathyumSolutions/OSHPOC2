"""
Audio resampling utilities
Convert between different sample rates
"""
import struct


def resample_8khz_to_16khz(pcm_8khz):
    """
    Upsample from 8kHz to 16kHz by duplicating each sample
    Simple linear interpolation
    
    Args:
        pcm_8khz: bytes of 16-bit PCM audio at 8kHz
    
    Returns:
        bytes of 16-bit PCM audio at 16kHz
    """
    # Unpack 16-bit samples
    samples = []
    for i in range(0, len(pcm_8khz), 2):
        if i + 1 < len(pcm_8khz):
            sample = struct.unpack('<h', pcm_8khz[i:i+2])[0]
            samples.append(sample)
    
    # Upsample by duplicating each sample (simple but works)
    upsampled = []
    for sample in samples:
        upsampled.append(sample)
        upsampled.append(sample)  # Duplicate for 2x sample rate
    
    # Pack back to bytes
    return b''.join(struct.pack('<h', s) for s in upsampled)


def resample_16khz_to_8khz(pcm_16khz):
    """
    Downsample from 16kHz to 8kHz by taking every other sample
    
    Args:
        pcm_16khz: bytes of 16-bit PCM audio at 16kHz
    
    Returns:
        bytes of 16-bit PCM audio at 8kHz
    """
    # Unpack 16-bit samples
    samples = []
    for i in range(0, len(pcm_16khz), 2):
        if i + 1 < len(pcm_16khz):
            sample = struct.unpack('<h', pcm_16khz[i:i+2])[0]
            samples.append(sample)
    
    # Downsample by taking every other sample
    downsampled = samples[::2]
    
    # Pack back to bytes
    return b''.join(struct.pack('<h', s) for s in downsampled)
