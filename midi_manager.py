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
import collections

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

loops = 8
fx_loops = 1

if len(sys.argv) > 1:
	try:
		fx_loops = int(sys.argv[1])
	except ValueError:
		print ("Parameter have to be an int, using default value: " + str(fx_loops))

########################################################################
## prepare
########################################################################

# footswitch
if gpio:
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

started = False
jackclient = jack.Client ('MidiManager')


def send_modhost (client, msg, readAnswer=True):
	client.send ( msg.encode() )
	
	if (readAnswer):
		return client.recv (20).decode ('utf-8')

modhost_client_fx = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
modhost_client_fx.connect ( ("localhost", 5555) )
waste = send_modhost (modhost_client_fx, 'load mod-host/mod-host-config.txt', False)

modhost_client_loop = [socket.socket(socket.AF_INET, socket.SOCK_STREAM) for i in range(fx_loops)]
for i in range(len(modhost_client_loop)):
	time.sleep (2)
	mh = modhost_client_loop[i]
	mh.connect ( ("localhost", 5555 + i + 1) )
	waste = send_modhost (mh, 'load mod-host/mod-host-config.txt', False)

def read_modhost_params():
	params = {}
	
	with open ('mod-host/mod-host-config.txt') as f:
		content = f.readlines()
		for line in content:
			if 'midi_map' in line:
				line_split = line.split (' ')
				instance = line_split[1]
				sym = line_split[2]
				
				if instance in params:
					params[instance].append (sym)
				else:
					params[instance] = [sym]
		
	return params
	
modhost_params = read_modhost_params()
n_effects = len(modhost_params)

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
midi_queue = {}
ports_ready = False

