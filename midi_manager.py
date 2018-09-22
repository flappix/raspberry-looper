#!/usr/bin/python3

import sys
import os
import stat
import time
import _thread
import liblo
from subprocess import call
import math
import socket
import pdb
import struct

gpio = False
try:
	import RPi.GPIO as GPIO
	gpio = True
except ModuleNotFoundError:
	print ('no gpio available')

import jack



########################################################################
## config
########################################################################

osc_write_port = 9951
osc_read_port = 9952
save_dir = "/mnt/data/saved_loops/"

########################################################################
## prepare
########################################################################

# footswitch
if gpio:
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

started = False
jackclient = jack.Client ('MidiManager')
#jackclient.activate()

modhost_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
modhost_client.connect ( ("localhost", 5555) )

def getPort (ports, keywords):
	for i in ports:
		if sum([1 for k in keywords if k in i.name]) == len(keywords):
			return i
	
	return None

def connect_ports (ports, pin, pout, disconnect=False):
	
	if (not ports[pin] is None) and  (not ports[pout] is None):
		try:
			if not disconnect:
				jackclient.connect (ports[pin], ports[pout])
			else:
				jackclient.disconnect (ports[pin], ports[pout])
		except jack.JackError as e:
			print (e)
	else:
		if ports[pin] is None:
			print ('port ' + pin + ' is  None')
		if ports[pout] is None:
			print ('port ' + pout + ' is  None')

def disconnect_ports (ports, pin, pout):
	connect_ports (ports, pin, pout, disconnect=True)

### audio ports
midi_ports = {}
audio_ports = {}
my_midi_ports = {}

