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
import re
import argparse

import pprint
#import logging
pp = pprint.PrettyPrinter(indent=4)

gpio = False
try:
	import RPi.GPIO as GPIO
	gpio = True
except ModuleNotFoundError:
	print ('no gpio available')

import jack

from port_desc import getPortDesc
from port_desc import getPortDescMidi


#logging.basicConfig(filename='/tmp/llogs/midi_manager.py', level=logging.INFO)



########################################################################
## config
########################################################################

osc_write_port = 9951
osc_read_port = 9952
save_dir = "/mnt/data/saved_loops/"

parser = argparse.ArgumentParser()
parser.add_argument ('-l', '--loops', help='number of loops',  type=int)
parser.add_argument ('-fx', '--fxloops', help='number of fx loops', type=int)
parser.add_argument ('-m', '--midiloops', help='number of midi loops', type=int)

args = vars(parser.parse_args())

loops = args['loops'] or 8
fx_loops = args['fxloops'] or 2
midi_loops = args['midiloops'] or 2

########################################################################
## prepare
########################################################################

# footswitch
if gpio:
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

started = False
jackclient = jack.Client ('MidiManager')

record_mode = 'wav'

def send_modhost (client, msg, readAnswer=True):
	client.send ( msg.encode() )
	
	if (readAnswer):
		return client.recv (20).decode ('utf-8')

modhost_client_fx = None
#modhost_client_loop = None

# hold couples of values for each active plugin in modhost:
# [0] : modhost command with placeholder for plugin id
# [1] : plugin id
active_modhost_midi = []

def setup_modhost (n_effects, fx_loops):
	global modhost_client_fx
	
	config_template = []
	with open ('mod-host/mod-host-config-template.channel.txt', 'r') as config_file:
		for line in config_file:
			config_template.append (line.replace ('\n', ''))
	
	with open ('/tmp/mod-host-config.txt', 'w') as fx_file:
		for i in range (fx_loops + 1): # fx_loops + live fx
			for line in config_template:
				l = re.sub ( r'\{(\d)\}', lambda x: '{}'.format ( int ( x.groups()[0] ) + (i * n_effects) ), line )
				l = re.sub (r'\{c\}', str(i), l) # replace channel
				fx_file.write (l + '\n')
					
	modhost_client_fx = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	modhost_client_fx.connect ( ('localhost', 5555) )
	waste = send_modhost (modhost_client_fx, 'load /tmp/mod-host-config.txt', False)
	
	while ([i.name for i in jackclient.get_ports() if i.__class__ == jack.Port and ('effect_' + str (n_effects - 1)) in i.name]) == 0:
		time.sleep (0.1)
		
		while len([p.name for p in jackclient.get_ports() if p.__class__ == jack.Port and ('effect_' + str (n_effects - 1) + '-0' + str (i + 1) ) in p.name]) == 0:
			time.sleep (0.1)

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
print ('n_effects: ' + str(n_effects))

def getPort (ports, keywords):
	for i in ports:
		if sum([1 for k in keywords if k in i.name]) == len(keywords):
			return i
	
	return None

def connect_ports_direct (pin, pout, disconnect=False):
	try:
		if not disconnect:
			jackclient.connect (pin.name, pout.name)
		else:
			jackclient.disconnect (pin, pout)
	except jack.JackError as e:
		print (e)
	else:
		if pin is None:
			print ('port ' + str(pin) + ' is  None')
		if pout is None:
			print ('port ' + str(pout) + ' is  None')
			
def connect_ports (ports, pin, pout, disconnect=False,):
	print ( ('dis' if disconnect else '') + 'connect ' + str(pin) + ' -> ' + str(pout))
	
	if ports[pin] is None:
		print ('port ' + pin + ' is  None')
		return
	if ports[pout] is None:
		print ('port ' + pout + ' is  None')
		return
		
	connect_ports_direct (ports[pin], ports[pout], disconnect=disconnect)
		

def disconnect_ports (ports, pin, pout):
	connect_ports (ports, pin, pout, disconnect=True)

### audio ports
midi_ports = {}
audio_ports = {}
my_midi_ports = {}
ports_ready = False