def setup_connections():
	global midi_ports
	global audio_ports
	global my_midi_ports
	global midi_queue
	global ports_ready
	
	all_audio_ports = []
	port_desc = [('capture_1', ['system:capture_1']),
				 ('capture_2', ['system:capture_2']),
				 ('playback_1', ['system:playback_1']),
				 ('playback_2', ['system:playback_2']),
				 ('hydrogen_out', ['Hydrogen', 'out_R']),
				 ('aubio_in', ['aubio', 'in']),
				 ('amsynth_out', ['amsynth', 'R out']),
				 ('fluidsynth_out', ['fluidsynth', 'right']),
				 ('sl_out_all', ['sooperlooper', 'common_out_1']),
				 ('sl_in_all', ['sooperlooper', 'common_in_1'])] + \
				 [('sl_out_' + str(i), ['sooperlooper', 'loop' + str(i) + '_out_1']) for i in range(loops)] + \
				 [('sl_in_' + str(i), ['sooperlooper', 'loop' + str(i) + '_in_1']) for i in range(loops)] + \
				 [('fx_in_' + str(i), ['effect_' + str(i) + ':in']) for i in range(n_effects)] + \
				 [('fx_out_' + str(i), ['effect_' + str(i) + ':out']) for i in range(n_effects)] + \
				 [('loop_fx_' + str(k) + '_in_' + str(i), ['effect_' + str(i) + '-0' + str(k + 1) + ':in']) for i in range(n_effects) for k in range(fx_loops)] +\
				 [('loop_fx_' + str(k) + '_out_' + str(i), ['effect_' + str(i) + '-0' + str(k + 1) + ':out']) for i in range(n_effects) for k in range(fx_loops)]
				 
	
	# wait until all ports are present			 
	for (k, v) in port_desc:
		tryagain = True
		while tryagain:
			print ("get port " + k)
			all_audio_ports = [i for i in jackclient.get_ports() if i.__class__ == jack.Port]
			p = getPort (all_audio_ports, v)
			
			if p is None:
				time.sleep (0.5)
				
			else:
				tryagain = False
	
	audio_ports = {k: getPort (all_audio_ports, v) for (k, v) in port_desc}
	# connecting ports

	connect_ports (audio_ports, 'capture_1', 'aubio_in')
	connect_ports (audio_ports, 'capture_2', 'aubio_in')

	for i in ['hydrogen_out', 'amsynth_out', 'fluidsynth_out']:
		connect_ports (audio_ports, i, 'playback_1')
		connect_ports (audio_ports, i, 'playback_2')

	for i in ['amsynth_out', 'fluidsynth_out']:
		for k in range(loops):
			connect_ports (audio_ports, i, 'sl_in_' + str(k))
		#connect_ports (audio_ports, i, 'sl_in_all')

	#connect_ports (audio_ports, 'sl_out_all', 'loop_fx_in_0')
	
	# fx loop
	for i in range(fx_loops):
		#connect_ports (audio_ports, 'sl_out_0', 'loop_fx_' + str(i) + '_in_0')
		connect_ports (audio_ports, 'sl_out_' + str(i), 'loop_fx_' + str(i) + '_in_0')
		connect_ports (audio_ports, 'loop_fx_' + str(i) + '_out_6', 'playback_1')
		connect_ports (audio_ports, 'loop_fx_' + str(i) + '_out_6', 'playback_2')
	
	# normal loop
	for i in range(fx_loops, loops):
		connect_ports (audio_ports, 'sl_out_' + str(i), 'playback_1')
		connect_ports (audio_ports, 'sl_out_' + str(i), 'playback_2')

	connect_ports (audio_ports, 'capture_1', 'fx_in_0')
	connect_ports (audio_ports, 'capture_2', 'fx_in_0')

	for i in range(n_effects - 1):
		connect_ports (audio_ports, 'fx_out_' + str(i), 'fx_in_' + str(i+1))
		
		for k in range(fx_loops):
			connect_ports (audio_ports, 'loop_fx_' + str(k) + '_out_' + str(i), 'loop_fx_' + str(k) + '_in_' + str(i+1))
	
	# live fx
	connect_ports (audio_ports, 'fx_out_6', 'playback_1')
	connect_ports (audio_ports, 'fx_out_6', 'playback_2')
	#connect_ports (audio_ports, 'fx_out_6', 'sl_in_all')
	### record clean signal
	#connect_ports (audio_ports, 'capture_1', 'sl_in_all')
	#connect_ports (audio_ports, 'capture_2', 'sl_in_all')
	
	# fx loop records clean signal
	for i in range (fx_loops):
		connect_ports (audio_ports, 'capture_1', 'sl_in_' + str(i))
		connect_ports (audio_ports, 'capture_2', 'sl_in_' + str(i))
	
	# normal loops record processed signal
	for i in range(fx_loops, loops):
		connect_ports (audio_ports, 'fx_out_6', 'sl_in_' + str(i))
	
	#connect_ports (audio_ports, 'capture_2', 'sl_in_all')
		

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
				 ('mod-host-fx', ['mod-host:midi_in'])] + \
				 [('mod-host-loop_' + str(i), ['mod-host-0' + str(i + 1) + ':midi_in']) for i in range(fx_loops)]
				 
	midi_ports = {k: getPort (all_midi_ports, v) for (k, v) in port_desc}

	connect_ports (midi_ports, 'korg_in', 'sl')
	disconnect_ports (midi_ports, 'korg_in', 'mod-host-fx')
	for i in range(fx_loops):
		disconnect_ports (midi_ports, 'korg_in', 'mod-host-loop_' + str(i))

	# own midi ports
	my_midi_ports = {'korg_in': jackclient.midi_inports.register ('input'),
					 'korg_out': jackclient.midi_outports.register ('output'),
					 'sl_out': jackclient.midi_outports.register ('sl_out'),
					 'fluidsynth_out': jackclient.midi_outports.register ('fluidsynth_out'),
					 'amsynth_out': jackclient.midi_outports.register ('amsynth_out')};
	midi_queue = {k: [] for (k, v) in my_midi_ports.items()}
	
	#pdb.set_trace()
	jackclient.connect (my_midi_ports['korg_out'].name, midi_ports['korg_out'].name)
	jackclient.connect (midi_ports['korg_in'], my_midi_ports['korg_in'].name)
	jackclient.connect (my_midi_ports['sl_out'].name, midi_ports['sl'].name)
	jackclient.connect (my_midi_ports['fluidsynth_out'].name, midi_ports['fluidsynth'].name)
	jackclient.connect (my_midi_ports['amsynth_out'].name, midi_ports['amsynth'].name)
	
	ports_ready = True

