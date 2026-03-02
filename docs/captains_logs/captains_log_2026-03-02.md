# Captain's Log - 2026-03-02

## v1.05 Installer: Robust Homebrew detection, auto-version banner

### Homebrew Detection Fix
- **Bug:** Installer was re-installing Homebrew in user's home directory even when system Homebrew already existed (e.g., at `/opt/homebrew`)
- **Root cause:** Script runs under `#!/bin/bash` but user's Homebrew PATH setup is typically in `.zshrc`/`.zprofile` (macOS default shell is zsh), so `command -v brew` failed silently
- **Fix:** Three-tier detection approach:
  1. Source all shell profiles first (`.zprofile`, `.bash_profile`, `.zshrc`, `.bashrc`) before checking
  2. Check known installation locations (`/opt/homebrew`, `/usr/local`, `$HOME/homebrew`)
  3. `find`-based search as final fallback
- **Additional fix:** Shell profile modification now only happens when we install Homebrew ourselves (user-local). System Homebrew installs are left untouched

### Auto-Version Banner
- `install.sh` now reads version from `plotbot/__init__.py` at runtime
- Shows version in welcome message: `🚀 Welcome to Plotbot Installation (2026_03_02_v1.05)`
- Zero maintenance — updates automatically with every version bump

### Note on Jaye's Install
- Jaye's screenshot showed old install script behavior (cloning to `/Users/jlverniero/Homebrew` instead of `$HOME/homebrew/Homebrew`), suggesting she was running a stale version of the installer
- Solution: `git pull` to get latest scripts before re-running `./install.sh`
