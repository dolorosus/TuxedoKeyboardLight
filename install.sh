#!/bin/bash
#
#
#

export pname="KeyboardLightControl"

mkdir "/tmp/$pname"
rm -rf "/tmp/$pname/*"

set -e
echo "creating venv in /tmp/.venv$pname"
python3 -m venv "/tmp/.venv$pname"
. "/tmp/.venv$pname/bin/activate"

echo "install pyinstaller to /tmp/.venv$pname"
pip install -r requirements.txt
set +e

rm -rf {dist,build} &>/dev/null
set -e
pyinstaller --onefile --noupx --optimize 2 --strip "$pname.py"
set +e
echo "systemctl stop $pname"
sudo systemctl stop "$pname" 2>/dev/null

set -e
echo cp "dist/$pname" /usr/local/bin
sudo cp "dist/$pname" /usr/local/bin 

[ -f "/etc/systemd/system/$pname.service" ] || {
    echo "no service file found. Generating a new one as /etc/systemd/system/$pname.service"
cat <<EOF >>"/tmp/$pname.service"
[Unit]
Description=Turn off Keyboard light after inactivity

[Service]
Type=simple

StandardOutput="/var/log/$pname.log"
StandardError="/var/log/$pname.log"

ExecStartPre=-/usr/bin/killall -9 "$pname"
ExecStart="/usr/local/bin/$pname" --brightness 5 --timeout 20 

RestartSec=2
Restart=on-success

[Install]
WantedBy=multi-user.target

EOF

    sudo mv "/tmp/$pname.service" "/etc/systemd/system/$pname.service"
}

echo "enable and start service"
sudo systemctl enable "$pname.service"
sudo systemctl start "$pname.service"
