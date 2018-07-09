#!/usr/bin/python3

import sys
import os
import stat
import time
import _thread
import rtmidi
from rtmidi import midiutil
from inputs import devices
import liblo
from subprocess import call
import math

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

jackclient = jack.Client ('MidiManager')

def getPort (ports, keywords):
	for i in ports:
		if sum([1 for k in keywords if k in i.name]) == len(keywords):
			return i
	
	return None

def connect_ports (ports, pin, pout, disconnect=False):
	if pin is iteratable 
	
	if (not ports[pin] is None) and  (not ports[pout] is None):
		try:
			if not disconnect:
				jackclient.connect (ports[pin], ports[pout])
			else:
				jackclient.disconnect (port[pin], port[pout])
		except jack.JackError as e:
			print (e)
	else:
		if ports[pin] is None:
			print ('port ' + pin + ' is  None')
		if ports[pout] is None:
			print ('port ' + pout + ' is  None')

def disconnect_ports (port, pin, pout):
	connect_ports (port, pin, pout, disconnect=True)

all_audio_ports = [i for i in jackclient.get_ports() if i.__class__ == jack.Port]
port_desc = [('capture_1', ['system:capture_1']),
			 ('capture_2', ['system:capture_2']),
			 ('playback_1', ['system:playback_1']),
			 ('playback_2', ['system:playback_2']),
			 ('rr_in_1', ['rakarrack:in_1']),
			 ('rr_in_2', ['rakarrack:in_2']),
			 ('rr_out_1', ['rakarrack:out_1']),
			 ('rr_out_2', ['rakarrack:out_2']),
			 ('hydrogen_out_1', ['Hydrogen', 'out_R']),
			 ('hydrogen_out_2', ['Hydrogen', 'out_L']),
			 ('amsynth_out_1', ['amsynth', 'R out']),
			 ('amsynth_out_2', ['amsynth', 'L out']),
			 ('fluidsynth_out_1', ['fluidsynth', 'right']),
			 ('fluidsynth_out_2', ['fluidsynth', 'left'])] + \
			 [('sl_out_' + str(i+1), ['sooperlooper', 'loop' + str(i) + '_out_1']) for i in range(8)] + \
			 [('sl_in_' + str(i+1), ['sooperlooper', 'loop' + str(i) + '_in_1']) for i in range(8)]
audio_ports = {k: getPort (all_audio_ports, v) for (k, v) in port_desc}

### connecting ports

connect_ports (audio_ports, 'capture_1', 'rr_in_1')
connect_ports (audio_ports, 'capture_1', 'rr_in_2')
connect_ports (audio_ports, 'capture_2', 'rr_in_1')
connect_ports (audio_ports, 'capture_2', 'rr_in_2')

for i in ['hydrogen_out_1', 'hydrogen_out_2', 'rr_out_1', 'rr_out_2', 'amsynth_out_1', 'amsynth_out_2', 'fluidsynth_out_1', 'fluidsynth_out_2']:
	connect_ports (audio_ports, i, 'playback_1')
	connect_ports (audio_ports, i, 'playback_2')

for i in audio_ports:
	if 'sl_in' in str(i):
		connect_ports (audio_ports, 'rr_out_1', i)
		connect_ports (audio_ports, 'rr_out_2', i)
	if 'sl_out' in str(i):
		connect_ports (audio_ports, i, 'playback_1')
		connect_ports (audio_ports, i, 'playback_2')

all_midi_ports = [i for i in jackclient.get_ports() if i.__class__ == jack.MidiPort]
port_desc = [('korg_in', ['nanoKONTROL', 'capture']),
			 ('korg_out', ['nanoKONTROL', 'playback']),
			 ('sl', ['sooperlooper', 'playback']),
			 ('rr', ['rakarrack', 'in']),
			 ('hydrogen', ['Hydrogen', 'playback']),
			 ('amsynth', ['amsynth', 'playback']),
			 ('fluidsynth', ['FLUID', 'playback']),
			 ('aubio', ['midi_out'])]
midi_ports = {k: getPort (all_midi_ports, v) for (k, v) in port_desc}

connect_ports (midi_ports, 'korg_out', 'sl')
connect_ports (midi_ports, 'korg_out', 'hydrogen')
connect_ports (midi_ports, 'korg_out', 'rr')

slider_lst_state = [-1]*8
rot_lst_state = [-1]*8

########################################################################
## buttons, messages
########################################################################