slider_lst_state = [-1]*loops
rot_lst_state = [-1]*loops

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
loop_fx = ['loop', 'fx']  # light loop and fx up to indicate we have selected loop fx

########################################################################
## variables
########################################################################

osc_writer = None
vosc_reader = None
osc_data = None

curr_loaded = -1
loop_state = []

msg = {'record': [144,0,1], 'sync': [144,1,1], 'desync': [144,2,1], 'playsync': [144,3,1], 'deplaysync': [144,4,1], 'incr_bpm': [144,6,1]}

curr_loop = 1
sync_switch = True
pedal_pressed = False

mode = 'loop' # loop, fx, drum synth

selected = {'fx': [True] + [False]*5 + [True], 'drum': [True] + [False]*23, 'amsynth': button (1, 1), 'fluidsynth': button(1,1)}
for i in range(fx_loops):
	selected['loop_fx_' + str(i)] = [True] + [False]*5 + [True]

poweroff_counter = 0

led_buttons = list(range(32+1, 39)) + list(range(32+1, 39)) + list(range(41+1,46))+ list(range(48+1, 55)) + list (range(64+1, 71))
display_state = {i: (False, led_buttons[i]) for i in range (len (led_buttons)) };

########################################################################
## utils
########################################################################

def connect_loop (disconnect=False):
	if curr_loop <= fx_loops: # curr_loop is fx loop
		connect_ports (audio_ports, 'capture_1', 'sl_in_' + str(curr_loop - 1), disconnect) 
		connect_ports (audio_ports, 'capture_2', 'sl_in_' + str(curr_loop - 1), disconnect)
	else: # curr_loop is normal loop
		connect_ports (audio_ports, 'fx_out_6', 'sl_in_' + str(curr_loop - 1), disconnect)

def disconnect_loop():
	connect_loop (True)

def disconnect_midi_loops():
	disconnect_ports (midi_ports, 'korg_in', 'mod-host-loop_' + str(curr_loop - 1))
	#for i in range(fx_loops):
	#	disconnect_ports (midi_ports, 'korg_in', 'mod-host-loop_' + str(i))

########################################################################
## process
########################################################################

# reads and writes all midi events
#@jackclient.set_process_callback
#def process(frames):
#	global my_midi_ports
#	global pedal_pressed
#	global copy_fx_config
#	global midi_queue
#	
#	if ports_ready:
#		
#		my_midi_ports['sl_out'].clear_buffer()
#		
#		if pedal_pressed:
#			if not sync_switch:
#				#my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button('record'), 127) )
#				midi_event ('korg_out', spec_button('record'), 127)
#				
#				# copy fx config to loop_fx
#				if mode != 'synth' and mode != fluidsynth and curr_loop <= fx_loops:
#					copy_fx_config = True
#			else:
#				#my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button('record'), 0))
#				midi_event ('korg_out', spec_button('record'), 0)
#			
#			my_midi_ports['sl_out'].write_midi_event (0, msg['record'])
#			pedal_pressed = False
#			
#		for offset, data in my_midi_ports['korg_in'].incoming_midi_events():
#			if len(data) == 3:
#				b1, b2, b3 = struct.unpack('3B', data)
#				process_korg_in (b2, b3)
#				print('input: ' + str(b2) + ', ' + str(b3))
# reads and writes all midi events
@jackclient.set_process_callback
def process(frames):
	pass

def midi_event (port, cc, value,  channel=176, offset=0):
	global midi_queue
	midi_queue[port].append ([offset, channel, cc, value])
		
def read_pedal():
	global sync_switch
	global pedal_pressed
	
	last_time = 0
	while True:
		print('wait for input')
		if gpio:
			GPIO.wait_for_edge(3, GPIO.FALLING)
		else:
			input()
		
		if time.time() - last_time > 0.4:
			print ("Record")
			pedal_pressed = True
			
			sync_switch = not sync_switch
			last_time = time.time()

