import numpy as np

def smooth_data(data_list, window_size):
    data = np.array(data_list)
    # Ensure window_size is odd to have a central point
    if window_size % 2 == 0:
        raise ValueError("Window size must be odd.")
    
    # Generate weights that decrease with distance from the center
    center_index = window_size // 2
    weights = np.array([max(1, (window_size - abs(i - center_index))) for i in range(window_size)])
    weights = weights / weights.sum()  # Normalize weights so they sum to 1
    
    return np.convolve(data, weights, mode='same')

