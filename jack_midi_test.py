import jack
import binascii
import struct

client = jack.Client('MIDI-Monitor')
inport = client.midi_inports.register('input')

outport = client.midi_outports.register('output')


@client.set_process_callback
def process(frames):
	outport.clear_buffer()
	
	for offset, data in inport.incoming_midi_events():
		print('{0}: 0x{1}'.format(client.last_frame_time + offset,binascii.hexlify(data).decode()))
		
		if len(data) == 3:
			status, pitch, vel = struct.unpack('3B', data)
			print(offset)
			if vel == 127:
				print ('huuarray')
				outport.write_midi_event(offset, data)
				outport.write_midi_event(offset, (status, pitch + 1, vel))
		

with client:
	print('#' * 80)
	print('press Return to quit')
	print('#' * 80)
	input()