def setup_connections():
	global midi_ports
	global audio_ports
	global my_midi_ports
	global ports_ready
	
	all_audio_ports = []
	port_desc = getPortDesc (loops, fx_loops, n_effects, midi_loops)

	setup_modhost (n_effects, fx_loops)
	
	# wait until all ports are present
	audio_ports = {}

	while len(port_desc) > 0:
		all_audio_ports = [i for i in jackclient.get_ports() if i.__class__ == jack.Port]
		for (k, v) in port_desc:
			print ('look for port ' + k + ':' + str(v))
			p = getPort (all_audio_ports, v)

			if p is not None:
				#print ('found port ' + k)
				audio_ports[k] = p
				
				for pd in port_desc:
					print (pd)
				
				port_desc[:] = [(x, y) for (x, y) in port_desc if x is not k]
		
		if len(port_desc) > 0:
			time.sleep (0.1)
	# connecting ports

	connect_ports (audio_ports, 'capture_1', 'aubio_in')
	connect_ports (audio_ports, 'capture_2', 'aubio_in')

	#for i in ['hydrogen_out', 'amsynth_out', 'fluidsynth_out']:
	for i in ['amsynth_out', 'fluidsynth_out', 'drum']:
		connect_ports (audio_ports, i, 'playback_1')
		connect_ports (audio_ports, i, 'playback_2')

	for i in ['amsynth_out', 'fluidsynth_out']:
		connect_ports (audio_ports, i, 'sl_in')
		
	#for i in range(midi_loops):
	#	connect_ports (audio_ports, 'fluidsynth_loop_' + str(i), 'playback_1')
	#	connect_ports (audio_ports, 'fluidsynth_loop_' + str(i), 'playback_2')
	
	# fx loop
	for i in range(fx_loops):
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
	#for i in range (fx_loops):
	connect_ports (audio_ports, 'capture_1', 'sl_in')
	connect_ports (audio_ports, 'capture_2', 'sl_in')
	
	# normal loops record processed signal
	#for i in range(fx_loops, loops):
	connect_ports (audio_ports, 'fx_out_6', 'sl_in')
	
	#connect_ports (audio_ports, 'capture_2', 'sl_in_all')
	
	for i in range(midi_loops):
		connect_ports (audio_ports, 'fluidsynth_loop_' + str(i), 'playback_1')
		connect_ports (audio_ports, 'fluidsynth_loop_' + str(i), 'playback_2')
					

	### foreign midi ports
	all_midi_ports = [i for i in jackclient.get_ports() if i.__class__ == jack.MidiPort]
	port_desc = getPortDescMidi (fx_loops, midi_loops)
				 
	midi_ports = {k: getPort (all_midi_ports, v) for (k, v) in port_desc}

	connect_ports (midi_ports, 'korg_in', 'sl')
	connect_ports (midi_ports, 'korg_in', 'sl_capture')
	disconnect_ports (midi_ports, 'korg_in', 'mod-host-fx')
	#for i in range(fx_loops):
	#	disconnect_ports (midi_ports, 'korg_in', 'mod-host-loop_' + str(i))

	# drum
	connect_ports (midi_ports, 'midimap_out_cc', 'drum')
	connect_ports (midi_ports, 'midimap_out_channel_fx', 'mod-host-fx')
	
	disconnect_ports (midi_ports, 'korg_in', 'amsynth')
	
	for i in range (fx_loops):
		connect_ports (midi_ports, 'midimap_out_channel_loop_' + str(i), 'mod-host-fx')
	
	# own midi ports
	my_midi_ports = {'korg_in': jackclient.midi_inports.register ('input'),
					 'korg_out': jackclient.midi_outports.register ('output'),
					 'sl_out': jackclient.midi_outports.register ('sl_out'),
					 'drum': jackclient.midi_outports.register ('drum_out'),
					 'fluidsynth_out': jackclient.midi_outports.register ('fluidsynth_out'),
					 'amsynth_out': jackclient.midi_outports.register ('amsynth_out'),
					 'midimap_fx': jackclient.midi_outports.register ('midimap_control_fx')};
	for i in range(fx_loops):
		my_midi_ports['midimap_loop_' + str(i)] = jackclient.midi_outports.register ('midimap_control_loop-' + str(i)) 
		
	#pdb.set_trace()
	jackclient.connect (my_midi_ports['korg_out'].name, midi_ports['korg_out'].name)
	jackclient.connect (midi_ports['korg_in'], my_midi_ports['korg_in'].name)
	jackclient.connect (my_midi_ports['sl_out'].name, midi_ports['sl'].name)
	jackclient.connect (my_midi_ports['fluidsynth_out'].name, midi_ports['fluidsynth'].name)
	jackclient.connect (my_midi_ports['amsynth_out'].name, midi_ports['amsynth'].name)
	jackclient.connect (my_midi_ports['midimap_fx'].name, midi_ports['midimap_control_fx'].name)
	
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
loop_fluidsynth = ['loop', 'synth']  # light loop and synth up to indicate we have selected loop synth

