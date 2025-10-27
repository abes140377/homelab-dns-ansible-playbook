#!/bin/bash

sudo rm -rf /usr/local/bin/AdGuardHome*
sudo rm -rf /usr/local/bin/data
sudo rm -rf /etc/adguardhome/
sudo rm -rf /etc/systemd/system/AdGuardHome.service

sudo userdel adguardhome
sudo rm -rf /var/lib/adguardhome
