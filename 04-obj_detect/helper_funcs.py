import io
import numpy as np
from PIL import Image

def raw_to_bmp_bytes(image_data, width=None, height=None, channels=3):
    """
    Convert raw image data or numpy array to BMP format bytes.
    
    Args:
        image_data: raw bytes or numpy array representing image data
        width: image width (required for raw bytes)
        height: image height (required for raw bytes)
        channels: number of channels (3 for RGB, 1 for grayscale)
        
    Returns:
        bytes: BMP formatted image data
    """
    # If it's already a numpy array, use the original logic
    if isinstance(image_data, np.ndarray):
        numpy_array = image_data
    else:
        # Convert raw bytes to numpy array
        if width is None or height is None:
            raise ValueError("Width and height must be provided for raw byte data")
        
        # Calculate expected size and validate
        expected_size = width * height * channels
        if len(image_data) != expected_size:
            raise ValueError(f"Data size {len(image_data)} doesn't match expected size {expected_size} for {width}x{height} with {channels} channels")
        
        # Reshape based on number of channels
        if channels == 1:
            numpy_array = np.frombuffer(image_data, dtype=np.uint8).reshape((height, width))
        else:
            numpy_array = np.frombuffer(image_data, dtype=np.uint8).reshape((height, width, channels))
    
    # Convert numpy array to BMP using PIL
    if len(numpy_array.shape) == 1:
        raise ValueError("1D array needs to be reshaped to image dimensions")
    elif len(numpy_array.shape) == 2:
        # Grayscale image
        pil_image = Image.fromarray(numpy_array, mode='L')
    elif len(numpy_array.shape) == 3:
        if numpy_array.shape[2] == 3:
            # RGB image
            pil_image = Image.fromarray(numpy_array, mode='RGB')
        elif numpy_array.shape[2] == 4:
            # RGBA image
            pil_image = Image.fromarray(numpy_array, mode='RGBA')
        else:
            # Handle other channel counts
            pil_image = Image.fromarray(numpy_array)
    else:
        raise ValueError(f"Unsupported array shape: {numpy_array.shape}")
    
    # Convert PIL Image to BMP bytes
    byte_io = io.BytesIO()
    pil_image.save(byte_io, format='BMP')
    return byte_io.getvalue()
