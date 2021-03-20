#!/bin/bash

export PATH=/home/flappix/docs/code/raspberry-looper/packages/hydrogen97/bin/usr/bin:$PATH
export LD_LIBRARY_PATH=/home/flappix/docs/code/raspberry-looper/packages/hydrogen97/bin/usr/lib:$LD_LIBRARY_PATH

#kill_str="killall -s KILL jackd; killall -s KILL python; killall -s KILL aubionotes; killall -s KILL mod-host; killall -s KILL a2jmidid; killall -s KILL amsynth; killall -s KILL h2cli; killall -s KILL slgui; killall -s KILL sooperlooper; killall -s KILL alsa_in; killall -s KILL fluidsynth; exit" # killall -s KILL jackd;
kill_str="killall -s KILL python; killall -s KILL aubionotes; killall -s KILL mod-host; killall -s KILL a2jmidid; killall -s KILL amsynth; killall -s KILL h2cli; killall -s KILL slgui; killall -s KILL sooperlooper; killall -s KILL alsa_in; killall -s KILL fluidsynth; exit" # killall -s KILL jackd;
trap "$kill_str" SIGINT SIGTERM

FXLOOPS=2
MIDILOOPS=8
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
	home_dir=/home/flappix/docs/code/raspberry-looper
	#home_dir=/home/flappix/docs/Programmierung/raspberry-looper

	cd $home_dir

	mkdir -p /tmp/llogs/

	#dbus-launch jackd -d alsa -X raw > /tmp/llogs/jack.log 2>&1 &
	#dbus-launch jackd -d alsa -X raw -S -p 512 > /tmp/llogs/jack.log 2>&1 &
	#/usr/bin/jackd -dalsa -r44100 -p256 -n2 -Xraw -D -Chw:PCH -Phw:PCH,0 > /tmp/llogs/jack.log 2>&1 &
	#/usr/bin/jackd -dalsa -r44100 -p256 -n2 -Xraw -D -Chw:CODEC -Phw:PCH,0 > /tmp/llogs/jack.log 2>&1 &

	# wait until jack started
	while ! jack_lsp > /dev/null 2>&1; do sleep 0.1; done

	mod-host -p 5555 > /tmp/llogs/mod-host-fx.log 2>&1
	while ! jack_lsp | grep "mod-host:"; do
		sleep 0.1
	done
	
	# start mod-host loop fx
	#for i in $(seq 1 $FXLOOPS)
	#do
	#	mod-host -p $((5555+$i)) > /tmp/llogs/mod-host-loop$i.log 2>&1
	#	while ! jack_lsp | grep "mod-host-0$i:"; do
	#		sleep 0.1
    #    done
	#done
	
	fluidsynth -s -i -m jack -g 2 fluidsynth/custom.sf2 -o synth.polyphony=1 > /tmp/llogs/fluidsynth.log 2>&1 &
	
	# start synthesizers
	#for i in $(seq 1 $MIDILOOPS)
	#do
	#	fluidsynth -s -i -m jack -g 2 fluidsynth/custom.sf2 -o synth.polyphony=1 -o shell.port=$((9800 + $i)) > /tmp/llogs/fluidsynth-loop$i.log 2>&1 &
	#	sleep 0.1
	#done
	
	#sooperlooper -l 8 -c 1 -L sooperlooper/default_session.slsess -m sooperlooper/default_midi.slb > /tmp/llogs/sooperlooper.log 2>&1 &
	python /home/flappix/docs/code/jacklooper/looper.py -l 8 &
	h2cli -s hydrogen/default.h2song > /tmp/llogs/hydrogen.log 2>&1 &
	amsynth -x > /tmp/llogs/amsynth.log 2>&1 &
	
	fluidsynth -s -i -m jack -g 2 fluidsynth/custom.sf2 -o synth.polyphony=1 > /tmp/llogs/fluidsynth.log 2>&1 &
	#/home/flappix/aubio-git/build/dist/usr/local/bin/aubionotes > /tmp/llogs/aubio.log 2>&1 & #-B 1024 -H 1024 &
	aubionotes > /tmp/llogs/aubio.log 2>&1 & #-B 1024 -H 1024 &
	a2jmidid > /tmp/llogs/a2jmidid.log 2>&1 &

	./midi_manager.jacklooper.py $FXLOOPS

}

if [ $EXIT == 1 ]
then
	stop
else
	start
fi