########################################################################
## variables
########################################################################

osc_writer = None
vosc_reader = None
osc_data = None

curr_loaded = -1
loop_state = []

msg = {'record_wav': [176,144,127], 'record_midi': [176,42,127], }

curr_loop = 1
sync_switch = True
pedal_pressed = False

copy_fx_config = False

mode = 'loop' # loop, fx, drum synth

selected = {'fx': [True] + [False]*5 + [True], 'drum': [True] + [False]*23, 'amsynth': button (1, 1), 'fluidsynth': button(1,1), 'wav_2_midi_track': [False]*midi_loops}
for i in range(fx_loops):
	selected['loop_fx_' + str(i)] = [True] + [False]*5 + [True]

fluidsynth_presets = 9
amsynth_presets = 9
for i in range(midi_loops): 
	selected['loop_fluidsynth_' + str(i)] = -1
	selected['loop_amsynth_' + str(i)] = -1

poweroff_counter = 0

led_buttons = list(range(32+1, 39)) + list(range(32+1, 39)) + list(range(41+1,46))+ list(range(48+1, 55)) + list (range(64+1, 71))
display_state = {i: (False, led_buttons[i]) for i in range (len (led_buttons)) };

# processed parallel to jack's @process callback
midi_queue = collections.deque (
	# shut down all leds
	[['korg_out', 0, (176, button (i + 1, k), 0)] for i in range(loops) for k in [1, 2, 3]] +\
	[['korg_out', 0, (176, i, 0)] for i in [58, 59, 46, 60, 61, 62, 43, 44, 42, 41, 45]] +\

	 # light up initial leds
	[['korg_out', 0, (176, button (curr_loop, 1), 127)]] +\
	[['korg_out', 0, (176, button (curr_loop, 3), 127)]] +\
	[['korg_out', 0, (176, spec_button ('loop'), 127)]]
)
# processed in jack's @process callback
# used for record event change program for synthesizer which does not
# work when processed parallel (why?)
rt_midi_queue = connect_queue = collections.deque()
connect_queue = collections.deque()
disconnect_queue = collections.deque()

aubio_connected = None


########################################################################
## utils
########################################################################

def connect_loop (disconnect=False):
	queue = connect_queue if not disconnect else disconnect_queue
	if curr_loop <= fx_loops: # curr_loop is fx loop
		queue.append ([audio_ports, 'capture_1', 'sl_in']) 
		queue.append ([audio_ports, 'capture_2', 'sl_in'])
	else: # curr_loop is normal loop
		queue.append ([audio_ports, 'fx_out_6', 'sl_in'])

def disconnect_loop():
	connect_loop (True)

def disconnect_midi_loops():
	pass
	#disconnect_queue.append ([midi_ports, 'korg_in', 'mod-host-loop_' + str(curr_loop - 1)])
	#for i in range(fx_loops):
	#	disconnect_ports (midi_ports, 'korg_in', 'mod-host-loop_' + str(i))

