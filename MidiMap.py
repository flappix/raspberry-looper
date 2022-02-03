import jack
import time
import struct
import argparse

parser = argparse.ArgumentParser()
parser.add_argument ('-c', '--channel', help='number of channel tracks',  type=int)
parser.add_argument ('-cc', '--cc', help='number of cc tracks', type=int)
args = vars(parser.parse_args())

n_channel = args['channel']
n_cc = args['cc']

client = jack.Client ('MidiMap')

control = [client.midi_inports.register ( 'control-' + str(i) ) for i in range (n_channel)] # select output midi channel 
curr_channel = [i for i in range (n_channel)]

inport_channel = [client.midi_inports.register ( 'in_channel-' + str(i) ) for i in range (n_channel)]
outport_channel = [client.midi_outports.register ( 'out_channel-' + str(i) ) for i in range (n_channel)]

inport_cc = [client.midi_inports.register ( 'in_cc-' + str(i) ) for i in range (n_cc)]
outport_cc = [client.midi_outports.register ( 'out_cc-' + str(i) ) for i in range (n_cc)]



@client.set_process_callback
def process (frames):
	global curr_channel
	
	for o in outport_channel:
		o.clear_buffer()
	for o in outport_cc:
		o.clear_buffer()
	
	# cc
	for i in range (n_cc):
		for offset, data in inport_cc[i].incoming_midi_events():
			b1, b2, b3 = struct.unpack('3B', data)
			outport_cc[i].write_midi_event ( 0, (144, b2, b3) )
		
	for i in range (n_channel):
		# channel
		for offset, data in inport_channel[i].incoming_midi_events():
			b1, b2, b3 = struct.unpack('3B', data)
			outport_channel[i].write_midi_event ( 0, (b1 + curr_channel[i], b2, b3) )
		
		# control
		for offset, data in control[i].incoming_midi_events():
			b1, b2, b3 = struct.unpack('3B', data)
			curr_channel[i] = b2

with client:
		client.activate()
		
		while True:
			time.sleep (1000)