def button (loop, n, on=True):
	return [176, 32 + (loop - 1) + (n - 1)*16 , 127*on]

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
		return [176, 45, 127*on]
	elif s == 'loop':			# left arrow, bottom
		return [176, 43, 127*on]
	elif s == 'fx':				# right arrow, bottom
		return [176, 44, 127*on]
	elif s == 'drum':			# square, bottom
		return [176, 42, 127*on]
	elif s == 'synth': # triangle, bottom
		return [176, 41, 127*on]
	elif s == 'save': # ball, bottom
		return [176, 45, 127*on]
	elif s == 'load_next': # Track right
		return [176, 59, 127*on]
	elif s == 'load_prev': # Track left
		return [176, 58, 127*on]
	elif s == 'save_blink': # cycle
		return [176, 46, 127*on]
	elif s == 'sync_lfo': # set
		return [176, 60, 127*on]
		
		
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

midi = {'korg_in': rtmidi.MidiIn(), 'korg_out': rtmidi.MidiOut(), 'sl_out': rtmidi.MidiOut(), 'rr_out': rtmidi.MidiOut(), 'amsynth_out': rtmidi.MidiOut(midiutil.get_api_from_environment(rtmidi.API_UNIX_JACK)), 'fluidsynth_out': rtmidi.MidiOut(midiutil.get_api_from_environment(rtmidi.API_UNIX_JACK)), 'hydrogen_out':  rtmidi.MidiOut(midiutil.get_api_from_environment(rtmidi.API_UNIX_JACK)) }
queues = { 'out': {}, 'in': {} }
for i in midi:
	if 'out' in i:
		queues['out'][i] = []
#					  select first loop						 	select loop mode
queues['out']['korg_out'] = [button(1, 1), button(1, 3), spec_button ('loop')]
queues['out']['sl_out'] = [button (1, 1), ] # select first loop

osc_writer = None
vosc_reader = None
osc_data = None

curr_loaded = -1
loop_state = []

msg = {'record': [144,0,1], 'sync': [144,1,1], 'desync': [144,2,1], 'playsync': [144,3,1], 'deplaysync': [144,4,1], 'incr_bpm': [144,6,1]}
footswitch = None
for i in devices.mice:
	if 'FootSwitch' in i.name:
		footswitch = i 

curr_loop = 1
sync_switch = True

mode = 'loop' # loop, fx, drum synth

selected = {'fx': button (1, 1)[1], 'drum': [True] + [False]*23, 'amsynth': button (1, 1)[1], 'fluidsynth': button(1,1)[1]}

poweroff_counter = 0

########################################################################
## read, write midi events
########################################################################

def openPorts():
	global midi
	ports = {}
	for i in midi:
		ports[i] = None
	
	keywords = ['nanoKONTROL', 'nanoKONTROL', 'sooperlooper', 'rakarrack', 'amsynth', 'fluidsynth', 'Hydrogen']
	k = 0
	for i in midi:
		# alsa api
		p = midi[i].get_ports()
		for m in range (len (p)):
			if keywords[k] in p[m]:
				ports[i] = m
				try:
					midi[i].open_port (m)
				except:
					pass # port already opened (amsynth)
				
				print ( i + " port: " + midi[i].get_ports()[m] )
				break
			
		k += 1
	
	for i in ports:
		if ports[i] == None:
			print ("Warning: " + i + " could not be opened")

def read_korg():
	while True:
		m = midi['korg_in'].get_message()	
		if m:
			#print("debug: " + str(m))
			process_korg_in (m[0])
		
		time.sleep (0.01)

def write():
	while True:
		for i in queues['out']:
			if len (queues['out'][i]) > 0:
				#print ("write (" +str(i)+") : " + str(queues['out'][i][0]))
				midi[i].send_message (queues['out'][i][0])
				del queues['out'][i][0]
		time.sleep (0.01)
		
def read_pedal():
	global sync_switch
	global footswitch
	
	last_time = 0
	while True:
		footswitch.read()
		if time.time() - last_time > 0.4:
			print ("Record")
			if sync_switch:
				queues['out']['korg_out'].append ( spec_button ('record') )
				#queues['out']['sl_out'].append (msg['desync'])
				#queues['out']['sl_out'].append (msg['deplaysync'])
			else:
				queues['out']['korg_out'].append ( spec_button ('record', False) )
				#queues['out']['sl_out'].append (msg['sync'])
				#queues['out']['sl_out'].append (msg['playsync'])
			
			queues['out']['sl_out'].append (msg['record'])
			
			sync_switch = not sync_switch
			last_time = time.time()