########################################################################
## process
########################################################################
first_clear = True
# reads and writes all midi events
@jackclient.set_process_callback
def process(frames):
	global my_midi_ports
	global pedal_pressed
	global copy_fx_config
	global rt_midi_queue
	global first_clear
	
	if ports_ready:
		
		my_midi_ports['korg_out'].clear_buffer()
		my_midi_ports['sl_out'].clear_buffer()
		my_midi_ports['fluidsynth_out'].clear_buffer()
		my_midi_ports['amsynth_out'].clear_buffer()
		my_midi_ports['drum'].clear_buffer()
		my_midi_ports['midimap_fx'].clear_buffer()
			
		if pedal_pressed:
			if not sync_switch: #start recording
				#my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button('record'), 127) )
				rt_midi_queue.append (['korg_out', 0, (176, spec_button('record'), 127)])
				
				if curr_loop < midi_loops:
					selected['wav_2_midi_track'][curr_loop - 1] = False
					
				rt_midi_queue.append (['korg_out', 0, (176, button (curr_loop, 2), 0)])
			else: # stop recording
				rt_midi_queue.append (['korg_out', 0, (176, spec_button('record'), 0)])
				
				if record_mode == 'midi':
					print ('Looper:midi_out' + str(curr_loop) + '_0')
					midi_ports['sl_midi_track_' + str(curr_loop)] = jackclient.get_ports ('Looper:midi_out' + str(curr_loop - 1) + '_0', is_midi=True, is_output=True)[0]
					connect_queue.append ([midi_ports, 'sl_midi_track_' + str(curr_loop), 'midimap_in_channel_loop_' + str(curr_loop - 1)])
				else:
				
					#my_midi_ports['korg_out'].write_midi_event (0, (176, spec_button('record'), 0))
					#rt_midi_queue.append (['korg_out', 0, (176, spec_button('record'), 0)])
					
					# copy fx config to loop_fx
					if mode != 'synth' and mode != fluidsynth and curr_loop <= fx_loops:
						copy_fx_config = True
				
				
				
			
			#my_midi_ports['sl_out'].write_midi_event (0, msg['record'])
			
			if record_mode == 'wav':
				rt_midi_queue.append (['sl_out', 0, msg['record_wav']])
			else: # if record_mode == 'midi':
				rt_midi_queue.append (['sl_out', 0, msg['record_midi']])
			pedal_pressed = False
		
		#qc = 0
		while rt_midi_queue:# and qc < 5: # is empty?
			q = rt_midi_queue.popleft()
			print (q)
			my_midi_ports[q[0]].write_midi_event (q[1], q[2])
			#qc += 1
		
		for offset, data in my_midi_ports['korg_in'].incoming_midi_events():
			if len(data) == 3:
				b1, b2, b3 = struct.unpack('3B', data)
				process_korg_in (b2, b3)
				print('input: ' + str(b2) + ', ' + str(b3))

#@jackclient.set_xrun_callback
#def xrun (delay):
#    print ('xrun; delay', delay, 'microseconds')
	
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
			print ("Record " + record_mode)
			pedal_pressed = True
			
			sync_switch = not sync_switch
			last_time = time.time()
				
def copy_fx_config_to_loop():
	global copy_fx_config
	while True:
		if copy_fx_config:
			copy_fx_config = False

			# bypass
			#print(selected['fx'])
			for i in range(len(selected['fx'])):
				waste = send_modhost ( modhost_client_fx, 'bypass ' + str ( curr_loop * n_effects + int(i) ) + ' ' + str(int(not selected['fx'][i])) )
				
				#print(('bypass ' + str(i) + ' ' + str(int(not selected['fx'][i])) ))
				#print(waste)
			selected['loop_fx_' + str(curr_loop - 1)] = selected['fx'].copy()
			
			for inst in modhost_params:
				for sym in modhost_params[inst]:
					answer = send_modhost (modhost_client_fx, 'param_get ' + str(inst) + ' ' + sym).split (' ')[2]
					#print (('param_get ' + inst + ' ' + sym))
					#print ('"' + answer + '"')
					waste = send_modhost (modhost_client_fx, 'param_set ' + str (curr_loop * n_effects + int(inst) ) + ' ' + str (sym) + ' ' + str (answer) )
		time.sleep (0.01)

