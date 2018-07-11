#!env python

from pynput import keyboard
import rtmidi

notes = {'c': 0, 'c#': 1, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'bb': 10, 'b': 11}

def mod (note, octave, channel=0):
	return [144+channel, notes[note] + 12*octave, 127]

print(notes)

keymap = {'a': [mod ('d', 4, 1), mod ('f', 4, 1), mod ('a', 5, 1)], # Dm
		  'q': [mod ('f', 4, 1), mod ('a', 4, 1), mod ('c', 5, 1)], # F
		  's': [mod ('a', 4, 1), mod ('c#', 4, 1), mod ('e', 5, 1)], # A
		  'x': [mod ('a', 4, 1), mod ('c#', 4, 1), mod ('e', 5, 1), mod('g', 5, 1)], # A7
		  'w': [mod ('c', 4, 1), mod ('e', 4, 1), mod ('g', 5, 1)], # C
		  'd': [mod ('g', 4, 1), mod ('bb', 4, 1), mod ('d', 5, 1)], # Gm
		  'c': [mod ('bb', 4, 1), mod ('d', 4, 1), mod ('f', 5, 1)], # Bb
		  'f': [mod ('d', 7)],	
		  'g': [mod ('e', 7)],	
		  'h': [mod ('f', 7)],	
		  'j': [mod ('g', 7)],	
		  'k': [mod ('a', 7)],	
		  'l': [mod ('bb', 7)],	
		  'o': [mod ('c#', 8)],	
		  'p': [mod ('d', 8)]}	

active_notes = []

midiOut = rtmidi.MidiOut()
print ( midiOut.get_ports() )
midiOut.open_port(1);
	

def on_press(key):
	try:
		k = format(key.char)
		if k in keymap:
			for i in keymap[k]:
				if not i in active_notes:
					midiOut.send_message (i)
					active_notes.append (i);
					print(i)

	except AttributeError:
		pass

def on_release(key):
	try:
		k = format(key.char)
		if k in keymap:
			for i in keymap[k]:
				# note off
				midiOut.send_message ([128+i[0]-144]+i[1:])
				if i in active_notes:
					active_notes.remove (i);
				print([128]+i[1:])
	except AttributeError:
		pass

# Collect events until released
with keyboard.Listener(
	on_press=on_press,
	on_release=on_release) as listener:
	listener.join()
