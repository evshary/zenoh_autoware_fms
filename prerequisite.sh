#!/bin/bash

# Install poetry
curl -sSL https://install.python-poetry.org | python3 -
poetry config virtualenvs.in-project true


# Install packages
sudo apt install parallel
# Install Python packages
poetry install

# Install nodejs
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
source "$HOME/.nvm/nvm.sh"
nvm install node
# Install npm
cd frontend && npm install

