#!/bin/bash 
 
# Download Slicer 
echo "Downloading Slicer..." 
if [ -f Slicer-5.6.2-linux-amd64.tar.gz ]; then 
    echo "Slicer-5.6.2-linux-amd64.tar.gz already exists." 
else 
    wget https://download.slicer.org/bitstream/660f92ed30e435b0e355f1a4 -O Slicer-5.6.2-linux-amd64.tar.gz 
    if [ $? -ne 0 ]; then 
        echo "Failed to download Slicer. Exiting..." 
        exit 1 
    fi 
fi 
 
# Extract to /opt 
echo "Extracting Slicer to /opt..." 
if [ -d /opt/Slicer-5.6.2-linux-amd64 ]; then 
    echo "/opt/Slicer-5.6.2-linux-amd64 already exists." 
    echo "Deleting existing /opt/Slicer-5.6.2-linux-amd64..." 
    sudo rm -rf /opt/Slicer-5.6.2-linux-amd64 
fi 
sudo tar xzf Slicer-5.6.2-linux-amd64.tar.gz -C /opt/ 
 
# Create symbolic link 
echo "Creating symbolic link..." 
sudo ln -s /opt/Slicer-5.6.2-linux-amd64/Slicer /usr/local/bin/Slicer 
 
# Install dependencies 
echo "Installing dependencies..." 
sudo apt-get update 
sudo apt-get install -y \ 
    libpulse-dev \ 
    libnss3 \ 
    libglu1-mesa \ 
    libsm6 \ 
    libxt6 
 
echo "Slicer installation complete." 
echo "Run 'Slicer' to start 3D Slicer."