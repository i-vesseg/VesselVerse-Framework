#!/bin/bash

# Environment setup for OpenGL and runtime
export XDG_RUNTIME_DIR=/run/user/0
export LIBGL_ALWAYS_INDIRECT=0
export MESA_GL_VERSION_OVERRIDE=3.3
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/mesa

echo '''
In case of problems:
    1. Make sure VcXsrv is running with these settings:
            - Multiple windows
            - Start no client
            - Native OpenGL: UNCHECKED (important!)
            - Disable access control: CHECKED

    2. (OPTIONAL) -  Run these commands in your terminal:
            xhost +
            export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
   '''
# Set Slicer path to installation directory
SLICER_PATH="/root/slicer/Slicer-5.8.0-linux-amd64/Slicer"

# Set module path
MODULE_PATH="$(dirname "$(dirname "$(realpath "$0")")")/src/slicer_extension/VesselVerse"

if [[ ! -d "$MODULE_PATH" ]]; then
    echo "Module path $MODULE_PATH not found!"
    echo "(Complete path: $(realpath "$MODULE_PATH"))"
    exit 1
fi

echo "Slicer Path: $SLICER_PATH"
echo "Module Path: $MODULE_PATH"

# Function to move SQL files
move_sql_files() {
    echo "Moving SQL files"
    src_dir="$(dirname "$(dirname "$(realpath "$0")")")"
    
    dest_dir="$src_dir/src/slicer_extension/sql_files"
    mkdir -p "$dest_dir"
    
    echo "Destination directory: $dest_dir"
    
    for sql_file in "$src_dir"/*.sql; do
        # Check if there are actually any .sql files
        if [[ -f "$sql_file" ]]; then
            dest_file="$dest_dir/$(basename "$sql_file")"
            mv -f "$sql_file" "$dest_file"
        fi
    done
}

# Call the function to move SQL files
move_sql_files

# Try to detect Mesa version
MESA_VERSION=$(glxinfo | grep "Mesa" | head -n 1 | awk '{print $3}')
echo "Detected Mesa version: $MESA_VERSION"

# Launch Slicer with the VesselVerse module
"$SLICER_PATH" --additional-module-paths "$MODULE_PATH" "$@" --python-code "slicer.util.selectModule('VesselVerse')"

echo ""
echo "Run this in Slicer's Python console to add the module path to the settings permanently!!!"
echo '''
settings = qt.QSettings()
currentPaths = settings.value("Modules/AdditionalPaths") or []
if isinstance(currentPaths, str):
    currentPaths = [currentPaths]
newPath = "/path/to/vesselverse/src/slicer_extension/VesselVerse"
if newPath not in currentPaths:
    currentPaths.append(newPath)
settings.setValue("Modules/AdditionalPaths", currentPaths)
'''