def setup_connections():
	global midi_ports
	global audio_ports
	global my_midi_ports
	
	all_audio_ports = [i for i in jackclient.get_ports() if i.__class__ == jack.Port]
	port_desc = [('capture_1', ['system:capture_1']),
				 ('capture_2', ['system:capture_2']),
				 ('playback_1', ['system:playback_1']),
				 ('playback_2', ['system:playback_2']),
				 #('rr_in', ['rakarrack:in_1']),
				 #('rr_out', ['rakarrack:out_1']),
				 ('hydrogen_out', ['Hydrogen', 'out_R']),
				 ('aubio_in', ['aubio', 'in']),
				 ('amsynth_out', ['amsynth', 'R out']),
				 ('fluidsynth_out', ['fluidsynth', 'right']),
				 ('sl_out_all', ['sooperlooper', 'common_out_1']),
				 ('sl_in_all', ['sooperlooper', 'common_in_1'])] + \
				 [('sl_out_' + str(i+1), ['sooperlooper', 'loop' + str(i) + '_out_1']) for i in range(8)] + \
				 [('sl_in_' + str(i+1), ['sooperlooper', 'loop' + str(i) + '_in_1']) for i in range(8)] + \
				 [('fx_in_' + str(i), ['effect_' + str(i), 'in']) for i in range(6+1)] + \
				 [('fx_out_' + str(i), ['effect_' + str(i), 'out']) for i in range(6+1)]
	audio_ports = {k: getPort (all_audio_ports, v) for (k, v) in port_desc}

	# connecting ports

	#connect_ports (audio_ports, 'capture_1', 'rr_in')
	#connect_ports (audio_ports, 'capture_2', 'rr_in')

	connect_ports (audio_ports, 'capture_1', 'aubio_in')
	connect_ports (audio_ports, 'capture_2', 'aubio_in')

	for i in ['hydrogen_out', 'amsynth_out', 'fluidsynth_out']:
		connect_ports (audio_ports, i, 'playback_1')
		connect_ports (audio_ports, i, 'playback_2')

	for i in ['amsynth_out', 'fluidsynth_out']:
		connect_ports (audio_ports, i, 'sl_in_all')

	connect_ports (audio_ports, 'sl_out_all', 'playback_1')
	connect_ports (audio_ports, 'sl_out_all', 'playback_2')

	connect_ports (audio_ports, 'capture_1', 'fx_in_0')
	connect_ports (audio_ports, 'capture_2', 'fx_in_0')

	for i in range(6):
		connect_ports (audio_ports, 'fx_out_' + str(i), 'fx_in_' + str(i+1))

	connect_ports (audio_ports, 'fx_out_6', 'playback_1')
	connect_ports (audio_ports, 'fx_out_6', 'playback_2')
	connect_ports (audio_ports, 'fx_out_6', 'sl_in_all')
		

	### foreign midi ports
	all_midi_ports = [i for i in jackclient.get_ports() if i.__class__ == jack.MidiPort]
	port_desc = [('korg_in', ['system', 'capture']),
				 ('korg_out', ['system', 'playback']),
				 ('sl', ['sooperlooper', 'playback']),
				 #('rr', ['rakarrack', 'in']),
				 ('hydrogen', ['hydrogen', 'midi', 'RX']),
				 ('amsynth', ['amsynth', 'midi_in']),
				 ('fluidsynth', ['fluidsynth', 'midi']),
				 ('aubio', ['aubio', 'midi_out']),
				 ('mod-host', ['mod-host', 'midi_in'])]
				 
	midi_ports = {k: getPort (all_midi_ports, v) for (k, v) in port_desc}

	connect_ports (midi_ports, 'korg_in', 'sl')
	connect_ports (midi_ports, 'korg_in', 'hydrogen')
	#connect_ports (midi_ports, 'korg_in', 'rr')
	disconnect_ports (midi_ports, 'korg_in', 'mod-host')

	# own midi ports
	my_midi_ports = {'korg_in': jackclient.midi_inports.register ('input'),
					 'korg_out': jackclient.midi_outports.register ('output'),
					 'sl_out': jackclient.midi_outports.register ('sl_out'),
					 'fluidsynth_out': jackclient.midi_outports.register ('fluidsynth_out'),
					 'amsynth_out': jackclient.midi_outports.register ('amsynth_out')};
	#pdb.set_trace()
	jackclient.connect (my_midi_ports['korg_out'].name, midi_ports['korg_out'].name)
	jackclient.connect (midi_ports['korg_in'], my_midi_ports['korg_in'].name)
	jackclient.connect (my_midi_ports['sl_out'].name, midi_ports['sl'].name)
	jackclient.connect (my_midi_ports['fluidsynth_out'].name, midi_ports['fluidsynth'].name)
	jackclient.connect (my_midi_ports['amsynth_out'].name, midi_ports['amsynth'].name)

slider_lst_state = [-1]*8
rot_lst_state = [-1]*8

########################################################################
## buttons, messages
########################################################################

# matrix buttons
def button (x, y, on=True):
	return 32 + (x - 1) + (y - 1)*16


###  0  1  2  3  4  5  6  7
###  8  9 10 11 12 13 14 15
### 16 17 18 19 20 21 22 23
def int2button (i):
	if i in list(range(0,7+1)):
		return i + 31 + 1
	elif i in list(range(8,15+1)):
		return i + 31 + 9
	elif i in list(range(16, 23+1)):
		return i + 31 + 17

	return None

def spec_button (s, on=True):
	if s == 'record':
		return 45
	elif s == 'loop':			# left arrow, bottom
		return 43
	elif s == 'fx':				# right arrow, bottom
		return 44
	elif s == 'drum':			# square, bottom
		return 42
	elif s == 'synth': # triangle, bottom
		return 41
	elif s == 'save': # ball, bottom
		return 45
	elif s == 'load_next': # Track right
		return 59
	elif s == 'load_prev': # Track left
		return 58
	elif s == 'save_blink': # cycle
		return 46
	elif s == 'sync_lfo': # set
		return 60
		
		
	return None

def slider (k, v=127): # n = 1: rotation knobs, n = 2: Slider
	return [176, k-1, v]

def rot (k, v=127):
	return [176, k + 15, v]

def spec_rot (s, v=127):
	global rot_lst_state
	
	if s == 'fx_vol':
		return rot (4, v if v != -1 else rot_lst_state[4-1])
	elif s == 'dry_wet':
		return rot (3, v if v != -1 else rot_lst_state[3-1])

