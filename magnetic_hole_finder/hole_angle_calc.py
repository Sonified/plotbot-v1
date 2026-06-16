#file: hole_angle_calc.py

from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def calculate_moving_avg_and_stdev(data, window_seconds, sampling_rate):
    window_size = int(window_seconds * sampling_rate)  # Calculate window size in number of samples
    moving_avg = pd.Series(data).rolling(window=window_size, center=True, min_periods=1).mean().to_numpy()
    moving_stdev = pd.Series(data).rolling(window=window_size, center=True, min_periods=1).std().to_numpy()
    return moving_avg, moving_stdev

def calculate_boundaries_and_w_angle(bmag, times, min_idx, lower_bound):
    tS = None
    tE = None

    # Search for the point on the left side of the minimum where bmag is closest to lower_bound
    left_segment = bmag[0:min_idx + 1]
    left_bound = lower_bound[0:min_idx + 1]
    left_hits = np.where(left_segment >= left_bound)[0]
    tS = left_hits[-1] if len(left_hits) > 0 else None

    # Search for the point on the right side of the minimum where bmag is closest to lower_bound
    right_segment = bmag[min_idx:len(bmag)]
    right_bound = lower_bound[min_idx:len(bmag)]
    right_hits = np.where(right_segment >= right_bound)[0]
    tE = right_hits[0] + min_idx if len(right_hits) > 0 else None
    
    if tS is not None and tE is not None:
        # Calculate the directional change angle ω between the vectors at tS and tE
        B_tS = bmag[tS]
        B_tE = bmag[tE]
        W_angle = np.arccos(np.dot(B_tS, B_tE) / (np.linalg.norm(B_tS) * np.linalg.norm(B_tE))) * 180 / np.pi
    else:
        W_angle = None  # Handle cases where boundaries couldn't be found
    
    return tS, tE, W_angle

current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
print(f'{current_time} - 📐 Hole Angle Calc Initialized')

def calculate_hole_angle_and_boundaries(bmag, br, bt, bn, left_max_value_idx, right_max_value_idx, min_idx, sampling_rate, Bave_window_seconds, wide_angle_threshold, break_for_wide_angle, precomputed_lower_bound=None):
    if precomputed_lower_bound is not None:
        lower_bound = precomputed_lower_bound
    else:
        Bave, delta_B = calculate_moving_avg_and_stdev(bmag, Bave_window_seconds, sampling_rate)
        lower_bound = Bave - delta_B
    
    # Find the left boundary (tS) where bmag drops below lower_bound, scanning right from left_max
    left_segment = bmag[left_max_value_idx:min_idx]
    left_bound_segment = lower_bound[left_max_value_idx:min_idx]
    left_hits = np.where(left_segment <= left_bound_segment)[0]
    tS = left_hits[0] + left_max_value_idx if len(left_hits) > 0 else None

    # Find the right boundary (tE) where bmag drops below lower_bound, scanning left from right_max
    if min_idx < right_max_value_idx + 1:
        right_segment = bmag[min_idx:right_max_value_idx + 1]
        right_bound_segment = lower_bound[min_idx:right_max_value_idx + 1]
        right_hits = np.where(right_segment <= right_bound_segment)[0]
        tE = right_hits[-1] + min_idx if len(right_hits) > 0 else None
    else:
        tE = None

    if tS is None or tE is None:
        return None, None, None

    # Calculate the directional change angle ω between the vectors at tS and tE
    B_tS = np.array([br[tS], bt[tS], bn[tS]])
    B_tE = np.array([br[tE], bt[tE], bn[tE]])
    W_angle = np.arccos(np.dot(B_tS, B_tE) / (np.linalg.norm(B_tS) * np.linalg.norm(B_tE))) * 180 / np.pi
    
    print(f"-----📐 W angle between boundaries is {W_angle} degrees.")
    
    # Check if the W angle exceeds the threshold
    if W_angle > wide_angle_threshold:
        print(f"🇲🇦 Too large W angle: {W_angle}°")
        if break_for_wide_angle:
            print("-----⛔️ Skipping this hole due to excessive W angle.")
            return None, None, None  # Skip this hole if the angle exceeds the threshold
    
    return tS, tE, W_angle
