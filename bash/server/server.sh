#!/bin/bash

trap "killall nc6; exit" SIGINT SIGTERM

# remote commands
nc6 -l localhost -p 1337 -e ./remote.sh &

# list for pedal
while read -s -n 1 input
do
	[ $input == "b" ] && amidi -p hw:2,0 -S "900001"
done

