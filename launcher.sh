#!/bin/bash

trap "killall aubionotes; killall mod-host; killall a2jmidi; killall amsynth; killall rakarrack; killall h2cli; killall slgui; killall sooperlooper; killall jackd; killall -s KILL alsa_in; killall -s KILL fluidsynth; exit" SIGINT SIGTERM

if [ "$1" == "-x" ]
then
	killall aubionotes; killall a2jmidi; killall amsynth; killall rakarrack; killall h2cli; killall mod-host; killall slgui; killall sooperlooper; killall jackd; killall -s KILL alsa_in; killall -s KILL fluidsynth
	exit
fi

#home_dir=/root/looper
home_dir=/home/flappix/docs/code/raspberry-looper

cd $home_dir

#dbus-launch jackd -R -d alsa -r 44100 -p 128 -X raw &
#/usr/bin/jackd -dalsa -r44100 -p256 -n2 -Xraw -D -Chw:PCH -Phw:PCH,0 > logs/jack.log 2>&1 &
/usr/bin/jackd -dalsa -r44100 -p256 -n2 -Xraw -D -Chw:CODEC -Phw:PCH,0 > logs/jack.log 2>&1 &
sleep 1
#rakarrack -n -b rakarrack/bank.rkrb -p 0 &

# start mod-host
mod-host -p 5555
sleep 1
echo "load mod-host/mod-host-config.txt" | ncat localhost 5555

sooperlooper -l 8 -c 1 -L sooperlooper/default_session.slsess -m sooperlooper/default_midi.slb > logs/sooperlooper.log 2>&1 &
h2cli -s hydrogen/default.h2song > logs/hydrogen.log 2>&1 &
amsynth -x > logs/amsynth.log 2>&1 &
fluidsynth -s -i -m jack -g 2 fluidsynth/custom.sf2 > logs/fluidsynth.log 2>&1 &
/home/flappix/build/aubio/build/dist/usr/local/bin/aubionotes > logs/aubio.log 2>&1 & #-B 1024 -H 1024 &
a2jmidid > logs/a2jmidid.log 2>&1 &

sleep 2

./midi_manager.py