########################################################################
## process
########################################################################

def process_korg_in (msg):
	global curr_loop
	global mode
	global curr_loaded
	global osc_data
	global slider_lst_state
	global rot_lst_state
	global selected
	global poweroff_counter

	# select mode
	if msg[:2] == spec_button ('loop')[:2]:
		if mode != 'loop':
			updateLeds (mode, 'loop')
			mode = 'loop'
			
			#call (["aconnect", str(midi_ports['korg']),  str(midi_ports['sl'])])
			#call (["aconnect", "-d", str(midi_ports['korg']),  str(midi_ports['amsynth'])])
			#call (["jack_disconnect", str(midi_ports['korg_jack']),  str(midi_ports['amsynth_jack'])])
			
			connect_ports (midi_ports, 'korg_out', 'sl')
			disconnect_ports (midi_ports, 'korg_out', 'amsynth')
			
	elif msg[:2] == spec_button ('fx')[:2]:
		if mode != 'fx':
			updateLeds (mode, 'fx')
			mode = 'fx'
			
			#call (["jack_disconnect", str(midi_ports['aubio']),  str(midi_ports['amsynth_jack'])])
			#call (["jack_disconnect", str(midi_ports['aubio']),  str(midi_ports['fluidsynth'])])
			#call (["aconnect", "-d", str(midi_ports['korg']),  str(midi_ports['sl'])])
			#call (["jack_disconnect", str(midi_ports['korg_jack']),  str(midi_ports['amsynth_jack'])])
			
			disconnect_ports (midi_ports, 'aubio', 'amsynth')
			disconnect_ports (midi_ports, 'aubio', 'fluidsynth')
			disconnect_ports (midi_ports, 'korg_out', 'amsynth')
			disconnect_ports (midi_ports, 'korg_out', 'fluidsynth')
			connect_ports (midi_ports, 'korg_out', 'sl')
			
	elif msg[:2] == spec_button ('drum')[:2]:
		if mode != 'drum':
			updateLeds (mode, 'drum')
			mode = 'drum'
			
			#call (["aconnect", "-d", str(midi_ports['korg']),  str(midi_ports['sl'])])
			
			disconnect_ports (midi_ports, 'korg_out', 'sl')
			disconnect_ports (midi_ports, 'korg_out', 'amsynth')
			disconnect_ports (midi_ports, 'korg_out', 'fluidsynth')
			disconnect_ports (midi_ports, 'aubio', 'amsynth')
			disconnect_ports (midi_ports, 'aubio', 'fluidsynth')

	elif msg == spec_button ('synth', False):
		if mode != 'synth' and mode != fluidsynth:
			updateLeds (mode, 'synth')
			mode = 'synth'
			
			#call (["aconnect", str(midi_ports['rr_out']),  str(midi_ports['amsynth'])])
			#call (["jack_disconnect", str(midi_ports['aubio']),  str(midi_ports['fluidsynth'])])
			#call (["jack_connect", str(midi_ports['aubio']),  str(midi_ports['amsynth_jack'])])
			#call (["jack_connect", str(midi_ports['korg_jack']),  str(midi_ports['amsynth_jack'])])
			#call (["aconnect", "-d", str(midi_ports['korg']),  str(midi_ports['sl'])])
			
			queues['out']['fluidsynth_out'].append ([176,123,0]) # kill every noteon event from fluidsynth
			
			disconnect_ports (midi_ports, 'aubio', 'fluidsynth')
			sconnect_ports (midi_ports, 'aubio', 'amsynth')
			disconnect_ports (midi_ports, 'korg_out', 'sl')
			connect_ports (midi_ports, 'korg_out', 'amsynth')
			
		else: # toggle between amsynth and fluidsynth
			if mode == 'synth': # amsynth
				updateLeds (mode, fluidsynth)
				mode = fluidsynth
				
				queues['out']['amsynth_out'].append ([176,123,0]) # kill every noteon event from amsynth
				#call (["jack_connect", str(midi_ports['aubio']),  str(midi_ports['fluidsynth'])])
				#call (["jack_disconnect", str(midi_ports['aubio']),  str(midi_ports['amsynth_jack'])])
				#call (["jack_connect", str(midi_ports['korg_jack']),  str(midi_ports['fluidsynth'])])
				#call (["jack_disconnect", str(midi_ports['korg_jack']),  str(midi_ports['amsynth_jack'])])
				
				connect_ports (midi_ports, 'aubio', 'fluidsynth')
				disconnect_ports (midi_ports, 'aubio', 'amsynth')
				connect_ports (midi_ports, 'korg_out', 'fluidsynth')
				disconnect_ports (midi_ports, 'korg_out', 'amsynth')
				
			else: # fluidsynth
				updateLeds (mode, 'synth')
				mode = 'synth'
				queues['out']['fluidsynth_out'].append ([176,123,0]) # kill every noteon event from fluidsynth
				#call (["jack_disconnect", str(midi_ports['aubio']),  str(midi_ports['fluidsynth'])])
				#call (["jack_connect", str(midi_ports['aubio']),  str(midi_ports['amsynth_jack'])])
				#call (["jack_disconnect", str(midi_ports['korg_jack']),  str(midi_ports['fluidsynth'])])
				#call (["jack_connect", str(midi_ports['korg_jack']),  str(midi_ports['amsynth_jack'])])
				
				disconnect_ports (midi_ports, 'aubio', 'fluidsynth')
				connect_ports (midi_ports, 'aubio', 'amsynth')
				disconnect_ports (midi_ports, 'korg', 'fluidsynth')
				connect_ports (midi_ports, 'korg', 'amsynth')
			
	elif msg == spec_button ('save'):
		save()
	elif msg == spec_button ('load_next'):
		if latest_session() > curr_loaded:
			curr_loaded += 1
			load()
	elif msg == spec_button ('load_prev'):
		if 0 < curr_loaded:
			curr_loaded -= 1
			load()
	elif mode == 'loop':
		if msg[1] >= 32 and msg[1] <= 39: # select loop
			if msg[1] - 31 != curr_loop:
				queues['out']['korg_out'].append ( button (curr_loop, 1, False) )
				queues['out']['korg_out'].append ( button (curr_loop, 3, False) )
				
				curr_loop = msg[1] - 31
				
				queues['out']['korg_out'].append ( button (curr_loop, 1) )
				queues['out']['korg_out'].append ( button (curr_loop, 3) )
				
		if msg[1] >= 48 and msg[1] <= 55 and msg[2] == 127: # pause loop
			time.sleep (0.01)
			liblo.send (osc_writer, "/sl/" + str(msg[1] - 48) + "/get", "state", "osc.udp://localhost:9952", "osc.udp://localhost:9952")
			osc_reader.recv (100)
			if osc_data == 14:
				queues['out']['korg_out'].append ( button (msg[1] - 47, 2) )
			else:
				queues['out']['korg_out'].append ( button (msg[1] - 47, 2, False) )
			
	elif mode == 'fx':
		if msg[2] == 127:
			b = button2Int (msg[1])
			if b != None:
				queues['out']['rr_out'].append ([192, b])
			
			if msg[1] in buttonList and msg[2] == 127:
				queues['out']['korg_out'].append ([176, selected['fx'], 0])
				selected['fx'] = msg[1]
				queues['out']['korg_out'].append ([176, selected['fx'], 127])
	elif mode == 'synth' or mode == fluidsynth:
		if msg[2] == 127:
			if msg[1] in buttonList:
				synth_mode = 'amsynth' if mode == 'synth' else 'fluidsynth'
				synth_port = synth_mode + '_out'
					
				#call (["aconnect", "-d", str(midi_ports['korg']),  str(midi_ports['amsynth'])])
				time.sleep (0.3)
				b = button2Int (msg[1])
				if b != None:
					queues['out'][synth_port].append ([192, b])
				#call (["aconnect", str(midi_ports['korg']),  str(midi_ports['amsynth'])])
				
				queues['out']['korg_out'].append ([176, selected[synth_mode], 0])
				selected[synth_mode] = msg[1]
				queues['out']['korg_out'].append ([176, selected[synth_mode], 127])
			elif mode == 'synth' and msg[1] == spec_button ('sync_lfo')[1]:
				#						min max values for lfo in amsynth, min max bpm defined in hydrogen
				#print ("bpm: " + str(detect_bpm()) )
				#print ("freq: " + str(detect_bpm()/60) )
				freq_v =  math.sqrt (detect_bpm() / 60);
				#print ("sqrt freq: " + str(freq_v))
				lfo_speed = linear_trans ( 0, 127, 0, 7.5, freq_v)
				#lfo_speed = math.log (detect_bpm() / 60, 2)
				queues['out']['amsynth_out'].append ([176, 3, lfo_speed])
				#print (lfo_speed)
			else:
				#print (msg[1])
				print (spec_button('sync_lfo')[1])
	elif mode == 'drum':
		if msg[1] in buttonList and msg[2] == 127:
			#queues['out']['korg_out'].append ([176, selected[mode], 0])
			#selected[mode] = msg[1]
			b = button2Int (msg[1])
			selected[mode][b] = not selected[mode][b]
			print([176, msg[1], 127*int(selected[mode][b])])
			queues['out']['korg_out'].append ([176, msg[1], 127*int(selected[mode][b])])

	# power off
	if msg[:2] == spec_button ('save_blink')[:2]:
		if msg[2] == 127:	
			poweroff_counter += 1
			#print (poweroff_counter)
			if poweroff_counter == 3:
				#call (["systemctl", "stop", "looper.service"])
				call (["poweroff"])
	else :
		poweroff_counter = 0

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

