#!/bin/bash

portfile=/tmp/midi_ports.txt

korg=""
sl=""
rr_in=""
rr_out=""
hydrogen=""
amsynth=""
amsynth_jack=""
fluidsynth=""
aubio=""

while [ "$korg" == "" ] || [ "$korg_jack" == "" ] || [ "$sl" == "" ] || [ "$rr_in" == "" ] || [ "$rr_out" == "" ] || [ "$hydrogen" == "" ] || [ "$amsynth_jack" == "" ] || [ "$aubio" == "" ] || [ "$fluidsynth" == "" ]
do
	echo "connecting..."
	echo korg $korg
	echo korg_jack $korg_jack
	echo sl $sl
	echo rr_in $rr_in
	echo rr_out $rr_out
	echo hydrogen $hydrogen
	#echo amsynth $amsynth
	echo amsynth_jack $amsynth_jack
	echo fluidsynth $fluidsynth
	echo aubio $aubio
	
	korg=$(aconnect -l | grep nanoKONTROL2 | grep client | cut -d ' ' -f2 | tr -d ':')
	sl=$(aconnect -l | grep sooperlooper | grep client | cut -d ' ' -f2 | tr -d ':')
	rr_in=$(aconnect -l | grep rakarrack | grep IN -B 1 | grep client | cut -d ' ' -f2 | tr -d ':')
	rr_out=$(aconnect -l | grep rakarrack | grep OUT -B 1 | grep client | cut -d ' ' -f2 | tr -d ':')
	amsynth=$(aconnect -l | grep amsynth | grep client | cut -d ' ' -f2 | tr -d ':')
	hydrogen=$(aconnect -l | grep Hydrogen | grep client | cut -d ' ' -f2 | tr -d ':')
	# note: uses jack_connect, not aconnect
	korg_jack=$(jack_lsp | grep "a2j:nanoKONTROL2" | grep capture) 
	amsynth_jack=$(jack_lsp | grep "amsynth:midi_in") 
	fluidsynth=$(jack_lsp | grep 'fluidsynth:midi') 
	aubio=$(jack_lsp | grep "aubio:midi_out_1") 
	sleep 1
done

>$portfile
echo $korg >> $portfile
echo $sl >> $portfile
echo $rr_in >> $portfile
echo $rr_out >> $portfile
echo $hydrogen >> $portfile
echo $amsynth >> $portfile
echo $amsynth_jack >> $portfile
echo $korg_jack >> $portfile
echo $fluidsynth >> $portfile
echo $aubio >> $portfile

aconnect $korg $hydrogen
aconnect $korg $sl
aconnect $korg $rr_in
#aconnect $rr_out $amsynth

exit 0
