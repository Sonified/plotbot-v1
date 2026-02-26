#!/bin/bash

echo "🔹 Registering Plotbot as Jupyter kernel (Micromamba)..."
echo ""

# Smart micromamba detection: find it wherever it lives
export MAMBA_ROOT_PREFIX="$HOME/micromamba"
export MAMBA_EXE=""

# Method 1: Check if micromamba is already in PATH
if command -v micromamba &> /dev/null; then
    MAMBA_EXE="$(command -v micromamba)"
fi

# Method 2: Ask brew (try system brew first, then user brew)
if [ -z "$MAMBA_EXE" ] || [ ! -f "$MAMBA_EXE" ]; then
    for BREW_CMD in "brew" "/opt/homebrew/bin/brew" "/usr/local/bin/brew" "$HOME/homebrew/bin/brew"; do
        if command -v "$BREW_CMD" &> /dev/null || [ -f "$BREW_CMD" ]; then
            CANDIDATE="$($BREW_CMD --prefix micromamba 2>/dev/null)/bin/micromamba"
            if [ -f "$CANDIDATE" ] && [ -x "$CANDIDATE" ]; then
                MAMBA_EXE="$CANDIDATE"
                break
            fi
        fi
    done
fi

# Method 3: Check common locations directly
if [ -z "$MAMBA_EXE" ] || [ ! -f "$MAMBA_EXE" ]; then
    for CANDIDATE in \
        "/opt/homebrew/bin/micromamba" \
        "/opt/homebrew/opt/micromamba/bin/micromamba" \
        "/usr/local/bin/micromamba" \
        "$HOME/homebrew/bin/micromamba" \
        "$HOME/homebrew/opt/micromamba/bin/micromamba"; do
        if [ -f "$CANDIDATE" ] && [ -x "$CANDIDATE" ]; then
            MAMBA_EXE="$CANDIDATE"
            break
        fi
    done
fi

if [ -z "$MAMBA_EXE" ] || [ ! -f "$MAMBA_EXE" ]; then
    echo "❌ Error: micromamba command not found."
    echo "   Please ensure micromamba is installed and your terminal is restarted."
    exit 1
fi

export MAMBA_EXE
echo "✅ Found micromamba at: $MAMBA_EXE"

# Initialize micromamba shell hook for bash
__mamba_setup="$("$MAMBA_EXE" shell hook --shell bash --root-prefix "$MAMBA_ROOT_PREFIX" 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__mamba_setup"
else
    micromamba() {
        "$MAMBA_EXE" "$@"
    }
    export -f micromamba
fi

# Ensure micromamba is available as a command
if ! command -v micromamba &> /dev/null; then
    micromamba() {
        "$MAMBA_EXE" "$@"
    }
    export -f micromamba
fi

# Check if plotbot_v1_micromamba exists
if ! micromamba env list | grep -q "plotbot_v1_micromamba"; then
    echo "❌ Error: plotbot_v1_micromamba environment not found."
    echo "   Please run 3_setup_env_micromamba.sh first."
    exit 1
fi

echo "✅ Found plotbot_v1_micromamba environment"
echo ""

# Activate the environment and install ipykernel
echo "🔹 Installing ipykernel in plotbot_v1_micromamba..."
micromamba run -n plotbot_v1_micromamba python -m pip install ipykernel

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install ipykernel."
    exit 1
fi

echo "✅ ipykernel installed successfully"
echo ""

# Register the Jupyter kernel
echo "🔹 Registering Jupyter kernel..."
micromamba run -n plotbot_v1_micromamba python -m ipykernel install --user --name plotbot_v1_micromamba --display-name "Plotbot v1 (Micromamba)"

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to register Jupyter kernel."
    exit 1
fi

echo "✅ Jupyter kernel registered successfully"
echo ""

# Verify kernel registration
echo "🔍 Verifying kernel registration..."
if micromamba run -n plotbot_v1_micromamba jupyter kernelspec list | grep -q "plotbot_v1_micromamba"; then
    echo "✅ plotbot_v1_micromamba kernel is registered and available"
else
    echo "⚠️  Kernel may be registered but not showing in current environment"
    echo "   This is often normal - try checking in Jupyter/VS Code"
fi

# Test Python version and key packages
echo ""
echo "🔍 Environment verification:"
echo "   Python version: $(micromamba run -n plotbot_v1_micromamba python --version)"

# Test import of key packages
echo "   Testing key package imports..."
micromamba run -n plotbot_v1_micromamba python -c "
import sys
packages = ['numpy', 'matplotlib', 'pandas', 'scipy']
failed = []
for pkg in packages:
    try:
        __import__(pkg)
        print(f'   ✅ {pkg}')
    except ImportError:
        print(f'   ❌ {pkg}')
        failed.append(pkg)
        
if failed:
    print(f'   ⚠️  Failed imports: {failed}')
    sys.exit(1)
else:
    print('   ✅ All key packages imported successfully')
"

if [ $? -ne 0 ]; then
    echo "❌ Error: Some required packages are not available."
    echo "   The environment may not be set up correctly."
    exit 1
fi

echo ""
echo "🎉 Kernel registration completed successfully!"