def process_korg_in (cc, value):
	global curr_loop
	global mode
	global curr_loaded
	global osc_data
	global slider_lst_state
	global rot_lst_state
	global selected
	global poweroff_counter
	global connect_queue
	global rt_midi_queue
	global aubio_connected
	global active_modhost_midi
	global record_mode

	if (value > 0):
		#power off
		if cc == spec_button ('save_blink'):
			poweroff_counter += 1
			if poweroff_counter >= 3:
				call (["poweroff"])
				
		else :
			poweroff_counter = 0
			
			pmode = mode
			
			# select mode
			if cc == spec_button ('loop'):
				record_mode = 'wav'
				
				if mode != 'loop':
					updateLeds (mode, 'loop')
					mode = 'loop'
					
					connect_queue.append ([midi_ports, 'korg_in',  'sl'])
					
					if pmode == 'synth':
						disconnect_queue.append ([midi_ports, 'korg_in', 'amsynth'])
						connect_loop()
					elif pmode == fluidsynth:
						disconnect_queue.append ([midi_ports, 'korg_in', 'fluidsynth'])
						connect_loop()
					elif pmode == 'fx':
						disconnect_queue.append ([midi_ports, 'korg_in', 'midimap_in_channel_fx'])
					elif pmode == loop_fx:
						disconnect_queue.append ([midi_ports, 'korg_in', 'midimap_in_channel_fx'])
					elif pmode == loop_fluidsynth:
						disconnect_queue.append ([midi_ports, 'korg_in', 'fluidsynth_loop_' + str(curr_loop - 1)])
					elif pmode == 'drum':
						disconnect_queue.append ([midi_ports, 'korg_in', 'midimap_in_cc'])
						disconnect_queue.append ([audio_ports, 'drum', 'sl_in'])
						
					
			elif cc == spec_button ('fx'):
				record_mode = 'wav'
				
				if mode != 'fx':
					updateLeds (mode, 'fx')
					mode = 'fx'
					
					if aubio_connected != None:
						disconnect_queue.append ([midi_ports, 'aubio', aubio_connected])
						aubio_connected = None
						connect_queue.append ([audio_ports, 'fx_out_6', 'playback_1'])
						connect_queue.append ([audio_ports, 'fx_out_6', 'playback_2'])
					
					if pmode == 'synth':
						disconnect_queue.append ([midi_ports, 'korg_in', 'amsynth'])
						connect_loop()
						
					elif pmode == fluidsynth:
						disconnect_queue.append ([midi_ports, 'korg_in', 'fluidsynth'])
					elif pmode == 'loop':
						disconnect_queue.append ([midi_ports, 'korg_in', 'sl'])
					elif pmode == 'drum':
						disconnect_queue.append ([midi_ports, 'korg_in', 'midimap_in_cc'])
						disconnect_queue.append ([audio_ports, 'drum', 'sl_in'])
					#elif pmode == loop_fx:
					#
					
					#load_modhost_midi (0)
					rt_midi_queue.append (['midimap_fx', 0, (176, 0, 127)]) # select channel 0
					connect_queue.append ([midi_ports, 'korg_in', 'midimap_in_channel_fx'])
					
					
			elif cc == spec_button ('drum'):
				record_mode = 'wav'
				
				if mode != 'drum':
					updateLeds (mode, 'drum')
					mode = 'drum'
					
					if pmode == 'loop':
						disconnect_queue.append ([midi_ports, 'korg_in', 'sl'])
					elif pmode == 'synth':
						disconnect_queue.append ([midi_ports, 'korg_in', 'amsynth'])
						disconnect_queue.append ([midi_ports, 'aubio', 'amsynth'])
					elif pmode == fluidsynth:
						disconnect_queue.append ([midi_ports, 'korg_in', 'fluidsynth'])
						disconnect_queue.append ([midi_ports, 'aubio', 'fluidsynth'])
					elif pmode == 'fx':
						disconnect_queue.append ([midi_ports, 'korg_in', 'midimap_in_channel_fx'])
					elif pmode == loop_fx:
						disconnect_midi_loops()
					
					connect_queue.append ([midi_ports, 'korg_in', 'midimap_in_cc'])
					connect_queue.append ([audio_ports, 'drum', 'sl_in'])
					
					if pmode == 'synth' or pmode == fluidsynth:
						connect_queue.append ([audio_ports, 'fx_out_6', 'playback_1'])
						connect_queue.append ([audio_ports, 'fx_out_6', 'playback_2'])
						connect_loop()

			elif cc == spec_button ('synth'):
				record_mode = 'wav'
				
				if pmode == 'loop':
					disconnect_queue.append ([midi_ports, 'korg_in', 'sl'])
				elif pmode == 'fx':
					disconnect_queue.append ([midi_ports, 'korg_in', 'midimap_in_channel_fx'])
				elif pmode == loop_fx:
					disconnect_midi_loops()
				elif pmode == 'drum':
					disconnect_queue.append ([midi_ports, 'korg_in', 'midimap_in_cc'])
				
				if pmode != 'synth' and pmode != fluidsynth:
					disconnect_queue.append ([audio_ports, 'fx_out_6', 'playback_1'])
					disconnect_queue.append ([audio_ports, 'fx_out_6', 'playback_2'])
					disconnect_loop()
				
				if mode != 'synth':  # somewhat -> amsynth
					updateLeds (mode, 'synth')
					mode = 'synth'
					
					if pmode == fluidsynth:
						rt_midi_queue.append (['fluidsynth_out', 0, (176,123,0)] ) # kill every noteon event from fluidsynth
						rt_midi_queue.append (['fluidsynth_out', 9, (176, 123, 0)])
						
						disconnect_queue.append ([midi_ports, 'aubio', 'fluidsynth'])
						disconnect_queue.append ([midi_ports, 'korg_in', 'fluidsynth'])
						
					connect_queue.append ([midi_ports, 'aubio', 'amsynth'])
					connect_queue.append ([midi_ports, 'korg_in', 'amsynth'])
					aubio_connected = 'amsynth'
					
					
				else: # amsynth -> fluidsynth
					updateLeds (mode, fluidsynth)
					mode = fluidsynth
					
					for c in my_midi_ports['fluidsynth_out'].connections:
						disconnect_queue.append ([my_midi_ports['fluidsynth_out'], c])
					connect_queue.append ([my_midi_ports['fluidsynth_out'], midi_ports['fluidsynth']])
					
					rt_midi_queue.append (['amsynth_out', 0, (176,123,0)] ) # kill every noteon event from amsynth
					
					connect_queue.append ([midi_ports, 'aubio', 'fluidsynth'])
					disconnect_queue.append ([midi_ports, 'aubio', 'amsynth'])
					connect_queue.append ([midi_ports, 'korg_in', 'fluidsynth'])
					disconnect_queue.append ([midi_ports, 'korg_in', 'amsynth'])
					
					aubio_connected = 'fluidsynth'

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
					if cc >= 32 and cc <= 39: # select loop (top row)
						if cc - 31 != curr_loop:
							
							rt_midi_queue.append (['korg_out', 0, (176, button (curr_loop, 1), 0)])
							rt_midi_queue.append (['korg_out', 0, (176, button (curr_loop, 3), 0)])
							
							curr_loop = cc - 31
							
							rt_midi_queue.append (['korg_out', 0, (176, button (curr_loop, 1), 127)])
							rt_midi_queue.append (['korg_out', 0, (176, button (curr_loop, 3), 127)])
							
							
							
					#if cc >= 48 and cc <= 55: # midi track synth menu (middle row)
					#	b = cc - 47 - 1
					#	print (b)
					#	port = None
					#	try:
					#		port = jackclient.get_port_by_name ('Looper:midi_out' + str (b) + '_wav2midi')
					#	
					#		selected['wav_2_midi_track'][b] = not selected['wav_2_midi_track'][b]
					#		
					#		if not selected['wav_2_midi_track'][b]:
					#			rt_midi_queue.append (['korg_out', 0, (176, cc, 0)])
					#		
					#		curr_loop = cc - 47
					#		
					#		if selected['wav_2_midi_track'][b]:
					#			updateLeds (mode, loop_fluidsynth)
					#			mode = loop_fluidsynth
					#			
					#			midi_ports['wav_2_midi_' + str(b)] = port
					#			
					#			connect_queue.append ([midi_ports, 'wav_2_midi_' + str(curr_loop - 1), 'fluidsynth_loop_' + str(b)])
					#			disconnect_queue.append ([midi_ports, 'korg_in', 'sl'])
					#			
					#			#print ('connections')
					#			# disconnect own fluidsynth ouput from every present port
					#			for c in my_midi_ports['fluidsynth_out'].connections:
					#			#	print ('connections: ' + str(c))
					#				disconnect_queue.append ([my_midi_ports['fluidsynth_out'], c])
					#					
					#			connect_queue.append ([my_midi_ports['fluidsynth_out'], midi_ports['fluidsynth_loop_' + str (b)]])	
					#			
					#			connect_queue.append ([midi_ports, 'korg_in', 'fluidsynth_loop_' + str (b)])
					#			
					#		else:
					#			for i in range(10):
					#				rt_midi_queue.append (['fluidsynth_out', i, (176,123,0)] ) # kill every noteon event from fluidsynth
					#	except jack.JackError:
					#		pass
					
					#if cc >= 48 and cc <= 55: # midi record (middle row)
					#	b = cc - 47 - 1
					#	if b < fx_loops:
					#		rt_midi_queue.append (['sl_out', 0, (1,46,127)] ) # create new midi track
					#		record_mode = 'midi'
					#		connect_queue.append ([midi_ports, 'korg_in', 'midimap_in_channel_loop_' + str(b) ])
							
						
					if cc >= 64 and cc <= 71: # fx loop menu (bottom row)
						b = cc - 63 - 1
						if b < fx_loops:
							
							rt_midi_queue.append (['midimap_fx', 0, (176, b + 1, 127)]) # select channel b
							
							rt_midi_queue.append (['sl_out', 0, (1,46,127)] ) # create new midi track
							record_mode = 'midi'
							
							disconnect_queue.append ([midi_ports, 'korg_in', 'sl'])
							connect_queue.append ([midi_ports, 'korg_in', 'midimap_in_channel_loop_' + str(b) ])
							
							updateLeds (mode, loop_fx)
							mode = loop_fx
				elif mode == loop_fluidsynth:
					b = button2Int (cc)
					
					if b != None:
						s = selected['loop_fluidsynth_' + str(curr_loop - 1)]
						if s != -1:
							rt_midi_queue.append (['korg_out', 0, (176, s, 0)])
							
						
						if s != cc:
							selected['loop_fluidsynth_' + str(curr_loop - 1)] = cc
							rt_midi_queue.append (['korg_out', 0, (176, selected['loop_fluidsynth_' + str(curr_loop - 1)], 127)])
							
							rt_midi_queue.append (['fluidsynth_out', 0, (192, b)])
					else:
						selected['loop_fluidsynth_' + str(curr_loop - 1)] = -1
							
				elif mode == 'fx' or mode == loop_fx:
					m = 'fx'
					mh = modhost_client_fx
					if mode == loop_fx:
						m = 'loop_fx_' + str(curr_loop - 1)
						#mh = modhost_client_loop[curr_loop - 1]
					
					if cc in buttonList:
						b = button2Int (cc)
						if b < len(selected[m]):
							selected[m][b] = not selected[m][b]
							rt_midi_queue.append (['korg_out', 0, (176, cc, 127*int(selected[m][b]))])
							
							plugin = b if mode == 'fx' else b + (n_effects * curr_loop)
							waste = send_modhost (modhost_client_fx, 'bypass ' + str(plugin) + ' ' + ('0' if selected[m][b] else '1'))
							
				elif mode == 'synth' or mode == fluidsynth:
					if cc in buttonList:
						synth_mode = 'amsynth' if mode == 'synth' else 'fluidsynth'
						synth_port = synth_mode + '_out'
							
						b = button2Int (cc)
						if b != None:
							rt_midi_queue.append ([synth_port, 0, (192, b)])
						
						rt_midi_queue.append (['korg_out', 0, (176, selected[synth_mode], 0)])
						selected[synth_mode] = cc
						rt_midi_queue.append (['korg_out', 0, (176, selected[synth_mode], 127)])
						
					elif mode == 'synth' and cc == spec_button ('sync_lfo'):
						freq_v =  math.sqrt (detect_bpm() / 60);
						lfo_speed = linear_trans ( 0, 127, 0, 7.5, freq_v)
						midi_ports['amsynth_out'].write_midi_event ([176, 3, lfo_speed])
				elif mode == 'drum':
					pass

