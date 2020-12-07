#!/usr/bin/env bash
apt-get update -y
apt-get upgrade -y
apt-get install python3-pip -y
apt-get install python-picamera python3-picamera
apt-get install -y libdbus-1 libdbus-1-dev
apt-get autoremove -y
pip3 install --upgrade pip
pip3 install -r requirements.txt
chmod +x ../monitor/startup.sh
sudo cp autostart /home/pi/.config/lxsession/LXDE-pi/autostart