def button2Int (b):
	if b in list(range(32, 39+1)):
		return b - 31 - 1
	elif b in list(range (48, 55+1)): 
		return b - 31 - 9
	elif b in list(range(64, 71+1)):
		return b - 31 - 18 + 1
	
	return None

buttonList = list(range(32, 39+1))+list(range (48, 55+1))+list(range(64, 71+1))
fluidsynth = ['synth', 'drum']  # light synth and drum up to indicate we are selected fluid synth

########################################################################
## variables
########################################################################

#midi = {'korg_in': rtmidi.MidiIn(midiutil.get_api_from_environment(rtmidi.API_UNIX_JACK)), 'korg_out': rtmidi.MidiOut(midiutil.get_api_from_environment(rtmidi.API_UNIX_JACK)), 'sl_out': rtmidi.MidiOut(), 'rr_out': rtmidi.MidiOut(), 'amsynth_out': rtmidi.MidiOut(midiutil.get_api_from_environment(rtmidi.API_UNIX_JACK)), 'fluidsynth_out': rtmidi.MidiOut(midiutil.get_api_from_environment(rtmidi.API_UNIX_JACK)), 'hydrogen_out':  rtmidi.MidiOut(midiutil.get_api_from_environment(rtmidi.API_UNIX_JACK)) }
#queues = { 'out': {}, 'in': {} }
#for i in midi:
#	if 'out' in i:
#		queues['out'][i] = []
#					  select first loop						 	select loop mode
#queues['out']['korg_out'] = [button(1, 1), button(1, 3), spec_button ('loop')]
#queues['out']['sl_out'] = [button (1, 1), ] # select first loop

osc_writer = None
vosc_reader = None
osc_data = None

curr_loaded = -1
loop_state = []


msg = {'record': [144,0,1], 'sync': [144,1,1], 'desync': [144,2,1], 'playsync': [144,3,1], 'deplaysync': [144,4,1], 'incr_bpm': [144,6,1]}
#footswitch = None
#for i in devices.mice:
#	if 'FootSwitch' in i.name:
#		footswitch = i 

curr_loop = 1
sync_switch = True
pedal_pressed = False

mode = 'loop' # loop, fx, drum synth

selected = {'fx': [True] + [False]*5 + [True], 'drum': [True] + [False]*23, 'amsynth': button (1, 1), 'fluidsynth': button(1,1)}

poweroff_counter = 0

led_buttons = list(range(32+1, 39)) + list(range(32+1, 39)) + list(range(41+1,46))+ list(range(48+1, 55)) + list (range(64+1, 71))
display_state = {i: (False, led_buttons[i]) for i in range (len (led_buttons)) };


# replaces read_korg $ write
# reads and writes all midi events
i = 0
@jackclient.set_process_callback
def process(frames):
	#midi_ports['korg_out'].clear_buffer()
	global my_midi_ports
	global i
	global pedal_pressed
	
	if (len(my_midi_ports)>0):
		my_midi_ports['korg_out'].clear_buffer()
		my_midi_ports['sl_out'].clear_buffer()
		my_midi_ports['fluidsynth_out'].clear_buffer()
		my_midi_ports['amsynth_out'].clear_buffer()

		if i == 0:
			#queues['out']['korg_out'] = [button(1, 1), button(1, 3), spec_button ('loop')]
			my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 1), 127))
			my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 3), 127))
			my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button ('loop'), 127))
			#MAYBE we need this?
			my_midi_ports['sl_out'].write_midi_event (0, (176, button (1, 1), 1) ) # select first loop
		
		i += 1
		
		if pedal_pressed:
			if not sync_switch:
				my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button('record'), 127) )
			else:
				my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button('record'), 0))
			
			my_midi_ports['sl_out'].write_midi_event (0, msg['record'])
			pedal_pressed = False
		
		for offset, data in my_midi_ports['korg_in'].incoming_midi_events():
			if len(data) == 3:
				b1, b2, b3 = struct.unpack('3B', data)
				process_korg_in (b2, b3)
				# print('input: ' + str(b2) + ', ' + str(b3))
		