def process_midi_queue():
	global midi_queue
	
	while started and ports_ready:
		while midi_queue: # is empty?
			q = midi_queue.popleft()
			print (q)
			my_midi_ports[q[0]].write_midi_event (q[1], q[2])
		
		time.sleep (0.01)

def process_connect_queue():
	global connect_queue
	global disconnect_queue
	
	while started and ports_ready:
		while connect_queue: # is empty?
			q = connect_queue.popleft()
			if len(q) == 2:
				connect_ports_direct (q[0], q[1])
			else: # len(q) == 3: # dict, key1, key2 for short
				connect_ports (q[0], q[1], q[2])
		
		while disconnect_queue: # is empty?
			q = disconnect_queue.popleft()
			
			if len(q) == 2:
				connect_ports_direct (q[0], q[1], disconnect=True)
			else: # len(q) == 3: # dict, key1, key2 for short
				connect_ports (q[0], q[1], q[2], disconnect=True)
		
		time.sleep (0.01)

def save():
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

def updateLeds (pmode, cmode): # prev, curr
	global queues
	global selected
	global curr_loop
	
	# update mode leds
	if isinstance (pmode, list):
		for pm in pmode:
			rt_midi_queue.append (['korg_out', 0, (176, spec_button(pm), 0)])
	else:
		rt_midi_queue.append (['korg_out', 0, (176, spec_button(pmode), 0)])

	if isinstance (cmode, list):
		for cm in cmode:
			rt_midi_queue.append (['korg_out', 0, (176, spec_button(cm), 127)])
	else:
		rt_midi_queue.append (['korg_out', 0, (176, spec_button(cmode), 127)])
	
	# update matrix leds
	
	# shut down active leds
	if pmode == 'loop':
		
		rt_midi_queue.append (['korg_out', 0, (176, button(curr_loop, 1), 0)])
		rt_midi_queue.append (['korg_out', 0, (176, button(curr_loop, 3), 0)])
	elif pmode in ['drum', 'fx', loop_fx]:
		pm = 'loop_fx_' + str(curr_loop - 1) if pmode == loop_fx else pmode
		for i in range(len(selected[pm])):
			if selected[pm][i]:
				#my_midi_ports['korg_out'].write_midi_event (0, (176, int2button(i), 0))
				rt_midi_queue.append (['korg_out', 0, (176, int2button(i), 0)])
	elif pmode == fluidsynth:
		#my_midi_ports['korg_out'].write_midi_event (0, (176, selected['fluidsynth'], 0))
		rt_midi_queue.append (['korg_out', 0, (176, selected['fluidsynth'], 0)])
	elif pmode == loop_fluidsynth:
		#my_midi_ports['korg_out'].write_midi_event (0, (176, selected['fluidsynth'], 0))
		if selected['loop_fluidsynth_' + str (curr_loop - 1)] != -1:
			rt_midi_queue.append (['korg_out', 0, (176, selected['loop_fluidsynth_' + str (curr_loop - 1)], 0)])
	elif pmode == 'synth':
		#my_midi_ports['korg_out'].write_midi_event (0, (176, selected['amsynth'], 0))
		rt_midi_queue.append (['korg_out', 0, (176, selected['amsynth'], 0)])
	else:
		#my_midi_ports['korg_out'].write_midi_event (0, (176, selected[pmode], 0))
		rt_midi_queue.append (['korg_out', 0, (176, selected[pmode], 0)])
	
	# light up new ones
	if cmode == 'loop':
		#my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 1), 127))
		#my_midi_ports['korg_out'].write_midi_event (0, (176, button (curr_loop, 3), 127))
		
		rt_midi_queue.append (['korg_out', 0, (176, button(curr_loop, 1), 127)])
		rt_midi_queue.append (['korg_out', 0, (176, button(curr_loop, 3), 127)])
		
		for l in range (midi_loops):
			if selected['wav_2_midi_track'][l]:
				rt_midi_queue.append (['korg_out', 0, (176, button(l + 1, 2), 127)])
		
	elif cmode == 'drum' or cmode == 'fx' or cmode == loop_fx:
		cm = 'loop_fx_' + str(curr_loop - 1) if cmode == loop_fx else cmode
		
		for i in range(len(selected[cm])):
			if selected[cm][i]:
				#my_midi_ports['korg_out'].write_midi_event (0, (176, int2button(i), 127))
				rt_midi_queue.append (['korg_out', 0, (176, int2button(i), 127)])
					
	elif cmode == fluidsynth:
		#my_midi_ports['korg_out'].write_midi_event (0, (176, selected['fluidsynth'], 127))
		rt_midi_queue.append (['korg_out', 0, (176, selected['fluidsynth'], 127)])
	elif cmode == loop_fluidsynth:
		#my_midi_ports['korg_out'].write_midi_event (0, (176, selected['fluidsynth'], 127))
		if selected['loop_fluidsynth_' + str (curr_loop - 1)] != -1:
			rt_midi_queue.append (['korg_out', 0, (176, selected['loop_fluidsynth_' + str (curr_loop - 1)], 127)])
	elif cmode == 'synth':
		#my_midi_ports['korg_out'].write_midi_event (0, (176, selected['amsynth'], 127))
		rt_midi_queue.append (['korg_out', 0, (176, selected['amsynth'], 127)])
	else:
		#my_midi_ports['korg_out'].write_midi_event (0, (176, selected[cmode], 127))
		
		rt_midi_queue.append (['korg_out', 0, (176, selected[cmode], 127)])
		

def load():
	global curr_loaded
	global loop_state
	global mode
	
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
				#midi_ports['hydrogen'].write_midi_event ( bpm_sig )
		
		if os.path.exists (save_dir + str(curr_loaded) + "/beat.txt"):
			with open (save_dir + str(curr_loaded) + "/beat.txt", 'r') as beatfile:
				if mode != 'drum':
					pass#midi_ports['hydrogen'].write_midi_event ( spec_button ('drum') ) # put hydrogen into drum mode
				#midi_ports['hydrogen'].write_midi_event ( [176, int( beatfile.readline() ), 127] ) 
				#midi_ports['hydrogen'].write_midi_event ( spec_button (mode) )
		
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
	_thread.start_new_thread ( read_pedal, () )
	_thread.start_new_thread ( process_midi_queue, () )
	_thread.start_new_thread ( process_connect_queue, () )
	_thread.start_new_thread ( copy_fx_config_to_loop, () )
except:
	print ("Error: unable to start thread: " + str(sys.exc_info()[0]))

#pdb.set_trace()
while True:
	time.sleep (1)
