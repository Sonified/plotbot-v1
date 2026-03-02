#!/bin/bash

echo "🧹 Plotbot Homebrew Cleanup"
echo "==========================="
echo ""
echo "This script removes the duplicate user-local Homebrew installation"
echo "that was accidentally created by an older version of the Plotbot installer."
echo "Your system Homebrew (e.g., /opt/homebrew or /usr/local) will NOT be affected."
echo ""

# Check if there's actually something to clean up
NEEDS_CLEANUP=false

if [ -d "$HOME/homebrew" ]; then
    echo "Found: ~/homebrew"
    NEEDS_CLEANUP=true
fi
if [ -d "$HOME/Homebrew" ]; then
    echo "Found: ~/Homebrew"
    NEEDS_CLEANUP=true
fi

if [ "$NEEDS_CLEANUP" = false ]; then
    echo "Nothing to clean up! No user-local Homebrew found."
    echo ""
    exit 0
fi

echo ""
read -p "Remove these and clean up shell profiles? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""

# Remove duplicate Homebrew directories
if [ -d "$HOME/homebrew" ]; then
    echo "Removing ~/homebrew..."
    rm -rf "$HOME/homebrew"
    echo "✅ Removed ~/homebrew"
fi

if [ -d "$HOME/Homebrew" ]; then
    echo "Removing ~/Homebrew..."
    rm -rf "$HOME/Homebrew"
    echo "✅ Removed ~/Homebrew"
fi

# Also remove micromamba if it was installed by the old script
if [ -d "$HOME/micromamba" ]; then
    echo "Removing ~/micromamba (will be recreated by fresh install)..."
    rm -rf "$HOME/micromamba"
    echo "✅ Removed ~/micromamba"
fi

# Clean up shell profiles
echo ""
echo "Cleaning shell profiles..."

for profile in "$HOME/.zshrc" "$HOME/.zprofile" "$HOME/.bash_profile" "$HOME/.bashrc"; do
    if [ -f "$profile" ]; then
        # Remove the Homebrew user installation block added by old installer
        if grep -q 'HOMEBREW_PREFIX.*\$HOME/homebrew' "$profile" 2>/dev/null || \
           grep -q 'Homebrew (user installation' "$profile" 2>/dev/null; then
            # Create backup
            cp "$profile" "${profile}.plotbot_backup"

            # Remove the block: from "# Homebrew (user installation" through the HOMEBREW_FORCE_VENDOR_RUBY line
            sed -i '' '/# Homebrew (user installation/,/HOMEBREW_FORCE_VENDOR_RUBY/d' "$profile" 2>/dev/null

            # Also remove any standalone HOMEBREW_PREFIX=$HOME/homebrew lines
            sed -i '' '/HOMEBREW_PREFIX.*\$HOME\/homebrew/d' "$profile" 2>/dev/null
            sed -i '' '/HOMEBREW_PREFIX.*\/Users\/.*\/homebrew/d' "$profile" 2>/dev/null

            # Remove micromamba activate lines from old installer
            sed -i '' '/micromamba activate plotbot_v1_micromamba/d' "$profile" 2>/dev/null

            # Clean up any leftover blank lines (collapse multiple blank lines to one)
            sed -i '' '/^$/N;/^\n$/d' "$profile" 2>/dev/null

            echo "✅ Cleaned $profile (backup at ${profile}.plotbot_backup)"
        fi
    fi
done

echo ""
echo "🎉 Cleanup complete!"
echo ""
echo "Next steps:"
echo "1. Restart your terminal:  exec zsh"
echo "2. Pull latest code:       cd ~/GitHub/plotbot-v1 && git pull"
echo "3. Re-run installer:       ./install.sh"
echo ""
