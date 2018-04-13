#!/bin/sh

lsmod | grep -q snd_virmidi || { echo "module snd_virmidi not loaded"; exit -1; }

korg_port=$(amidi -l | grep nanoKONTROL | cut -d ' ' -f3)
read_port=$(amidi -l | grep Virtual | head -n 1 | cut -d ' ' -f3)
write_port=$(amidi -l | grep Virtual | head -n 2 | tail -n 1 | cut -d ' ' -f3)

#echo "Read port: $read_port"
#echo "Write port: $write_port"
