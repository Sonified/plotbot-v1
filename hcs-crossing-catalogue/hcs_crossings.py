#!/usr/bin/env python3
"""
HCS Crossing Catalogue — generates time-windowed crossing ranges grouped by PSP encounter.

Usage:
    python hcs_crossings.py                  # default ±1 hour window
    python hcs_crossings.py --hours 2        # ±2 hour window
    python hcs_crossings.py --hours 0.5      # ±30 minute window
    python hcs_crossings.py --output my.csv  # write to specific file
"""

import argparse
import csv
import sys
from datetime import datetime, timedelta

# ── Master crossing list ──────────────────────────────────────────────────────
CROSSING_TIMES = [
    "2020-02-01 04:08:02",
    "2020-06-08 11:55:40",
    "2020-06-08 15:48:55",
    "2020-06-08 21:45:26",
    "2020-06-10 03:18:45",
    "2020-06-10 04:30:42",
    "2020-09-25 09:15:57",
    "2020-09-25 09:54:24",
    "2020-09-25 09:56:51",
    "2020-09-25 13:46:10",
    "2020-09-25 18:01:46",
    "2021-01-17 13:28:55",
    "2021-01-19 18:24:57",
    "2021-01-19 21:10:24",
    "2021-04-29 01:12:07",
    "2021-04-29 08:28:05",
    "2021-04-29 09:34:30",
    "2021-04-29 13:41:16",
    "2021-08-10 01:33:38",
    "2021-08-10 10:40:31",
    "2021-08-10 11:11:59",
    "2021-08-10 18:36:57",
    "2022-02-25 12:29:24",
    "2022-06-02 17:32:34",
    "2022-09-06 17:32:01",
    "2022-12-12 06:50:23",
    "2023-03-16 04:42:06",
    "2023-03-17 21:10:16",
    "2023-06-22 01:34:53",
    "2023-06-22 04:42:04",
    "2023-06-24 05:06:41",
    "2023-09-26 17:02:28",
    "2023-09-26 19:03:38",
    "2023-09-26 20:55:08",
    "2023-09-27 19:58:13",
    "2023-09-28 06:36:06",
    "2023-12-29 02:23:53",
    "2024-03-29 23:11:03",
    "2024-03-30 12:52:54",
    "2024-06-29 12:28:59",
    "2024-06-29 23:52:09",
    "2024-07-01 18:30:13",
    "2024-07-04 05:03:15",
    "2024-09-26 07:03:21",
]

# ── PSP perihelion dates (used to assign crossings to encounters) ─────────────
PERIHELION_DATES = {
    1:  "2018-11-06",
    2:  "2019-04-04",
    3:  "2019-09-01",
    4:  "2020-01-29",
    5:  "2020-06-07",
    6:  "2020-09-27",
    7:  "2021-01-17",
    8:  "2021-04-29",
    9:  "2021-08-09",
    10: "2021-11-21",
    11: "2022-02-25",
    12: "2022-06-01",
    13: "2022-09-06",
    14: "2022-12-11",
    15: "2023-03-17",
    16: "2023-06-22",
    17: "2023-09-27",
    18: "2023-12-29",
    19: "2024-03-30",
    20: "2024-06-30",
    21: "2024-09-30",
}

FMT = "%Y-%m-%d %H:%M:%S"


def parse_perihelion_dates():
    return {num: datetime.strptime(d, "%Y-%m-%d") for num, d in PERIHELION_DATES.items()}


def assign_encounter(crossing_dt, perihelia):
    best_enc = None
    best_delta = timedelta.max
    for enc_num, peri_dt in perihelia.items():
        delta = abs(crossing_dt - peri_dt)
        if delta < best_delta:
            best_delta = delta
            best_enc = enc_num
    return best_enc


def main():
    parser = argparse.ArgumentParser(description="HCS Crossing Catalogue with time windows")
    parser.add_argument("--hours", type=float, default=1.0,
                        help="± window in hours around each crossing (default: 1.0)")
    parser.add_argument("--output", type=str, default="hcs_crossings_output.csv",
                        help="Output CSV filename (default: hcs_crossings_output.csv)")
    args = parser.parse_args()

    window = timedelta(hours=args.hours)
    perihelia = parse_perihelion_dates()

    crossings = [datetime.strptime(t, FMT) for t in CROSSING_TIMES]

    # Group by encounter
    encounter_groups = {}
    for ct in crossings:
        enc = assign_encounter(ct, perihelia)
        encounter_groups.setdefault(enc, []).append(ct)

    # Sort encounters and crossings within each
    sorted_encounters = sorted(encounter_groups.keys())
    for enc in sorted_encounters:
        encounter_groups[enc].sort()

    # Build rows
    rows = []
    for enc in sorted_encounters:
        for i, ct in enumerate(encounter_groups[enc], start=1):
            rows.append({
                "Encounter": f"E{enc:02d}",
                "Crossing #": i,
                "Crossing Time": ct.strftime(FMT),
                "Range Start": (ct - window).strftime(FMT),
                "Range End": (ct + window).strftime(FMT),
            })

    # Write CSV
    fieldnames = ["Encounter", "Crossing #", "Crossing Time", "Range Start", "Range End"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Also print a nice table to terminal
    print(f"\nHCS Crossing Catalogue  (± {args.hours} hr window)")
    print(f"{'='*80}")

    current_enc = None
    for row in rows:
        if row["Encounter"] != current_enc:
            current_enc = row["Encounter"]
            print(f"\n── {current_enc} ──")
        print(f"  {row['Crossing #']:>2}.  {row['Range Start']}  →  {row['Range End']}    (center: {row['Crossing Time']})")

    print(f"\n{'='*80}")
    print(f"Total crossings: {len(rows)}")
    print(f"CSV written to: {args.output}")


if __name__ == "__main__":
    main()
