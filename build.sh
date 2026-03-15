#!/bin/bash
set -e

echo "Installing PyInstaller..."
.venv/bin/python -m pip install pyinstaller pyinstaller-hooks-contrib

echo ""
echo "Building..."
.venv/bin/python -m PyInstaller build.spec --clean

echo ""
echo "Done. Output is at dist/SpeedEditorCustomizer.app"
echo "Run:  open dist/SpeedEditorCustomizer.app"
