# VesselVerse: 3D Slicer Setup Guide

## Windows Installation

### 1. Install 3D Slicer
1. Download [3D Slicer](https://download.slicer.org/) (Recommended version 5.6.2)
2. Run the installer
3. Choose default options during installation

### 2. Configure Python Environment
```powershell
# Open PowerShell as Administrator
# Set-ExecutionPolicy RemoteSigned # (Optional) 
python -m pip install --upgrade pip
pip install nibabel numpy pandas SimpleITK
```

### 3. Install VesselVerse Module

#### Method A: Using Extension Manager
1. Open 3D Slicer
2. Navigate to Edit → Application Settings → Modules
3. Click "Add" under Additional Module Paths
4. Browse to: `C:\path\to\vesselverse\src\slicer_extension\VesselVerse`
5. Restart 3D Slicer

#### Method B: Manual Installation
```powershell
# Copy module to Slicer's extension directory
$SLICER_HOME = "C:\Program Files\Slicer 5.2.1"
Copy-Item -Path "src\slicer_extension\VesselVerse" -Destination "$SLICER_HOME\Extensions" -Recurse
```

## Linux Installation

### 1. Install 3D Slicer

#### Ubuntu/Debian
```bash
bash /path/to/vesselverse/vesselverse/scripts/install_slicer.sh
```

### 2. Configure Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install nibabel numpy pandas SimpleITK
```

### 3. Install VesselVerse Module

#### Method A: Using Extension Manager
1. Open 3D Slicer
2. Navigate to Edit → Application Settings → Modules
3. Click "Add" under Additional Module Paths
4. Browse to: `/path/to/vesselverse/src/slicer_extension/VesselVerse`
5. Restart 3D Slicer

#### Method B: Manual Installation
```bash
# For single user
mkdir -p ~/.local/share/3DSlicer/Extensions
cp -r src/slicer_extension/VesselVerse ~/.local/share/3DSlicer/Extensions/

# For all users
sudo cp -r src/slicer_extension/VesselVerse /opt/Slicer-5.2.1-linux-amd64/Extensions/
```

## Verify Installation

1. Start 3D Slicer
2. Open Python Console (View → Python Interactor)
3. Run verification code:
```python
import slicer
print(slicer.util.moduleNames())  # Should list 'VesselVerse'
```

## Environment Variables

### Windows
```powershell
# Add to System Environment Variables
$ENV:PYTHONPATH += ";C:\path\to\vesselverse\src"
$ENV:SLICER_EXTENSIONS_DIR = "C:\Program Files\Slicer 5.2.1\Extensions"
```

### Linux
```bash
# Add to ~/.bashrc
export PYTHONPATH="${PYTHONPATH}:/path/to/vesselverse/src"
export SLICER_EXTENSIONS_DIR="/opt/Slicer-5.2.1-linux-amd64/Extensions"
```

## Troubleshooting

### Module Not Found
```python
# In Slicer's Python Console
import sys
print(sys.path)  # Verify module path is included
print(slicer.app.settings().value("Modules/AdditionalPaths"))
```

### Permission Issues (Linux)
```bash
# Fix permissions
sudo chmod -R 755 /opt/Slicer-5.2.1-linux-amd64/Extensions/VesselVerse
sudo chown -R $USER:$USER ~/.local/share/3DSlicer
```

### Common Errors

1. **ImportError: No module named 'VesselVerse'**
   - Verify module path in Slicer settings
   - Check file permissions
   - Restart Slicer

2. **Failed to load module**
   - Check Python dependencies
   - Verify Slicer version compatibility
   - Check system dependencies

3. **GUI elements not displaying**
   - Clear Slicer settings: Delete `~/.config/NA-MIC` (Linux) or `%APPDATA%\NA-MIC` (Windows)
   - Restart Slicer

## Additional Resources

- [3D Slicer Documentation](https://www.slicer.org/wiki/Documentation/4.10/Training)
- [Extension Development Guide](https://www.slicer.org/wiki/Documentation/Nightly/Developers/Modules)
- [Troubleshooting Guide](https://www.slicer.org/wiki/Documentation/4.10/FAQ/Installation)