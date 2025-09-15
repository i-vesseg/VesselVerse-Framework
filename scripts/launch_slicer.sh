#!/bin/bash

CONFIG_FILE="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")/config.sh"

if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo "Configuration file $CONFIG_FILE not found!"
    echo "(Complete path: $(realpath "$CONFIG_FILE"))"
    exit 1
fi

MODULE_PATH="$(dirname "$(dirname "$(realpath "$0")")")/src/slicer_extension/VesselVerse"

if [[ ! -d "$MODULE_PATH" ]]; then
    echo "Module path $MODULE_PATH not found!"
    echo "(Complete path: $(realpath "$MODULE_PATH"))"
    exit 1
fi

echo "Slicer Path: $SLICER_PATH"
echo "Module Path: $MODULE_PATH"

# Launch Slicer with the VesselVerse module
"$SLICER_PATH" --additional-module-paths "$MODULE_PATH" "$@" --python-code "slicer.util.selectModule('VesselVerse')"
# Function to move SQL files to the specified directory

move_sql_files() {
    echo "Moving SQL files"
    src_dir="$(dirname "$(dirname "$(realpath "$0")")")" 
    dest_dir="$src_dir/src/slicer_extension/sql_files"
    mkdir -p "$dest_dir"

    #echo "Source directory: $src_dir"
    echo "Destination directory: $dest_dir"

    for sql_file in "$src_dir"/*.sql; do
        dest_file="$dest_dir/$(basename "$sql_file")"
        mv -f "$sql_file" "$dest_file"
    done
}

# Call the function to move SQL files
move_sql_files


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
