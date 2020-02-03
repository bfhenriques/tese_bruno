#!/usr/bin/env bash
mkdir /media/$USER/rootfs/home/pi/dmmd/
cp -r ../monitor /media/$USER/rootfs/home/pi/dmmd/
cp -r ../raspberry /media/$USER/rootfs/home/pi/dmmd/
sudo cp wpa_supplicant.conf /media/$USER/rootfs/etc/wpa_supplicant/wpa_supplicant.conf