def read_pedal():
	global sync_switch
	global pedal_pressed
#	global footswitch
	
	last_time = 0
	while True:
		if gpio:
			GPIO.wait_for_edge(3, GPIO.FALLING)
		else:
			print('wait for input')
			input()
		
		if time.time() - last_time > 0.4:
			print ("Record")
			#if sync_switch:
			#	queues['out']['korg_out'].append ( spec_button ('record') )
				#queues['out']['sl_out'].append (msg['desync'])
				#queues['out']['sl_out'].append (msg['deplaysync'])
			#else:
			#	queues['out']['korg_out'].append ( spec_button ('record', False) )
				#queues['out']['sl_out'].append (msg['sync'])
				#queues['out']['sl_out'].append (msg['playsync'])
		
			#queues['out']['sl_out'].append (msg['record'])
			pedal_pressed = True
			
			sync_switch = not sync_switch
			last_time = time.time()

########################################################################
## process
########################################################################

def process_korg_in (cc, value):
	global curr_loop
	global mode
	global curr_loaded
	global osc_data
	global slider_lst_state
	global rot_lst_state
	global selected
	global poweroff_counter

	if (value > 0):
		#power off
		if cc == spec_button ('save_blink'):
			poweroff_counter += 1
			if poweroff_counter == 3:
				#call (["systemctl", "stop", "looper.service"])
				call (["poweroff"])
				
		else :
			poweroff_counter = 0
			
			# select mode
			if cc == spec_button ('loop'):
				if mode != 'loop':
					updateLeds (mode, 'loop')
					mode = 'loop'
					
					connect_ports (midi_ports, 'korg_in', 'sl')
					disconnect_ports (midi_ports, 'korg_in', 'amsynth')
					disconnect_ports (midi_ports, 'korg_in', 'mod-host')
					
					connect_ports (audio_ports, 'fx_out_6', 'playback_1')
					connect_ports (auido_ports, 'fx_out_6', 'playback_2')
					
			elif cc == spec_button ('fx'):
				if mode != 'fx':
					updateLeds (mode, 'fx')
					mode = 'fx'
					
					disconnect_ports (midi_ports, 'aubio', 'amsynth')
					disconnect_ports (midi_ports, 'aubio', 'fluidsynth')
					disconnect_ports (midi_ports, 'korg_in', 'sl')
					disconnect_ports (midi_ports, 'korg_in', 'amsynth')
					disconnect_ports (midi_ports, 'korg_in', 'fluidsynth')
					disconnect_ports (midi_ports, 'korg_in', 'hydrogen')
					
					connect_ports (midi_ports, 'korg_in', 'mod-host')
					
					connect_ports (audio_ports, 'fx_out_6', 'playback_1')
					connect_ports (audio_ports, 'fx_out_6', 'playback_2')
					
			elif cc == spec_button ('drum'):
				if mode != 'drum':
					updateLeds (mode, 'drum')
					mode = 'drum'
					
					disconnect_ports (midi_ports, 'korg_in', 'sl')
					disconnect_ports (midi_ports, 'korg_in', 'amsynth')
					disconnect_ports (midi_ports, 'korg_in', 'fluidsynth')
					disconnect_ports (midi_ports, 'korg_in', 'mod-host')
					disconnect_ports (midi_ports, 'aubio', 'amsynth')
					disconnect_ports (midi_ports, 'aubio', 'fluidsynth')
					
					connect_ports (midi_ports, 'korg_in', 'hydrogen')
					
					connect_ports (audio_ports, 'fx_out_6', 'playback_1')
					connect_ports (auido_ports, 'fx_out_6', 'playback_2')

			elif cc == spec_button ('synth'):
				
				disconnect_ports (midi_ports, 'korg_in', 'sl')
				disconnect_ports (midi_ports, 'korg_in', 'mod-host')
				disconnect_ports (audio_ports, 'fx_out_6', 'playback_1')
				disconnect_ports (audio_ports, 'fx_out_6', 'playback_2')
				
				if mode != 'synth': # amsynth
					updateLeds (mode, 'synth')
					mode = 'synth'
					
					my_midi_ports['fluidsynth_out'].write_midi_event (0, (176,123,0) ) # kill every noteon event from fluidsynth
					
					disconnect_ports (midi_ports, 'aubio', 'fluidsynth')
					connect_ports (midi_ports, 'aubio', 'amsynth')
					connect_ports (midi_ports, 'korg_in', 'amsynth')
					disconnect_ports (midi_ports, 'korg_in', 'fluidsynth')
					
				else: # fluidsynth
					updateLeds (mode, fluidsynth)
					mode = fluidsynth
					
					my_midi_ports['amsynth_out'].write_midi_event (0, (176,123,0) ) # kill every noteon event from amsynth
					
					connect_ports (midi_ports, 'aubio', 'fluidsynth')
					disconnect_ports (midi_ports, 'aubio', 'amsynth')
					connect_ports (midi_ports, 'korg_in', 'fluidsynth')
					disconnect_ports (midi_ports, 'korg_in', 'amsynth')
						
					
			elif cc == spec_button ('save'):
				save()
			elif cc == spec_button ('load_next'):
				if latest_session() > curr_loaded:
					curr_loaded += 1
					load()
			elif cc == spec_button ('load_prev'):
				if 0 < curr_loaded:
					curr_loaded -= 1
					load()
			
			### no mode button, one of the matrix button
			else:
				if mode == 'loop':
					if cc >= 32 and cc <= 39: # select loop
						if cc - 31 != curr_loop:
							#queues['out']['korg_out'].append ( button (curr_loop, 1, False) )
							#queues['out']['korg_out'].append ( button (curr_loop, 3, False) )
							
							my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 1), 0))
							my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 3), 0))
							
							curr_loop = cc - 31
							
							my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 1), 127))
							my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 3), 127))
							
							
							
					if cc >= 48 and cc <= 55 and cc == 127: # pause loop
						#time.sleep (0.01)
						liblo.send (osc_writer, "/sl/" + str(cc - 48) + "/get", "state", "osc.udp://localhost:9952", "osc.udp://localhost:9952")
						osc_reader.recv (100)
						if osc_data == 14:
							#queues['out']['korg_out'].append ( button (msg[1] - 47, 2) )
							my_midi_ports['korg_out'].write_midi_event (0, (176, buttonn (cc - 47, 2), 127))
						else:
							#queues['out']['korg_out'].append ( button (msg[1] - 47, 2, False) )
							my_midi_ports['korg_out'].write_midi_event (0, (176, buttonn (cc - 47, 2), 0))
						
				elif mode == 'fx':
					if cc in buttonList:
						b = button2Int (cc)
						
						if b < len(selected[mode]):
							selected[mode][b] = not selected[mode][b]
							my_midi_ports['korg_out'].write_midi_event (0, (176, cc, 127*int(selected[mode][b])))
						
							modhost_client.send ( ('bypass ' + str(b) + ' ' + ('0' if selected[mode][b] else '1')).encode() )
				elif mode == 'synth' or mode == fluidsynth:
					if cc in buttonList:
						synth_mode = 'amsynth' if mode == 'synth' else 'fluidsynth'
						synth_port = synth_mode + '_out'
							
						#time.sleep (0.3)
						b = button2Int (cc)
						if b != None:
							my_midi_ports[synth_port].write_midi_event (0, (192, b))
						
						#queues['out']['korg_out'].append ([176, selected[synth_mode], 0])
						my_midi_ports['korg_out'].write_midi_event (0, (176, selected[synth_mode], 0))
						
						selected[synth_mode] = cc
						#queues['out']['korg_out'].append ([176, selected[synth_mode], 127])
						my_midi_ports['korg_out'].write_midi_event (0, (176, selected[synth_mode], 127))
						
					elif mode == 'synth' and cc == spec_button ('sync_lfo'):
						#						min max values for lfo in amsynth, min max bpm defined in hydrogen
						#print ("bpm: " + str(detect_bpm()) )
						#print ("freq: " + str(detect_bpm()/60) )
						freq_v =  math.sqrt (detect_bpm() / 60);
						#print ("sqrt freq: " + str(freq_v))
						lfo_speed = linear_trans ( 0, 127, 0, 7.5, freq_v)
						#lfo_speed = math.log (detect_bpm() / 60, 2)
						midi_ports['amsynth_out'].write_midi_event ([176, 3, lfo_speed])
				elif mode == 'drum':
					if cc in buttonList:
						b = button2Int (cc)
						selected[mode][b] = not selected[mode][b]
						my_midi_ports['korg_out'].write_midi_event (0, (176, cc, 127*int(selected[mode][b])))