def updateLeds (pmode, cmode): # prev, curr
	global queues
	global selected
	global curr_loop
	
	# update mode leds
	if isinstance (pmode, list):
		for pm in pmode:
			queues['out']['korg_out'].append ( spec_button (pm, False) )
	else:
		queues['out']['korg_out'].append ( spec_button (pmode, False) )

	if isinstance (cmode, list):
		for cm in cmode:
			queues['out']['korg_out'].append ( spec_button (cm) )
	else:
		queues['out']['korg_out'].append ( spec_button (cmode) )
	
	# update matrix leds
	if pmode == 'loop':
		queues['out']['korg_out'].append ( button (curr_loop, 1, False) )
		queues['out']['korg_out'].append ( button (curr_loop, 3, False) )
	
	elif pmode == 'drum':
		for i in range(len(selected['drum'])):
			if selected['drum'][i]:
				queues['out']['korg_out'].append ([176, int2button(i), 0])
	elif pmode == fluidsynth:
		queues['out']['korg_out'].append ([176, selected['fluidsynth'], 0])
	elif pmode == 'synth':
		queues['out']['korg_out'].append ([176, selected['amsynth'], 0])
	else:
		queues['out']['korg_out'].append ([176, selected[pmode], 0])
	
	if cmode == 'loop':
		queues['out']['korg_out'].append ( button (curr_loop, 1) )
		queues['out']['korg_out'].append ( button (curr_loop, 3) )
	elif cmode == 'drum':
		for i in range(len(selected['drum'])):
			if selected['drum'][i]:
				queues['out']['korg_out'].append ([176, int2button(i), 127])
	elif cmode == fluidsynth:
		queues['out']['korg_out'].append ([176, selected['fluidsynth'], 127])
	elif cmode == 'synth':
		queues['out']['korg_out'].append ([176, selected['amsynth'], 127])
	else:
		queues['out']['korg_out'].append ([176, selected[cmode], 127])
		

