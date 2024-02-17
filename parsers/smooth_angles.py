import numpy as np

def smooth_angles(data_list, window_size):
    data = np.array(data_list)
    # Ensure window_size is odd to have a central point
    if window_size % 2 == 0:
        raise ValueError("Window size must be odd.")
    
    # Generate weights for a triangular window
    center_index = window_size // 2
    weights = np.array([max(1, (window_size - abs(i - center_index))) for i in range(window_size)])
    weights = weights / weights.sum()  # Normalize weights so they sum to 1

    # Calculate the sine and cosine components
    sin_components = np.sin(data)
    cos_components = np.cos(data)
    
    # Smooth the sine and cosine components
    smoothed_sin = np.convolve(sin_components, weights, mode='same')
    smoothed_cos = np.convolve(cos_components, weights, mode='same')
    
    # Calculate the arctangent of the average sine and cosine components to get the smoothed angle
    smoothed_angles = np.arctan2(smoothed_sin, smoothed_cos)
    
    return smoothed_angles

