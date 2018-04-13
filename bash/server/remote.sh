#!/bin/bash

# launch with nc6 -l localhost -p 1337 -e ./server.sh

lsmod | grep -q snd_virmidi || { echo "module snd_virmidi not loaded"; exit; }

while read -s input
do
	param=""
	case  $input in
		"record")	param="0001" ;;
		"select1")	param="0500" ;;
		"select2")	param="0501" ;;
		"select3")	param="0502" ;;
		"select4")	param="0503" ;;
		"select5")	param="0504" ;;
		"select6")	param="0505" ;;
		"select7")	param="0506" ;;
		"select8")	param="0507" ;;
		"select9")	param="0508" ;;
		"select10")	param="0509" ;;
	esac
	
	echo "09$param" >> log
	amidi -p hw:2,0 -S "90$param"
done