def save():
	#print ('debug: saving')
	if os.path.exists (save_dir):
		i = 0
		saved = False
		while not saved:
			if not os.path.exists (save_dir + str(i) + "/"):
				os.makedirs (save_dir + str(i) + "/")
				os.chmod (save_dir + str(i) + "/", 0o777)
				for k in range(8):
					liblo.send (osc_writer, "/sl/" + str(k) + "/save_loop", save_dir + str(i) + "/" + str(k) + ".wav", "wav", "little", "osc.udp://localhost:9951", "osc.udp://localhost:9952" )
					time.sleep(0.01)
				
				# detect, save bpm
				with open (save_dir + str(i) + "/bpm.txt", 'w') as f:
					f.write ( str ( detect_bpm() ) )
				
				saved = True
			
			i += 1
	else:
		print (save_dir + " not found")

def detect_bpm():
	liblo.send (osc_writer, "/get", "tempo", "osc.udp://localhost:9952", "osc.udp://localhost:9952")
	osc_reader.recv (100)
	return osc_data

def upateLeds_jack (changes, offset):
	for cc, state in changes:
		if display_state[cc] != state:
			my_midi_ports['korg_out'].write_midi_event (0, (176, cc, 0 if state == False else 127))

def updateLeds (pmode, cmode): # prev, curr
	global queues
	global selected
	global curr_loop
	
	# update mode leds
	if isinstance (pmode, list):
		for pm in pmode:
			#queues['out']['korg_out'].append ( spec_button (pm, False) )
			my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button (pm), 0))
	else:
		my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button (pmode), 0))

	if isinstance (cmode, list):
		for cm in cmode:
			my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button (cm), 127))
	else:
		my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button (cmode), 127))
	
	# update matrix leds
	
	# shut down active leds
	if pmode == 'loop':
		my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 1), 0))
		my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 3), 0))
	elif pmode == 'drum' or pmode == 'fx':
		for i in range(len(selected[pmode])):
			if selected[pmode][i]:
				my_midi_ports['korg_out'].write_midi_event (0, (176, int2button(i), 0))
	elif pmode == fluidsynth:
		#queues['out']['korg_out'].append ([176, selected['fluidsynth'], 0])
		my_midi_ports['korg_out'].write_midi_event (0, (176, selected['fluidsynth'], 0))
	elif pmode == 'synth':
		#queues['out']['korg_out'].append ([176, selected['amsynth'], 0])
		my_midi_ports['korg_out'].write_midi_event (0, (176, selected['amsynth'], 0))
	else:
	#	queues['out']['korg_out'].append ([176, selected[pmode], 0])
		my_midi_ports['korg_out'].write_midi_event (0, (176, selected[pmode], 0))
	
	# light up nes ones
	if cmode == 'loop':
		my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 1), 127))
		my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 3), 127))
		
	elif cmode == 'drum' or cmode == 'fx':
		for i in range(len(selected[cmode])):
			if selected[cmode][i]:
				my_midi_ports['korg_out'].write_midi_event (0, (176, int2button(i), 127))
	elif cmode == fluidsynth:
		#queues['out']['korg_out'].append ([176, selected['fluidsynth'], 127])
		my_midi_ports['korg_out'].write_midi_event (0, (176, selected['fluidsynth'], 127))
	elif cmode == 'synth':
		#queues['out']['korg_out'].append ([176, selected['amsynth'], 127])
		my_midi_ports['korg_out'].write_midi_event (0, (176, selected['amsynth'], 127))
	else:
		my_midi_ports['korg_out'].write_midi_event (0, (176, selected[cmode], 127))
		