def process_korg_in (cc, value):
	global curr_loop
	global midi_queue
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
				call (["poweroff"])
				
		else :
			poweroff_counter = 0
			
			pmode = mode
				
			# select mode
			if cc == spec_button ('loop'):
				if mode != 'loop':
					updateLeds (mode, 'loop')
					
					mode = 'loop'
					
					connect_ports (midi_ports, 'korg_in',  'sl')
					
					if pmode == 'synth':
						disconnect_ports (midi_ports, 'korg_in', 'amsynth')
						connect_loop()
					elif pmode == fluidsynth:
						disconnect_ports (midi_ports, 'korg_in', 'fluidsynth')
						connect_loop()
					elif pmode == 'fx':
						disconnect_ports (midi_ports, 'korg_in', 'mod-host-fx')
					elif pmode == loop_fx:
						disconnect_ports (midi_ports, 'korg_in', 'mod-host-loop_' + str(curr_loop - 1))
					elif pmode == 'drum':
						disconnect_ports (midi_ports, 'korg_in', 'hydrogen')
					
			elif cc == spec_button ('fx'):
				if mode != 'fx':
					updateLeds (mode, 'fx')
					mode = 'fx'
					
					if pmode == 'synth':
						disconnect_ports (midi_ports, 'aubio', 'amsynth')
						disconnect_ports (midi_ports, 'korg_in', 'amsynth')
						
						connect_ports (audio_ports, 'fx_out_6', 'playback_1')
						connect_ports (audio_ports, 'fx_out_6', 'playback_2')
						
						connect_loop()
						
					elif pmode == fluidsynth:
						disconnect_ports (midi_ports, 'aubio', 'fluidsynth')
						disconnect_ports (midi_ports, 'korg_in', 'fluidsynth')
					elif pmode == 'loop':
						disconnect_ports (midi_ports, 'korg_in', 'sl')
					elif pmode == 'drum':
						disconnect_ports (midi_ports, 'korg_in', 'hydrogen')
					elif pmode == loop_fx:
						disconnect_midi_loops()
						
					
					connect_ports (midi_ports, 'korg_in', 'mod-host-fx')
					
					
			elif cc == spec_button ('drum'):
				if mode != 'drum':
					updateLeds (mode, 'drum')
					mode = 'drum'
					
					if pmode == 'loop':
						disconnect_ports (midi_ports, 'korg_in', 'sl')
					elif pmode == 'synth':
						disconnect_ports (midi_ports, 'korg_in', 'amsynth')
						disconnect_ports (midi_ports, 'aubio', 'amsynth')
					elif pmode == fluidsynth:
						disconnect_ports (midi_ports, 'korg_in', 'fluidsynth')
						disconnect_ports (midi_ports, 'aubio', 'fluidsynth')
					elif pmode == 'fx':
						disconnect_ports (midi_ports, 'korg_in', 'mod-host-fx')
					elif pmode == loop_fx:
						disconnect_midi_loops()
					
					connect_ports (midi_ports, 'korg_in', 'hydrogen')
					
					if pmode == 'synth' or pmode == fluidsynth:
						connect_ports (audio_ports, 'fx_out_6', 'playback_1')
						connect_ports (audio_ports, 'fx_out_6', 'playback_2')
						connect_loop()

			elif cc == spec_button ('synth'):
				
				if pmode == 'loop':
					disconnect_ports (midi_ports, 'korg_in', 'sl')
				elif pmode == 'fx':
					disconnect_ports (midi_ports, 'korg_in', 'mod-host-fx')
				elif pmode == loop_fx:
					disconnect_midi_loops()
				elif pmode == 'drum':
					disconnect_ports (midi_ports, 'korg_in', 'hydrogen')
				
				if pmode != 'synth' and pmode != fluidsynth:
					disconnect_ports (audio_ports, 'fx_out_6', 'playback_1')
					disconnect_ports (audio_ports, 'fx_out_6', 'playback_2')
					disconnect_loop()
				
				if mode != 'synth':  # somewhat -> amsynth
					updateLeds (mode, 'synth')
					mode = 'synth'
					
					if pmode == fluidsynth:
						midi_event ('fluidsynth_out', 123, 0) # kill every noteon event from fluidsynth
						#my_midi_ports['fluidsynth_out'].write_midi_event (9, [176, 123, 0])
						midi_event ('fluidsynth_out', 123, 0, 176, 9)
						
						disconnect_ports (midi_ports, 'aubio', 'fluidsynth')
						disconnect_ports (midi_ports, 'korg_in', 'fluidsynth')
						
					connect_ports (midi_ports, 'aubio', 'amsynth')
					connect_ports (midi_ports, 'korg_in', 'amsynth')
					
					
				else: # amsynth -> fluidsynth
					updateLeds (mode, fluidsynth)
					mode = fluidsynth
					
					midi_event ('amsynth_out', 123, 0) # kill every noteon event from amsynth
					
					connect_ports (midi_ports, 'aubio', 'fluidsynth')
					disconnect_ports (midi_ports, 'aubio', 'amsynth')
					connect_ports (midi_ports, 'korg_in', 'fluidsynth')
					disconnect_ports (midi_ports, 'korg_in', 'amsynth')
			
			### no mode button, one of the matrix button
			else:
				if mode == 'loop':
					if cc >= 32 and cc <= 39: # select loop (top row)
						if cc - 31 != curr_loop:
							
							midi_event ('korg_out', button (curr_loop, 1), 0)
							midi_event ('korg_out', button (curr_loop, 3), 0)
							
							curr_loop = cc - 31
							
							midi_event ('korg_out', button (curr_loop, 1), 127)
							midi_event ('korg_out', button (curr_loop, 3), 127)
							
					#if cc >= button (3, 1) and cc <= button (3, 8): # fx loop menu (bottom row)
					if cc in [button (i, 3) for i in range(1, fx_loops + 1)]:
						disconnect_ports (midi_ports, 'korg_in', 'sl')
						connect_ports (midi_ports, 'korg_in', 'mod-host-loop_' + str(curr_loop - 1))
						updateLeds (mode, loop_fx)
						mode = loop_fx
						
				elif mode == 'fx' or mode == loop_fx:
					m = 'fx'
					mh = modhost_client_fx
					if mode == loop_fx:
						m = 'loop_fx_' + str(curr_loop - 1)
						mh = modhost_client_loop[curr_loop - 1]
					
					if cc in buttonList:
						b = button2Int (cc)
						
						if b < len(selected[m]):
							selected[m][b] = not selected[m][b]
							midi_event ('korg_out', cc, 127*int(selected[m][b]))
						
							waste = send_modhost (mh, 'bypass ' + str(b) + ' ' + ('0' if selected[m][b] else '1'))
							
				elif mode == 'synth' or mode == fluidsynth:
					if cc in buttonList:
						synth_mode = 'amsynth' if mode == 'synth' else 'fluidsynth'
						synth_port = synth_mode + '_out'
							
						b = button2Int (cc)
						if b != None:
							#my_midi_ports[synth_port].write_midi_event (0, [192, b])
							midi_event (synth_port, b[0], b[1], 192)
						
						midi_event ('korg_out', selected[synth_mode], 0)
						selected[synth_mode] = cc
						midi_event ('korg_out', selected[synth_mode], 127)
						
					elif mode == 'synth' and cc == spec_button ('sync_lfo'):
						freq_v =  math.sqrt (detect_bpm() / 60);
						lfo_speed = linear_trans ( 0, 127, 0, 7.5, freq_v)
						#midi_ports['amsynth_out'].write_midi_event ([176, 3, lfo_speed])
						midi_event ('amsynth_out', 3, lfo_speed)
				elif mode == 'drum':
					if cc in buttonList:
						b = button2Int (cc)
						selected[mode][b] = not selected[mode][b]
						midi_event ('korg_out', cc, 127*int(selected[mode][b]))

