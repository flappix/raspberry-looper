#!/bin/bash

. ./init.sh

curr_preset=0
amidi -p $write_port --send-hex="C000"$(printf "%02x" $curr_preset) # set first preset to 1


# sync all loops
#for i in {7..0}
#do
#	echo 1 $i
#	amidi -p $write_port --send-hex="B02"$i"7F"
#	echo 2 $i
#	amidi -p $write_port --send-hex="900101"
#	echo 3 $i
#	amidi -p $write_port --send-hex="900301"
#done
amidi -p $write_port --send-hex="B02017F" # select first loop

while true
do
	read -n 9 -d 'X' cmd < <(amidi -p $read_port -d)
	killall amidi
	
	# next preset
	if [ "$cmd" == "B0 3B 7F" ]
	then
		if [ $curr_preset -lt 59 ]
		then
			((curr_preset++))
			amidi -p $write_port --send-hex="C000"$(printf "%02x" $curr_preset)
		fi
	
	# prev preset
	elif [ "$cmd" == "B0 3A 7F" ]
	then
		if [ $curr_preset -gt 0 ]
		then
			((curr_preset--))
			amidi -p $write_port --send-hex="C000"$(printf "%02x" $curr_preset)
		fi
	fi
done
