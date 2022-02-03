def getPortDesc (loops, fx_loops, n_effects, midi_loops):
	return [('capture_1', ['system:capture_1']),
			 ('capture_2', ['system:capture_1']),
			 #('capture_2', ['system:capture_2']),
			 ('playback_1', ['system:playback_1']),
			 ('playback_2', ['system:playback_2']),
			 #('hydrogen_out', ['Hydrogen', 'out_R']),
			 ('aubio_in', ['aubio', 'in']),
			 ('amsynth_out', ['amsynth', 'R out']),
			 ('fluidsynth_out', ['fluidsynth-midi', 'right']),
			 ('drum', ['fluidsynth-midi-01', 'right']),
			 ('sl_in', ['Looper:in'])] + \
			 [('sl_out_' + str(i), ['Looper', 'out' + str(i)]) for i in range(loops)] + \
			 [('fx_in_' + str(i), ['effect_' + str(i) + ':in']) for i in range(n_effects)] + \
			 [('fx_out_' + str(i), ['effect_' + str(i) + ':out']) for i in range(n_effects)] + \
			 [('loop_fx_' + str(k) + '_in_' + str(i), ['effect_' + str(((k + 1) * n_effects) + i) + ':in']) for i in range(n_effects) for k in range(fx_loops)] + \
			 [('loop_fx_' + str(k) + '_out_' + str(i), ['effect_' + str(((k + 1) * n_effects) + i) + ':out']) for i in range(n_effects) for k in range(fx_loops)] + \
			 [('fluidsynth_loop_' + str(i), ['fluidsynth-midi-0' + str(i + 2) + ':right']) for i in range (midi_loops)]

def getPortDescMidi (fx_loops, midi_loops):
	return 	[('korg_in', ['system', 'capture']),
			 ('korg_out', ['system', 'playback']),
			 ('sl', ['Looper', 'midi_control']),
			 ('sl_capture', ['Looper', 'midi_capture']),
			 #('hydrogen', ['hydrogen', 'midi', 'RX']),
			 ('amsynth', ['amsynth', 'midi_in']),
			 ('fluidsynth', ['fluidsynth-midi', 'midi']),
			 ('drum', ['fluidsynth-midi-01', 'midi']),
			 ('aubio', ['aubio', 'midi_out']),
			 ('midimap_in_cc', ['MidiMap', 'in_cc']),
			 ('midimap_out_cc', ['MidiMap', 'out_cc-0']),
			 ('midimap_in_channel_fx', ['MidiMap', 'in_channel-0']),
			 ('midimap_out_channel_fx', ['MidiMap', 'out_channel-0']),
			 ('midimap_control_fx', ['MidiMap', 'control-0']),
			 ('mod-host-fx', ['mod-host:midi_in'])] + \
			 [('fluidsynth_loop_' + str(i), ['fluidsynth-midi-0' + str(i + 2) + ':midi_00']) for i in range(midi_loops)] + \
			 [('midimap_in_channel_loop_' + str(i), ['MidiMap:in_channel-' + str(i+1)]) for i in range(fx_loops)] + \
			 [('midimap_out_channel_loop_' + str(i), ['MidiMap:out_channel-' + str(i+1)]) for i in range(fx_loops)] #+ \
			 #[('midimap_control_loop_' + str(i), ['MidiMap:control-' + str(i+1)]) for i in range(fx_loops)] #+ \
			 #[('mod-host-loop_' + str(i), ['mod-host-0' + str(i + 1) + ':midi_in']) for i in range(fx_loops)]
