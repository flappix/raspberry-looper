#!/bin/bash

. ./init.sh

# $1 = min bpm
# $2 = max bpm
# $3 = min cntrl value
# $4 = max cntrl value
# $5 = curr cntrl value
function linear_trans()
{
	printf %.0f $(echo "$1 + (($2 - $1)/($4 - $3)) * ( $5 - $3 )" | bc)
}

init=80
min=40
max=200

adj=0
while [ "$adj" == "0" ]
do
	read -n 9 -d 'X' cmd < <(amidi -p $read_port -d)
	if echo $cmd | grep -q "B0 10 " # wait for bpm control
	then
		v=$((16#$(echo $cmd | cut -d ' ' -f3)))
		
		for i in $(seq $init $(($init-$v)))
		do
			amidi -p $write_port --send-hex="900601"
		fi
		
		adj=1
	fi
done