def load():
	global curr_loaded
	global loop_state
	global mode
	
	#queues['out']['korg_out'].append ( spec_button ('save_blink') )
	midi_ports['korg_out'].write_midi_event ( spec_button ('save_blink') )

	if os.path.exists (save_dir + str(curr_loaded) + "/"):
		for k in range(8): # load
			liblo.send (osc_writer, "/sl/" + str(k) + "/load_loop", save_dir + str(curr_loaded) + "/" + str(k) + ".wav", "osc.udp://localhost:9951", "osc.udp://localhost:9952" )
			time.sleep(0.01)
			liblo.send (osc_writer, "/sl/" + str(k) + "/get", "state", "osc.udp://localhost:9952", "osc.udp://localhost:9952")
			osc_reader.recv(100)
			loop_state.append (osc_data)
		
		if os.path.exists (save_dir + str(curr_loaded) + "/bpm.txt"):
			with open (save_dir + str(curr_loaded) + "/bpm.txt", 'r') as bpmfile:
				bpm_sig = [176, 16, round ( linear_trans (0, 127, 40, 200, float ( bpmfile.readline() ) ) ) ]
				#queues['out']['hydrogen_out'].append ( bpm_sig )
				midi_ports['hydrogen'].write_midi_event ( bpm_sig )
		
		if os.path.exists (save_dir + str(curr_loaded) + "/beat.txt"):
			with open (save_dir + str(curr_loaded) + "/beat.txt", 'r') as beatfile:
				if mode != 'drum':
					midi_ports['hydrogen'].write_midi_event ( spec_button ('drum') ) # put hydrogen into drum mode
				midi_ports['hydrogen'].write_midi_event ( [176, int( beatfile.readline() ), 127] ) 
				midi_ports['hydrogen'].write_midi_event ( spec_button (mode) )
		
		for i in range(8): # play
			if loop_state[i] == 10:
				liblo.send (osc_writer, "/sl/" + str(i) + "/hit", "mute_off")
			if loop_state[i] == 14:
				liblo.send (osc_writer, "/sl/" + str(i) + "/hit", "pause")
			
			midi_ports['korg_out'].write_midi_event ( button (i + 1, 2, False) )
				
				
		loop_state = []
	
	time.sleep (1)
	midi_ports['korg_out'].write_midi_event ( spec_button ('save_blink', False) )
	
