import jack
import time
import struct

client = jack.Client ('Midi2Modhost')
inport = client.midi_inports.register ('in')
outport = client.midi_outports.register ('out')

@client.set_process_callback
def process (frames):
	outport.clear_buffer()
	
	for offset, data in inport.incoming_midi_events():
		b1, b2, b3 = struct.unpack('3B', data)
		
		outport.write_midi_event ( 0, (144, b2, b3) )

with client:
		client.activate()
		
		while True:
			time.sleep (1000)
