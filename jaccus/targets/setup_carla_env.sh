#!/bin/bash
# CARLA Environment Setup Script for Ubuntu
# This script sets up the Python path for CARLA and its agents

echo "🚗 Setting up CARLA environment for JACCUS..."

# Define CARLA installation root
export CARLA_ROOT="/home/seame/carla-simulator"

# Check if CARLA installation exists
if [ ! -d "$CARLA_ROOT" ]; then
    echo "❌ CARLA installation not found at $CARLA_ROOT"
    echo "   Please install CARLA or update CARLA_ROOT path"
    return 1 2>/dev/null || exit 1
fi

echo "✅ CARLA installation found at: $CARLA_ROOT"

# Add CARLA Python API directories to PYTHONPATH
export PYTHONPATH="${CARLA_ROOT}/PythonAPI:${PYTHONPATH}"
export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla:${PYTHONPATH}"
echo "📦 Added PythonAPI directories to PYTHONPATH"

# Add CARLA egg files for different Python versions
CARLA_EGG_37="${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.15-py3.7-linux-x86_64.egg"
CARLA_EGG_27="${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.15-py2.7-linux-x86_64.egg"

# Prefer Python 3.7 egg (most compatible)
if [ -f "$CARLA_EGG_37" ]; then
    export PYTHONPATH="${CARLA_EGG_37}:${PYTHONPATH}"
    echo "🥚 Added CARLA Python 3.7 egg to PYTHONPATH"
elif [ -f "$CARLA_EGG_27" ]; then
    export PYTHONPATH="${CARLA_EGG_27}:${PYTHONPATH}"
    echo "🥚 Added CARLA Python 2.7 egg to PYTHONPATH (fallback)"
else
    echo "⚠️  No CARLA egg files found in ${CARLA_ROOT}/PythonAPI/carla/dist/"
fi

# Set additional CARLA environment variables
export CARLA_SERVER="localhost"
export CARLA_PORT="2000"

# Test CARLA imports (skip if causes issues)
echo "🧪 Testing CARLA imports (quick test)..."
if python3 -c "import sys; sys.path.insert(0, '${CARLA_ROOT}/PythonAPI'); import carla" 2>/dev/null; then
    echo "✅ CARLA module can be imported"

    # Test agents separately (more likely to cause segfaults)
    if python3 -c "import sys; sys.path.insert(0, '${CARLA_ROOT}/PythonAPI'); from agents.navigation.behavior_agent import BehaviorAgent" 2>/dev/null; then
        echo "✅ CARLA agents can be imported"
    else
        echo "⚠️  CARLA agents import may have issues (but should work in JACCUS)"
    fi
else
    echo "⚠️  CARLA import test failed (but may work in your application)"
fi

echo ""
echo "🎉 CARLA environment setup complete!"
echo "📝 Environment variables set:"
echo "   CARLA_ROOT=$CARLA_ROOT"
echo "   CARLA_SERVER=$CARLA_SERVER"
echo "   CARLA_PORT=$CARLA_PORT"
echo ""
echo "💡 To make this permanent, add this line to your ~/.bashrc:"
echo "   source $(pwd)/setup_carla_env.sh"