def processNonRealtime():
	global my_midi_ports
	global pedal_pressed
	

def updateLeds (pmode, cmode): # prev, curr
	global queues
	global selected
	global curr_loop
	
	# update mode leds
	if isinstance (pmode, list):
		for pm in pmode:
			midi_event ('korg_out', spec_button(pm), 0)
	else:
		midi_event ('korg_out', spec_button(pmode), 0)

	if isinstance (cmode, list):
		for cm in cmode:
			midi_event ('korg_out', spec_button(cm), 127)
	else:
		midi_event ('korg_out', spec_button(cmode), 127)
	
	# update matrix leds
	
	# shut down active leds
	if pmode == 'loop':
		
		midi_event ('korg_out', button(curr_loop, 1), 0)
		midi_event ('korg_out', button(curr_loop, 3), 0)
	elif pmode == 'drum' or pmode == 'fx' or pmode == loop_fx:
		pm = 'loop_fx_' + str(curr_loop - 1) if pmode == loop_fx else pmode
		for i in range(len(selected[pm])):
			if selected[pm][i]:
				midi_event ('korg_out', int2button(i), 0)
	elif pmode == fluidsynth:
		midi_event ('korg_out', selected['fluidsynth'], 0)
	elif pmode == 'synth':
		midi_event ('korg_out', selected['amsynth'], 0)
	else:
		midi_event ('korg_out', selected[pmode], 0)
	
	# light up new ones
	if cmode == 'loop':
		midi_event ('korg_out', button(curr_loop, 1), 127)
		midi_event ('korg_out', button(curr_loop, 3), 127)
		
	elif cmode == 'drum' or cmode == 'fx' or cmode == loop_fx:
		cm = 'loop_fx_' + str(curr_loop - 1) if cmode == loop_fx else cmode
		
		for i in range(len(selected[cm])):
			if selected[cm][i]:
				midi_event ('korg_out', int2button(i), 127)
				
	elif cmode == fluidsynth:
		midi_event ('korg_out', selected['fluidsynth'], 127)
	elif cmode == 'synth':
		midi_event ('korg_out', selected['amsynth'], 127)
	else:
		midi_event ('korg_out', selected[cmode], 127)
			
	
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
	_thread.start_new_thread ( read_pedal, () )
