#!/bin/bash

pname="keyboardlight-idle"
tmp_dir="$(mktemp -d)"
venv_dir="${tmp_dir}/.venv"
service_file="${tmp_dir}/${pname}.service"
dist_dir="dist"
build_dir="build"

timeout=${1:-20}
brightness=${2:-4}
colour=${3:-"#0000ff"}

set -euo pipefail

echo "creating venv in ${venv_dir}"
python3 -m venv "${venv_dir}"
source "${venv_dir}/bin/activate"

echo "install pyinstaller to ${venv_dir}"
pip install -r requirements.txt

pyinstaller --onefile --noupx --optimize 2 --strip "${pname}.py"

echo "stopping ${pname}"
sudo systemctl stop "${pname}" 2>/dev/null || true

echo "copy dist/${pname} to /usr/local/bin"
sudo cp "${dist_dir}/${pname}" /usr/local/bin/

# systemd Service-Unit schreiben (mit absoluten Pfaden und Logging)
cat >"${service_file}" <<EOF
[Unit]
Description=Turn off Keyboard light after inactivity

[Service]
Type=simple
ExecStartPre=-/usr/bin/killall -9 ${pname}
ExecStart=/usr/local/bin/$pname --brightness ${brightness} --timeout ${timeout} --colour ${colour}
StandardOutput=append:/var/log/${pname}.log
StandardError=append:/var/log/${pname}.log
Restart=on-success
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

sudo mv "${service_file}" "/etc/systemd/system/${pname}.service"

echo "enable and start ${pname}.service"
sudo systemctl daemon-reload
sudo systemctl enable "${pname}.service"
sudo systemctl start "${pname}.service"
