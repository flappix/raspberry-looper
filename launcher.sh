#!/bin/bash
kill_str="killall -s KILL aubionotes; killall -s KILL mod-host; killall -s KILL a2jmidid; killall -s KILL amsynth; killall -s KILL h2cli; killall -s KILL slgui; killall -s KILL sooperlooper; killall -s KILL alsa_in; killall -s KILL fluidsynth; exit" # killall -s KILL jackd;
trap "$kill_str" SIGINT SIGTERM

FXLOOPS=1
EXIT=0

POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -l|--fxloops)
    FXLOOPS="$2"
    shift # past argument
    shift # past value
    ;;
    -x|--exit)
    EXIT=1
    shift # past argument
    shift # past value
    ;;
    *)    # unknown option
    POSITIONAL+=("$1") # save it in an array for later
    shift # past argument
    ;;
esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters

stop()
{
	eval $kill_str
}

start()
{
	#home_dir=/root/looper
	#home_dir=/home/flappix/docs/code/raspberry-looper
	home_dir=/home/flappix/docs/Programmierung/raspberry-looper

	cd $home_dir

	mkdir -p /tmp/llogs/

	#dbus-launch jackd -d alsa -X raw > /tmp/llogs/jack.log 2>&1 &
	#dbus-launch jackd -R -d alsa -r 44100 -p 128 -X raw > /tmp/llogs/jack.log &
	#/usr/bin/jackd -dalsa -r44100 -p256 -n2 -Xraw -D -Chw:PCH -Phw:PCH,0 > /tmp/llogs/jack.log 2>&1 &
	#/usr/bin/jackd -dalsa -r44100 -p256 -n2 -Xraw -D -Chw:CODEC -Phw:PCH,0 > /tmp/llogs/jack.log 2>&1 &
	sleep 3
	#rakarrack -n -b rakarrack/bank.rkrb -p 0 &

	mod-host -p 5555 > /tmp/llogs/mod-host-fx.log 2>&1
	
	# start mod-host loop fx
	for i in $(seq 1 $FXLOOPS)
	do
		mod-host -p $((5555+$i)) > /tmp/llogs/mod-host-loop$i.log 2>&1
	done
	
	sooperlooper -l 8 -c 1 -L sooperlooper/default_session.slsess -m sooperlooper/default_midi.slb > /tmp/llogs/sooperlooper.log 2>&1 &
	h2cli -s hydrogen/default.h2song > /tmp/llogs/hydrogen.log 2>&1 &
	amsynth -x > /tmp/llogs/amsynth.log 2>&1 &
	fluidsynth -s -i -m jack -g 2 fluidsynth/custom.sf2 -o synth.polyphony=1 > /tmp/llogs/fluidsynth.log 2>&1 &
	#/home/flappix/aubio-git/build/dist/usr/local/bin/aubionotes > /tmp/llogs/aubio.log 2>&1 & #-B 1024 -H 1024 &
	aubionotes > /tmp/llogs/aubio.log 2>&1 & #-B 1024 -H 1024 &
	a2jmidid > /tmp/llogs/a2jmidid.log 2>&1 &

	sleep 2

	./midi_manager.py $FXLOOPS

}

if [ $EXIT == 1 ]
then
	stop
else
	start
fi