except:
	print ("Error: unable to start thread: " + str(sys.exc_info()[0]))

#pdb.set_trace()
while not ports_ready:
	time.sleep (0.01)
	
# initial led light up
print (midi_queue)	
midi_event ('korg_out', button (curr_loop, 1), 127)
midi_event ('korg_out', button (curr_loop, 3), 127)
midi_event ('korg_out', spec_button ('loop'), 127)
midi_event ('sl_out', button (1, 1), 1)

time.sleep (1)
		
last_midi = (-1, -1)
while True:
	if pedal_pressed:
		
		if not sync_switch:
			midi_event ('korg_out', spec_button('record'), 127)
			
			# copy fx config to loop_fx
			if mode != 'synth' and mode != fluidsynth and curr_loop <= fx_loops:
				# bypass
				for i in range(len(selected['fx'])):
					waste = send_modhost (modhost_client_loop[curr_loop - 1], 'bypass ' + str(i) + ' ' + str(int(not selected['fx'][i])))
					
					print(('bypass ' + str(i) + ' ' + str(int(not selected['fx'][i])) ))
					print(waste)
				
				selected['loop_fx_' + str(curr_loop - 1)] = selected['fx'].copy()
					
				for inst in modhost_params:
					for sym in modhost_params[inst]:
						answer = send_modhost (modhost_client_fx, 'param_get ' + inst + ' ' + sym).split (' ')[2]
						#print (('param_get ' + inst + ' ' + sym))
						print ('"' + answer + '"')
						waste = send_modhost (modhost_client_loop[curr_loop - 1], 'param_set ' + inst + ' ' + sym + ' ' + answer)
		else:
			midi_event ('korg_out', spec_button('record'), 0)
		
		midi_event ('sl_out', msg['record'][0], msg['record'][1])
		
		print ('Record_sooperlooper')
		pedal_pressed = False
	
	for offset, data in my_midi_ports['korg_in'].incoming_midi_events():
		if len(data) == 3:
			b1, b2, b3 = struct.unpack('3B', data)
			if last_midi != (b2, b3):
				process_korg_in (b2, b3)
				#print('input: ' + str(b2) + ', ' + str(b3))
				print ('last  midi: ' + str(last_midi))
				print('input: ' + str((b2, b3)))
				last_midi = (b2, b3)
	
	for q in midi_queue:
		if (len(midi_queue[q]) > 0):
			print (q + ': ' + str(midi_queue[q]))
			my_midi_ports[q].clear_buffer()
			
			for i in midi_queue[q]:
				my_midi_ports[q].write_midi_event (i[0], [i[1], i[2], i[3]])
		
		midi_queue[q] = []
			
	
	time.sleep (0.01)
