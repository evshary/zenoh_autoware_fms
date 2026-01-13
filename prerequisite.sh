#!/bin/bash

# Install packages
sudo apt install parallel

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# Install Python packages
uv sync

# Install nodejs
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
source "$HOME/.nvm/nvm.sh"
nvm install 21.7.3
# Install npm
pushd frontend
npm install
popd # frontend

# Install necessary data
## map
./download_map.sh