def detect_bpm():
	if os.path.exists ('/tmp/bpm-log.txt'):
		with open ('/tmp/bpm-log.txt', 'r') as bpmfile:
			return int( bpmfile.readline() )
		#	queues['out']['amsynth_out'].append ( [176, 10, int( bpmfile.readline() ) ] )
	
	return 120
	
def latest_session():
	if os.path.exists (save_dir):
		i = 0
		while os.path.exists (save_dir + str(i) + "/"):
			i += 1
		
		return i - 1
	
	return -1
	
def get_osc_data (path, args, types, src):
	global osc_data
	osc_data = args[2]

def linear_trans (x1, x2, a, b, c):
	return x1 + ( (x2 - x1) / (b - a) ) * (c - a)

	

########################################################################
## main
########################################################################
	

jackclient.activate()
setup_connections()
started = True

try:
	osc_writer = liblo.Address (osc_write_port)
	osc_reader = liblo.Server (osc_read_port)
	osc_reader.add_method (None, None, get_osc_data)
except:
  print (sys.exc_info()[0])


try:
	pass
	#_thread.start_new_thread ( read_korg, () )
	_thread.start_new_thread ( read_pedal, () )
	#_thread.start_new_thread ( write, () )
except:
	print ("Error: unable to start thread: " + str(sys.exc_info()[0]))

while True:
	time.sleep (0.01)
