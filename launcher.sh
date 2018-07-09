#!/bin/bash

trap "killall aubionotes; killall a2jmidi; killall amsynth; killall rakarrack; killall h2cli; killall slgui; killall sooperlooper; killall jackd; killall -s KILL alsa_in; killall -s KILL fluidsynth; exit" SIGINT SIGTERM

if [ $1 == '-x' ]
then
	killall aubionotes; killall a2jmidi; killall amsynth; killall rakarrack; killall h2cli; killall slgui; killall sooperlooper; killall jackd; killall -s KILL alsa_in; killall -s KILL fluidsynth
	exit
fi

home_dir=/root/looper

cd $home_dir

#jackd -S -R -d alsa -r 48000 -p 256 &
dbus-launch jackd -R -d alsa -n 3 -r 44100 -p 256 --shorts -C hw:1,0 -P hw:1,0 &
sleep 1
#alsa_in -d usb &
rakarrack -n -b rakarrack/bank.rkrb -p 0 &
sooperlooper -l 8 -c 1 -L sooperlooper/default_session.slsess -m sooperlooper/default_midi.slb &
#slgui -l 8 -c 1 -L sooperlooper/default_session.slsess -m sooperlooper/default_midi.slb &
#slgui &
#h2cli -p hydrogen/playlist.h2playlist &
h2cli -s hydrogen/default.h2song > /dev/null 2>&1 &
sleep 1
amsynth -x &
fluidsynth -s -i -m jack -g 2 fluidsynth/custom.sf2 &
aubionotes &
a2jmidid --export-hw &
#./midi_patchbay.sh &&
#./jack_patchbay.sh &&
./midi_manager.py