def load():
	global curr_loaded
	global loop_state
	global mode
	
	queues['out']['korg_out'].append ( spec_button ('save_blink') )

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
				queues['out']['hydrogen_out'].append ( bpm_sig )
		
		if os.path.exists (save_dir + str(curr_loaded) + "/beat.txt"):
			with open (save_dir + str(curr_loaded) + "/beat.txt", 'r') as beatfile:
				if mode != 'drum':
					queues['out']['hydrogen_out'].append ( spec_button ('drum') ) # put hydrogen into drum mode
				queues['out']['hydrogen_out'].append ( [176, int( beatfile.readline() ), 127] ) 
				queues['out']['hydrogen_out'].append ( spec_button (mode) )
		
		for i in range(8): # play
			if loop_state[i] == 10:
				liblo.send (osc_writer, "/sl/" + str(i) + "/hit", "mute_off")
			if loop_state[i] == 14:
				liblo.send (osc_writer, "/sl/" + str(i) + "/hit", "pause")
			
			queues['out']['korg_out'].append ( button (i + 1, 2, False) )
				
				
		loop_state = []
	
	time.sleep (1)
	queues['out']['korg_out'].append ( spec_button ('save_blink', False) )
	
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
	

openPorts()
try:
	osc_writer = liblo.Address (osc_write_port)
	osc_reader = liblo.Server (osc_read_port)
	osc_reader.add_method (None, None, get_osc_data)
except:
  print (sys.exc_info()[0])


try:
	_thread.start_new_thread ( read_korg, () )
	_thread.start_new_thread ( read_pedal, () )
	_thread.start_new_thread ( write, () )
except:
	print ("Error: unable to start thread: " + str(sys.exc_info()[0]))

while True:
	time.sleep (0.01)
