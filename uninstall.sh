#!/bin/bash
#
#

pname="keyboardlight-idle"
service_file="$pname.service"

sudo systemctl disable ${service_file}
sudo rm /etc/systemd/system/${service_file}
sudo rm /usr/local/bin/${pname}
