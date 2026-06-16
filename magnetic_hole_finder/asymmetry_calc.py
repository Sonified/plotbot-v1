#file: asymmetry_calc.py
import numpy as np
import pandas as pd

def process_asymmetry(
    left_max_value, right_max_value,
    left_max_value_idx, right_max_value_idx,
    L_threshold_cross, R_threshold_cross,
    times_clipped, asymetric_peak_threshold,
    symmetrical_peak_scan_window_in_secs,
    bmag_clipped, bmag_slow_smooth_clipped, bmag_fast_smooth_clipped,
    determine_sampling_rate, INSTRUMENT_SAMPLING_RATE,
    max_window_seconds,
    break_for_assymettry,
    break_for_complex_hole  # New flag for skipping complex holes
):
    # Initialize flags
    asymmetrical_initial_peaks_flag = False
    symmetrical_peak_found_flag = False
    complex_hole_flag = False

    # Calculate asymmetry
    peak_diff_percentage = abs(left_max_value - right_max_value) / min(left_max_value, right_max_value)
    print(f"🪐 Asymmetry between peaks: {peak_diff_percentage:.2%}")

    # Determine the minimum index and value within the current hole using the clipped data
    min_idx = np.argmin(bmag_clipped[L_threshold_cross:R_threshold_cross + 1]) + L_threshold_cross
    min_value = bmag_clipped[min_idx]
    min_timestamp = times_clipped[min_idx]

    # Convert numpy.datetime64 to pandas Timestamp to use strftime
    min_timestamp_pd = pd.Timestamp(min_timestamp)
    min_timestamp_str = min_timestamp_pd.strftime('%Y-%m-%d/%H:%M:%S.%f')[:-3]
    print(f"Minimum detected at index {min_idx}, value: {min_value}, timestamp: {min_timestamp_str}")

    if peak_diff_percentage > asymetric_peak_threshold:
        asymmetrical_initial_peaks_flag = True
        complex_hole_flag = True
        print(f"🇲🇦 Peaks are NOT within the threshold of {asymetric_peak_threshold*100}%.")
        print("Initial asymmetry detected, marking as complex hole.")

        if break_for_complex_hole:
            print("-----⛔️ Skipping this hole due to complexity.")
            return {"status": "complex"}
        
        # Step 1: Check if Bmag crosses below the slow smooth Bmag in the next second
        sampling_rate = determine_sampling_rate(times_clipped, INSTRUMENT_SAMPLING_RATE, True)
        next_second_samples = int(1 * sampling_rate)
        extended_search_end = min(len(bmag_clipped), right_max_value_idx + next_second_samples)

        segment = bmag_clipped[right_max_value_idx:extended_search_end]
        smooth_segment = bmag_slow_smooth_clipped[right_max_value_idx:extended_search_end]
        below_indices = np.where(segment < smooth_segment)[0]
        crossed_below = len(below_indices) > 0
        if crossed_below:
            j = below_indices[0] + right_max_value_idx

        if crossed_below:
            above_segment = bmag_clipped[j:len(bmag_clipped)]
            smooth_above = bmag_slow_smooth_clipped[j:len(bmag_clipped)]
            above_indices = np.where(above_segment > smooth_above)[0]
            if len(above_indices) > 0:
                R_threshold_cross = above_indices[0] + j
            else:
                R_threshold_cross = len(bmag_clipped) - 1

            # Now apply the fast smoothing method
            R_plateau_scan = R_threshold_cross
            while R_plateau_scan < len(bmag_fast_smooth_clipped) - 1 and bmag_fast_smooth_clipped[R_plateau_scan] < bmag_fast_smooth_clipped[R_plateau_scan + 1]:
                R_plateau_scan += 1
            
            R_avg_inflect = R_plateau_scan
            slice_bmag = bmag_clipped[R_threshold_cross:R_avg_inflect + 1]
            print(f"Right peak search range: {R_threshold_cross} to {R_avg_inflect}, slice length: {len(slice_bmag)}")
            
            if len(slice_bmag) > 0:
                right_max_value_idx = np.argmax(slice_bmag) + R_threshold_cross
                right_max_value_idx = min(right_max_value_idx, len(bmag_clipped) - 1)
                right_max_value = bmag_clipped[right_max_value_idx]
                print(f"Right maximum detected at index {right_max_value_idx}, value: {right_max_value}")
            else:
                print(f"Warning: Empty slice for finding the right maximum: R_threshold_cross={R_threshold_cross}, R_avg_inflect={R_avg_inflect}")
                right_max_value_idx = min(R_threshold_cross, len(bmag_clipped) - 1)
                right_max_value = bmag_clipped[right_max_value_idx]
        else:
            # Step 3: If no crossing below, look forward two seconds for a new peak
            extended_search_end = min(len(bmag_clipped), int(right_max_value_idx + 2 * sampling_rate))
            search_segment = bmag_clipped[right_max_value_idx:extended_search_end]
            min_vals = np.minimum(left_max_value, search_segment)
            min_vals[min_vals == 0] = 1e-30
            diffs = np.abs(left_max_value - search_segment) / min_vals
            match_indices = np.where(diffs <= asymetric_peak_threshold)[0]
            if len(match_indices) > 0:
                right_max_value_idx = match_indices[0] + right_max_value_idx
                right_max_value = bmag_clipped[right_max_value_idx]
                print(f"New right maximum detected at index {right_max_value_idx}, value: {right_max_value}")

        # Re-scan the entire new region for a new minimum
        new_min_idx = np.argmin(bmag_clipped[L_threshold_cross:right_max_value_idx + 1]) + L_threshold_cross
        new_min_value = bmag_clipped[new_min_idx]
        print(f"New minimum detected at index {new_min_idx}, value: {new_min_value}")

        # Recalculate asymmetry after adjustment
        adjusted_peak_diff_percentage = abs(left_max_value - right_max_value) / min(left_max_value, right_max_value)
        print(f"Asymmetry between peaks after adjustment: {adjusted_peak_diff_percentage:.2%}")

        if adjusted_peak_diff_percentage <= asymetric_peak_threshold:
            print(f"Peaks are now within the threshold of {asymetric_peak_threshold * 100}%.")
        else:
            print(f"Peaks are STILL NOT within the threshold of {asymetric_peak_threshold * 100}%.")
            if break_for_assymettry:
                print("-----⛔️ Skipping this hole due to unresolved asymmetry.")
                return {"status": "unresolved_asymmetry"}

        # Update variables
        min_idx = new_min_idx
        min_value = new_min_value

    else:
        print(f"Peaks are within the threshold of {asymetric_peak_threshold*100}%.")

    # Prepare a dictionary with all relevant data
    
    hole_info = {
        "status": "resolved",
        "L_threshold_cross": L_threshold_cross,
        "R_threshold_cross": R_threshold_cross,
        "min_idx": min_idx,
        "min_value": bmag_clipped[min_idx],
        "left_max_value_idx": left_max_value_idx,
        "left_max_value": left_max_value,
        "right_max_value_idx": right_max_value_idx,
        "right_max_value": right_max_value,
        "asymmetrical_initial_peaks_flag": asymmetrical_initial_peaks_flag,
        "symmetrical_peak_found_flag": symmetrical_peak_found_flag,
        "complex_hole_flag": complex_hole_flag,
    }

    print(f"Final hole info: {hole_info}")

    return hole_info
