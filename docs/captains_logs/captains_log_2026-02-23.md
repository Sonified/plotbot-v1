# Captain's Log - 2026-02-23

## v1.03 Bugfix: Set energy index 8 for encounter 26

### Summary
Added encounter 26 (E26) to the list of encounters that use energy index 8 instead of 12 in the PSP electron classes.

### Files Changed
- `plotbot/data_classes/psp_electron_classes.py`: Added 'E26' to encounter list at both locations (lines 168 and 489)
- `plotbot/__init__.py`: Version bump to v1.03
