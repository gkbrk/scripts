#!/bin/sh
systemctl start bluetooth
{ echo "power on"; sleep 2; echo "connect 30:21:AE:AC:49:37"; sleep 3; } | bluetoothctl
