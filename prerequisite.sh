#!/bin/bash
# pipefail so a failed `curl ... | sh` isn't masked by the piped shell exiting 0.
set -eo pipefail

# moreutils ships a different `parallel`; version-check to detect GNU specifically.
parallel --version 2>/dev/null | grep -q GNU || sudo apt-get install -y parallel
dpkg -s build-essential cmake libyaml-dev nlohmann-json3-dev >/dev/null 2>&1 \
    || sudo apt-get install -y build-essential cmake libyaml-dev nlohmann-json3-dev

curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv sync
# uv tool venv needs colcon-core + extensions installed together.
command -v colcon >/dev/null 2>&1 \
    || uv tool install colcon-core --with colcon-common-extensions

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
# nvm.sh is not `set -e`-safe; source it leniently, then re-arm.
set +e
source "$HOME/.nvm/nvm.sh"
set -e
nvm install 21.7.3
pushd frontend
npm install
popd

./download_map.sh
