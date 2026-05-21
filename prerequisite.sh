#!/bin/bash
# Fail fast: a swallowed failure here (uv sync, npm install, ...) would
# otherwise surface only much later as a runtime crash. pipefail also
# catches a failed download in `curl ... | sh`.
set -eo pipefail

# Install packages (skip the sudo/apt round-trip when already present)
command -v parallel >/dev/null 2>&1 || sudo apt-get install -y parallel

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# Install Python packages
uv sync

# Install nodejs
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
# nvm.sh is not written for `set -e`; source it leniently, then re-arm.
set +e
source "$HOME/.nvm/nvm.sh"
set -e
nvm install 21.7.3
# Install npm
pushd frontend
npm install
popd # frontend

# Install necessary data
## map
./download_map.sh
