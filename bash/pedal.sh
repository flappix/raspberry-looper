#!/bin/bash

. ./init.sh
echo read port $read_port
echo write port $write_port

toggle=0

# list for pedal
while read -s -n 1 input
do
	if [ $input == "b" ]
	then
		amidi -p $write_port --send-hex="900001" # record
		
		if [ $toggle == 0 ]
		then
			amidi -p $write_port --send-hex="900201" # desync
			amidi -p $write_port --send-hex="900401" # de play sync
			toggle=1
		elif [ $toggle == 1 ]
		then
			amidi -p $write_port --send-hex="900101" # sync
			amidi -p $write_port --send-hex="900301" # play sync
			toggle=0
		fi
	fi
done
