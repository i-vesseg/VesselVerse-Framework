#!/bin/bash

# Exit on any error
set -e

echo "Setting up 3D Slicer installation..."

# Create installation directory
INSTALL_DIR="$HOME/slicer"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Install dependencies
echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y \
    libpulse0 \
    libnss3 \
    libnspr4 \
    libfontconfig1 \
    libxcursor1 \
    libxrender1 \
    libxtst6 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    x11-xserver-utils \
    xorg \
    openbox \
    qt5-default \
    libqt5x11extras5 \
    mesa-utils \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libegl1-mesa \
    mesa-va-drivers \
    mesa-vdpau-drivers \
    mesa-vulkan-drivers \
    libglu1-mesa \
    libopengl0 \
    libglx-mesa0

# Create runtime directory and set permissions
sudo mkdir -p /run/user/0
sudo chmod 700 /run/user/0
sudo chown root:root /run/user/0

# Check if Slicer is already extracted
if [ -d "Slicer-5.8.0-linux-amd64" ]; then
    echo "Slicer directory already exists, skipping download and extraction..."
else
    # Check if archive exists
    if [ -f "slicer.tar.gz" ]; then
        echo "Archive already exists, skipping download..."
    else
        echo "Downloading 3D Slicer..."
        wget -O slicer.tar.gz "https://download.slicer.org/bitstream/679325961357655fd585ffb5"
    fi

    echo "Extracting files..."
    tar xzf slicer.tar.gz
fi

# Find Slicer directory
SLICER_DIR=$(find . -maxdepth 1 -type d -name "Slicer-*" | head -n 1)
SLICER_EXECUTABLE="$SLICER_DIR/Slicer"

# Make executable
chmod +x "$SLICER_EXECUTABLE"

# Create symbolic link
sudo ln -sf "$PWD/$SLICER_EXECUTABLE" /usr/local/bin/Slicer

# Check if configuration already exists in .bashrc
if ! grep -q "# 3D Slicer Configuration" ~/.bashrc; then
    echo "Setting up environment configuration..."
    cat << 'EOF' >> ~/.bashrc

# 3D Slicer Configuration
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
export XDG_RUNTIME_DIR=/run/user/0
export LIBGL_ALWAYS_INDIRECT=0
export QT_QPA_PLATFORM=xcb
export MESA_GL_VERSION_OVERRIDE=3.3
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/mesa
EOF
else
    echo "Configuration already exists in .bashrc"
fi

# Create a wrapper script for Slicer
echo "Creating Slicer wrapper script..."
cat << 'EOF' | sudo tee /usr/local/bin/run-slicer
#!/bin/bash
export XDG_RUNTIME_DIR=/run/user/0
export LIBGL_ALWAYS_INDIRECT=0
export MESA_GL_VERSION_OVERRIDE=3.3
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/mesa

# Try to detect Mesa version
MESA_VERSION=$(glxinfo | grep "Mesa" | head -n 1 | awk '{print $3}')
echo "Detected Mesa version: $MESA_VERSION"

exec Slicer "$@"
EOF

sudo chmod +x /usr/local/bin/run-slicer

echo "
Installation completed successfully!

Before running Slicer, please do the following:

1. Close your current terminal and open a new one

2. Make sure VcXsrv is running with these settings:
   - Multiple windows
   - Start no client
   - Native OpenGL: UNCHECKED (important!)
   - Disable access control: CHECKED

3. Run these commands in your terminal:
   xhost +
   export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
   
4. Try running Slicer using the wrapper script:
    /usr/local/bin/run-slicer
    or 
    sudo run-slicer

Note: If you still experience display issues:
1. Check your Mesa version: glxinfo | grep 'Mesa'
2. Try restarting VcXsrv
3. Make sure you're running the commands as root (using sudo)
"

# Source the new configuration
source ~/.bashrc