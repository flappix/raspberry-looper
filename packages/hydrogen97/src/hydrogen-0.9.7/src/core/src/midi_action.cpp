/*
 * Hydrogen
 * Copyright(c) 2002-2008 by Alex >Comix< Cominu [comix@users.sourceforge.net]
 *
 * http://www.hydrogen-music.org
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY, without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 */
#include <QObject>

#include <hydrogen/audio_engine.h>
#include <hydrogen/event_queue.h>
#include <hydrogen/hydrogen.h>
#include <hydrogen/playlist.h>

#include <hydrogen/basics/instrument.h>
#include <hydrogen/basics/instrument_list.h>
#include <hydrogen/basics/song.h>
#include <hydrogen/basics/pattern_list.h>

#include <hydrogen/Preferences.h>
#include <hydrogen/midi_action.h>
#include <map>

#include <unistd.h>

#include <fstream>
#include <iostream>

#include <hydrogen/helpers/filesystem.h>

#include <thread>

using namespace H2Core;

/* Helperfunctions */

// hack
int linear_trans (int x1, int x2, int a, int b, int c)
{
	float fx1 = (float)x1;
	float fx2 = (float)x2;
	float fa = (float)a;
	float fb = (float)b;
	float fc = (float)c;
	float fr = fx1 + ((fx2 - fx1)/(fb - fa)) * (fc - fa);
	return (int)fr;
}

bool setAbsoluteFXLevel( int nLine, int fx_channel , int fx_param)
{
	//helper function to set fx levels

	Hydrogen::get_instance()->setSelectedInstrumentNumber( nLine );

	Hydrogen *engine = Hydrogen::get_instance();
	Song *song = engine->getSong();
	InstrumentList *instrList = song->get_instrument_list();
	Instrument *instr = instrList->get( nLine );
	if ( instr == NULL) return false;

	if( fx_param != 0 ){
		instr->set_fx_level(  ( (float) (fx_param / 127.0 ) ), fx_channel );
	} else {
		instr->set_fx_level( 0 , fx_channel );
	}

	Hydrogen::get_instance()->setSelectedInstrumentNumber(nLine);

	return true;
}

//hack
void waitForPlay (Hydrogen *pEngine, Playlist *pl, int sn, float bpm)
{
	int curr_tick = pEngine->getRealtimeTickPosition();
	int tick_buf;
	pl->setNextSongByNumber(sn);

	int nState = pEngine->getState();
	while ( nState != STATE_READY){
		pEngine->sequencer_play();

		usleep (100000);
		nState = pEngine->getState();
	}
	
	pEngine->sequencer_play();

	AudioEngine::get_instance()->lock( RIGHT_HERE );
	pEngine->setBPM (bpm);
	AudioEngine::get_instance()->unlock();
}

bool setSong( int songnumber ) {
	Hydrogen *pEngine = Hydrogen::get_instance();
	Playlist *PL = Playlist::get_instance();
	int curr_bpm = pEngine->getBPM();
	int asn = PL->getActiveSongNumber();
	if(asn != songnumber && songnumber >= 0 && songnumber <= pEngine->m_PlayList.size()-1){
		
		//cout<<"tick: "<<pEngine->getTickPosition()<<endl;
		//PL->setNextSongByNumber( songnumber );
		
		//waitForPlay (pEngine, songnumber, curr_bpm);
		std::thread wfp ( waitForPlay, pEngine, PL, songnumber, curr_bpm );
		wfp.detach();
		//wfp.join();
		
	}
	return true;
}

 // hack
bool setSong_ext (int s, Hydrogen *pEngine)
{
	bool r = setSong (s);
	if (r)
	{
		int nState = pEngine->getState();
		if ( nState == STATE_READY ){
			pEngine->sequencer_play();
			return true;
		}
	}
	
	return false;
}

/**
* @class MidiAction
*
* @brief This class represents a midi action.
*
* This class represents actions which can be executed
* after a midi event occured. An example is the "MUTE"
* action, which mutes the outputs of hydrogen.
*
* An action can be linked to an event. If this event occurs,
* the action gets triggered. The handling of events takes place
* in midi_input.cpp .
*
* Each action has two independ parameters. The two parameters are optional and
* can be used to carry additional informations, which mean
* only something to this very Action. They can have totally different meanings for other Actions.
* Example: parameter1 is the Mixer strip and parameter 2 a multiplier for the volume change on this strip
*
* @author Sebastian Moors
*
*/

const char* MidiAction::__class_name = "MidiAction";

MidiAction::MidiAction( QString typeString ) : Object( __class_name ) {

	type = typeString;
	QString parameter1 = "0";
	QString parameter2 = "0" ;
}

/**
* @class MidiActionManager
*
* @brief The MidiActionManager cares for the execution of MidiActions
*
*
* The MidiActionManager handles the execution of midi actions. The class
* includes the names and implementations of all possible actions.
*
*
* @author Sebastian Moors
*
*/
MidiActionManager* MidiActionManager::__instance = NULL;
const char* MidiActionManager::__class_name = "ActionManager";

MidiActionManager::MidiActionManager() : Object( __class_name )
{
	__instance = this;

	m_nLastBpmChangeCCParameter = -1;
	drum_mode = 0; // hack
	// hack
	QStringList sys_dks = Filesystem::sys_drumkits_list();
	for (int i = 0; i < sys_dks.size(); ++i) {
		QString absPath = Filesystem::sys_drumkits_dir() + "/" + sys_dks[i];
		Drumkit *pInfo = Drumkit::load( absPath );
		if (pInfo) {
			drumkit_info_list.push_back( pInfo );
		}
	}
	QStringList usr_dks = Filesystem::usr_drumkits_list();
	for (int i = 0; i < usr_dks.size(); ++i) {
		QString absPath = Filesystem::usr_drumkits_dir() + "/" + usr_dks[i];
		Drumkit *pInfo = Drumkit::load( absPath );
		if (pInfo) {
			drumkit_info_list.push_back( pInfo );
		}
	}
	current_drumkit = 0; // hack

	/*
		the actionList holds all Action identfiers which hydrogen is able to interpret.
	*/
	actionList <<""
			  << "PLAY"
			  << "PLAY/STOP_TOGGLE"
			  << "PLAY/PAUSE_TOGGLE"
			  << "STOP"
			  << "PAUSE"
			  << "RECORD_READY"
			  << "RECORD/STROBE_TOGGLE"
			  << "RECORD_STROBE"
			  << "RECORD_EXIT"
			  << "MUTE"
			  << "UNMUTE"
			  << "MUTE_TOGGLE"
			  << ">>_NEXT_BAR"
			  << "<<_PREVIOUS_BAR"
			  << "BPM_INCR"
			  << "BPM_DECR"
			  << "BPM_CC_RELATIVE"
			  << "BPM_FINE_CC_RELATIVE"
			  << "MASTER_VOLUME_RELATIVE"
			  << "MASTER_VOLUME_ABSOLUTE"
			  << "STRIP_VOLUME_RELATIVE"
			  << "STRIP_VOLUME_ABSOLUTE"
			  << "EFFECT1_LEVEL_RELATIVE"
			  << "EFFECT2_LEVEL_RELATIVE"
			  << "EFFECT3_LEVEL_RELATIVE"
			  << "EFFECT4_LEVEL_RELATIVE"
			  << "EFFECT1_LEVEL_ABSOLUTE"
			  << "EFFECT2_LEVEL_ABSOLUTE"
			  << "EFFECT3_LEVEL_ABSOLUTE"
			  << "EFFECT4_LEVEL_ABSOLUTE"
			  << "SELECT_NEXT_PATTERN" // hacked
			  << "SELECT_NEXT_PATTERN_CC_ABSOLUT"
			  << "SELECT_NEXT_PATTERN_PROMPTLY"
			  << "SELECT_NEXT_PATTERN_RELATIVE"
			  << "SELECT_PREV_PATTERN_RELATIVE"
			  << "SELECT_AND_PLAY_PATTERN"
			  << "PAN_RELATIVE"
			  << "PAN_ABSOLUTE"
			  << "BEATCOUNTER"
			  << "TAP_TEMPO"
			  << "PLAYLIST_SONG"
			  << "PLAYLIST_NEXT_SONG"
			  << "PLAYLIST_PREV_SONG"
			  << "TOGGLE_METRONOME"
			  << "SELECT_INSTRUMENT"
			  << "UNDO_ACTION"
			  << "REDO_ACTION"
			  << "BPM_CC_ABSOLUTE" // hack
			  << "LOOP_MODE" // hack
			  << "FX_MODE" // hack
			  << "DRUM_MODE" // hack
			  << "LOAD_NEXT_DRUMKIT" // hack
			  << "LOAD_PREV_DRUMKIT"; // hack

	eventList << ""
			  << "MMC_PLAY"
			  << "MMC_DEFERRED_PLAY"
			  << "MMC_STOP"
			  << "MMC_FAST_FORWARD"
			  << "MMC_REWIND"
			  << "MMC_RECORD_STROBE"
			  << "MMC_RECORD_EXIT"
			  << "MMC_RECORD_READY"
			  << "MMC_PAUSE"
			  << "NOTE"
			  << "CC"
			  << "PROGRAM_CHANGE";
}


MidiActionManager::~MidiActionManager(){
	//INFOLOG( "ActionManager delete" );
	__instance = NULL;
}

void MidiActionManager::create_instance()
{
	if ( __instance == 0 ) {
		__instance = new MidiActionManager;
	}
}

/**
 * The handleAction method is the heard of the MidiActionManager class.
 * It executes the operations that are needed to carry the desired action.
 */
bool MidiActionManager::handleAction( MidiAction * pAction ){

	Hydrogen *pEngine = Hydrogen::get_instance();

	/*
		return false if action is null
		(for example if no Action exists for an event)
	*/
	if( pAction == NULL )	return false;

	QString sActionString = pAction->getType();


	if( sActionString == "PLAY" )
	{
		int nState = pEngine->getState();
		if ( nState == STATE_READY ){
			pEngine->sequencer_play();
		}
		return true;
	}

	if( sActionString == "PLAY/STOP_TOGGLE" || sActionString == "PLAY/PAUSE_TOGGLE" )
	{
		int nState = pEngine->getState();
		switch ( nState )
		{
		case STATE_READY:
			pEngine->sequencer_play();
			break;

		case STATE_PLAYING:
			if( sActionString == "PLAY/STOP_TOGGLE" ) pEngine->setPatternPos( 0 );
			pEngine->sequencer_stop();
			pEngine->setTimelineBpm();
			break;

		default:
			ERRORLOG( "[Hydrogen::ActionManager(PLAY): Unhandled case" );
		}

		return true;
	}

	if( sActionString == "PAUSE" )
	{
		pEngine->sequencer_stop();
		return true;
	}

	if( sActionString == "STOP" )
	{
		pEngine->sequencer_stop();
		pEngine->setPatternPos( 0 );
		pEngine->setTimelineBpm();
		return true;
	}

	if( sActionString == "MUTE" ){
		//mutes the master, not a single strip
		pEngine->getSong()->__is_muted = true;
		return true;
	}

	if( sActionString == "UNMUTE" ){
		pEngine->getSong()->__is_muted = false;
		return true;
	}

	if( sActionString == "MUTE_TOGGLE" ){
		pEngine->getSong()->__is_muted = !Hydrogen::get_instance()->getSong()->__is_muted;
		return true;
	}

	if( sActionString == "BEATCOUNTER" ){
		pEngine->handleBeatCounter();
		return true;
	}

	if( sActionString == "TAP_TEMPO" ){
		pEngine->onTapTempoAccelEvent();
		return true;
	}

	if( sActionString == "SELECT_NEXT_PATTERN" )
	{
		if (drum_mode == 1)
		{
			 // hack
			bool ok2;
			if ( pAction->getParameter2().toInt(&ok2,10) == 127 )
			{
				bool ok;
				int row = pAction->getParameter1().toInt(&ok,10);
				if( row> pEngine->getSong()->get_pattern_list()->size() -1 ){
					return false;
				}

				if(Preferences::get_instance()->patternModePlaysSelected()){
					pEngine->setSelectedPatternNumber( row );
				}
				else
				{
					pEngine->sequencer_setNextPattern( row );
				}

				return true;
			}
		}
		
		return false;
	}

	if( sActionString == "SELECT_NEXT_PATTERN_RELATIVE" ){

		bool ok;

		if(!Preferences::get_instance()->patternModePlaysSelected())
		{
			return true;
		}

		int row = pEngine->getSelectedPatternNumber() + pAction->getParameter1().toInt(&ok,10);

		if( row> pEngine->getSong()->get_pattern_list()->size() -1 )
		{
			return false;
		}

		pEngine->setSelectedPatternNumber( row );

		return true;
	}

	if( sActionString == "SELECT_PREV_PATTERN_RELATIVE" ){
		bool ok;
		if(!Preferences::get_instance()->patternModePlaysSelected())
			return true;
		int row = pEngine->getSelectedPatternNumber() - pAction->getParameter1().toInt(&ok,10);
		if( row < 0 )
			return false;

		pEngine->setSelectedPatternNumber( row );
		return true;
	}

	if( sActionString == "SELECT_NEXT_PATTERN_CC_ABSOLUT" ){
		bool ok;
		int row = pAction->getParameter2().toInt(&ok,10);
		if( row> pEngine->getSong()->get_pattern_list()->size() -1 )
			return false;
		if(Preferences::get_instance()->patternModePlaysSelected())
			pEngine->setSelectedPatternNumber( row );
		else
			return true;// only usefully in normal pattern mode
		return true;
	}

	if( sActionString == "SELECT_NEXT_PATTERN_PROMPTLY" ){// obsolete, use SELECT_NEXT_PATTERN_CC_ABSOLUT instead
		bool ok;
		int row = pAction->getParameter2().toInt(&ok,10);
		pEngine->setSelectedPatternNumberWithoutGuiEvent( row );
		return true;
	}

	if( sActionString == "SELECT_AND_PLAY_PATTERN"){
		bool ok;
		int row = pAction->getParameter1().toInt(&ok,10);
		pEngine->setSelectedPatternNumber( row );
		pEngine->sequencer_setNextPattern( row );

		int nState = pEngine->getState();
		if ( nState == STATE_READY ){
			pEngine->sequencer_play();
		}

		return true;
	}

	if( sActionString == "SELECT_INSTRUMENT" ){
		bool ok;
		int  instrument_number = pAction->getParameter2().toInt(&ok,10) ;
		if ( pEngine->getSong()->get_instrument_list()->size() < instrument_number )
			instrument_number = pEngine->getSong()->get_instrument_list()->size() -1;
		pEngine->setSelectedInstrumentNumber( instrument_number );
		return true;
	}

	if( sActionString == "EFFECT1_LEVEL_ABSOLUTE" ){
		bool ok;
		int nLine = pAction->getParameter1().toInt(&ok,10);
		int fx_param = pAction->getParameter2().toInt(&ok,10);
		setAbsoluteFXLevel( nLine, 0 , fx_param );
	}

	if( sActionString == "EFFECT2_LEVEL_ABSOLUTE" ){
		bool ok;
		int nLine = pAction->getParameter1().toInt(&ok,10);
		int fx_param = pAction->getParameter2().toInt(&ok,10);
		setAbsoluteFXLevel( nLine, 1 , fx_param );
	}

	if( sActionString == "EFFECT3_LEVEL_ABSOLUTE" ){
		bool ok;
		int nLine = pAction->getParameter1().toInt(&ok,10);
		int fx_param = pAction->getParameter2().toInt(&ok,10);
		setAbsoluteFXLevel( nLine, 2 , fx_param );
	}

	if( sActionString == "EFFECT4_LEVEL_ABSOLUTE" ){
		bool ok;
		int nLine = pAction->getParameter1().toInt(&ok,10);
		int fx_param = pAction->getParameter2().toInt(&ok,10);
		setAbsoluteFXLevel( nLine, 3 , fx_param );
	}

	if( sActionString == "MASTER_VOLUME_RELATIVE" ){
		//increments/decrements the volume of the whole song

		bool ok;
		int vol_param = pAction->getParameter2().toInt(&ok,10);

		Hydrogen *engine = Hydrogen::get_instance();
		Song *song = engine->getSong();



		if( vol_param != 0 ){
			if ( vol_param == 1 && song->get_volume() < 1.5 ){
				song->set_volume( song->get_volume() + 0.05 );
			}  else  {
				if( song->get_volume() >= 0.0 ){
					song->set_volume( song->get_volume() - 0.05 );
				}
			}
		} else {
			song->set_volume( 0 );
		}

	}

	if( sActionString == "MASTER_VOLUME_ABSOLUTE" ){
		//sets the volume of a master output to a given level (percentage)

		bool ok;
		int vol_param = pAction->getParameter2().toInt(&ok,10);


		Hydrogen *engine = Hydrogen::get_instance();
		Song *song = engine->getSong();


		if( vol_param != 0 ){
			song->set_volume( 1.5* ( (float) (vol_param / 127.0 ) ));
		} else {
			song->set_volume( 0 );
		}

	}

	if( sActionString == "STRIP_VOLUME_RELATIVE" ){
		//increments/decrements the volume of one mixer strip

		bool ok;
		int nLine = pAction->getParameter1().toInt(&ok,10);
		int vol_param = pAction->getParameter2().toInt(&ok,10);

		Hydrogen::get_instance()->setSelectedInstrumentNumber( nLine );

		Hydrogen *engine = Hydrogen::get_instance();
		Song *song = engine->getSong();
		InstrumentList *instrList = song->get_instrument_list();

		Instrument *instr = instrList->get( nLine );

		if ( instr == NULL) return 0;

		if( vol_param != 0 ){
			if ( vol_param == 1 && instr->get_volume() < 1.5 ){
				instr->set_volume( instr->get_volume() + 0.1 );
			}  else  {
				if( instr->get_volume() >= 0.0 ){
					instr->set_volume( instr->get_volume() - 0.1 );
				}
			}
		} else {
			instr->set_volume( 0 );
		}

		Hydrogen::get_instance()->setSelectedInstrumentNumber(nLine);
	}

	if( sActionString == "STRIP_VOLUME_ABSOLUTE" ){
		//sets the volume of a mixer strip to a given level (percentage)

		bool ok;
		int nLine = pAction->getParameter1().toInt(&ok,10);
		int vol_param = pAction->getParameter2().toInt(&ok,10);

		Hydrogen::get_instance()->setSelectedInstrumentNumber( nLine );

		Hydrogen *engine = Hydrogen::get_instance();
		Song *song = engine->getSong();
		InstrumentList *instrList = song->get_instrument_list();

		Instrument *instr = instrList->get( nLine );

		if ( instr == NULL) return 0;

		if( vol_param != 0 ){
			instr->set_volume( 1.5* ( (float) (vol_param / 127.0 ) ));
		} else {
			instr->set_volume( 0 );
		}

		Hydrogen::get_instance()->setSelectedInstrumentNumber(nLine);
	}

	if( sActionString == "PAN_ABSOLUTE" ){

		// sets the absolute panning of a given mixer channel

		bool ok;
		int nLine = pAction->getParameter1().toInt(&ok,10);
		int pan_param = pAction->getParameter2().toInt(&ok,10);


		float pan_L;
		float pan_R;

		Hydrogen *engine = Hydrogen::get_instance();
		engine->setSelectedInstrumentNumber( nLine );
		Song *song = engine->getSong();
		InstrumentList *instrList = song->get_instrument_list();

		Instrument *instr = instrList->get( nLine );

		if( instr == NULL )
			return false;

		pan_L = instr->get_pan_l();
		pan_R = instr->get_pan_r();

		// pan
		float fPanValue = 0.0;
		if (pan_R == 1.0) {
			fPanValue = 1.0 - (pan_L / 2.0);
		}
		else {
			fPanValue = pan_R / 2.0;
		}


		fPanValue = 1 * ( ((float) pan_param) / 127.0 );


		if (fPanValue >= 0.5) {
			pan_L = (1.0 - fPanValue) * 2;
			pan_R = 1.0;
		}
		else {
			pan_L = 1.0;
			pan_R = fPanValue * 2;
		}


		instr->set_pan_l( pan_L );
		instr->set_pan_r( pan_R );

		Hydrogen::get_instance()->setSelectedInstrumentNumber(nLine);

		return true;
	}

	if( sActionString == "PAN_RELATIVE" ){

		// changes the panning of a given mixer channel
		// this is useful if the panning is set by a rotary control knob

		bool ok;
		int nLine = pAction->getParameter1().toInt(&ok,10);
		int pan_param = pAction->getParameter2().toInt(&ok,10);

		float pan_L;
		float pan_R;

		Hydrogen *engine = Hydrogen::get_instance();
		engine->setSelectedInstrumentNumber( nLine );
		Song *song = engine->getSong();
		InstrumentList *instrList = song->get_instrument_list();

		Instrument *instr = instrList->get( nLine );

		if( instr == NULL )
			return false;

		pan_L = instr->get_pan_l();
		pan_R = instr->get_pan_r();

		// pan
		float fPanValue = 0.0;
		if (pan_R == 1.0) {
			fPanValue = 1.0 - (pan_L / 2.0);
		}
		else {
			fPanValue = pan_R / 2.0;
		}

		if( pan_param == 1 && fPanValue < 1 ){
			fPanValue += 0.05;
		}

		if( pan_param != 1 && fPanValue > 0 ){
			fPanValue -= 0.05;
		}

		if (fPanValue >= 0.5) {
			pan_L = (1.0 - fPanValue) * 2;
			pan_R = 1.0;
		}
		else {
			pan_L = 1.0;
			pan_R = fPanValue * 2;
		}


		instr->set_pan_l( pan_L );
		instr->set_pan_r( pan_R );

		Hydrogen::get_instance()->setSelectedInstrumentNumber(nLine);

		return true;
	}

	if( sActionString == "BPM_CC_RELATIVE" ){
		/*
		 * increments/decrements the BPM
		 * this is useful if the bpm is set by a rotary control knob
		*/

		AudioEngine::get_instance()->lock( RIGHT_HERE );

		int mult = 1;

		//second parameter of cc command
		//this value should be 1 to decrement and something other then 1 to increment the bpm
		int cc_param = 1;

		//this Action should be triggered only by CC commands

		bool ok;
		mult = pAction->getParameter1().toInt(&ok,10);
		cc_param = pAction->getParameter2().toInt(&ok,10);

		if( m_nLastBpmChangeCCParameter == -1)
		{
			m_nLastBpmChangeCCParameter = cc_param;
		}

		Song* pSong = pEngine->getSong();

		if ( m_nLastBpmChangeCCParameter >= cc_param && pSong->__bpm  < 300) {
			pEngine->setBPM( pSong->__bpm - 1*mult );
		}

		if ( m_nLastBpmChangeCCParameter < cc_param && pSong->__bpm  > 40 ) {
			pEngine->setBPM( pSong->__bpm + 1*mult );
		}

		m_nLastBpmChangeCCParameter = cc_param;

		AudioEngine::get_instance()->unlock();

		return true;
	}

	if( sActionString == "BPM_FINE_CC_RELATIVE" ){
		/*
		 * increments/decrements the BPM
		 * this is useful if the bpm is set by a rotary control knob
		 */

		AudioEngine::get_instance()->lock( RIGHT_HERE );

		int mult = 1;

		//second parameter of cc command
		//this value should be 1 to decrement and something other then 1 to increment the bpm
		int cc_param = 1;

		//this Action should be triggered only by CC commands

		bool ok;
		mult = pAction->getParameter1().toInt(&ok,10);
		cc_param = pAction->getParameter2().toInt(&ok,10);

		if( m_nLastBpmChangeCCParameter == -1)
		{
			m_nLastBpmChangeCCParameter = cc_param;
		}

		Song* pSong = pEngine->getSong();

		if ( m_nLastBpmChangeCCParameter >= cc_param && pSong->__bpm  < 300) {
			pEngine->setBPM( pSong->__bpm - 0.01*mult );
		}

		if ( m_nLastBpmChangeCCParameter < cc_param && pSong->__bpm  > 40 ) {
			pEngine->setBPM( pSong->__bpm + 0.01*mult );
		}

		m_nLastBpmChangeCCParameter = cc_param;

		AudioEngine::get_instance()->unlock();

		return true;
	}

	if( sActionString == "BPM_INCR" ){
		AudioEngine::get_instance()->lock( RIGHT_HERE );

		int mult = 1;

		bool ok;
		mult = pAction->getParameter1().toInt(&ok,10);


		Song* pSong = pEngine->getSong();
		if (pSong->__bpm  < 300) {
			pEngine->setBPM( pSong->__bpm + 1*mult );
		}
		AudioEngine::get_instance()->unlock();

		return true;
	}

	if( sActionString == "BPM_DECR" ){
		AudioEngine::get_instance()->lock( RIGHT_HERE );

		int mult = 1;

		bool ok;
		mult = pAction->getParameter1().toInt(&ok,10);

		Song* pSong = pEngine->getSong();
		if (pSong->__bpm  > 40 ) {
			pEngine->setBPM( pSong->__bpm - 1*mult );
		}
		AudioEngine::get_instance()->unlock();

		return true;
	}

	if( sActionString == ">>_NEXT_BAR"){
		pEngine->setPatternPos(pEngine->getPatternPos() +1 );
		pEngine->setTimelineBpm();
		return true;
	}

	if( sActionString == "<<_PREVIOUS_BAR"){
		pEngine->setPatternPos(pEngine->getPatternPos() -1 );
		pEngine->setTimelineBpm();
		return true;
	}

	if( sActionString == "PLAYLIST_SONG"){
		bool ok;
		int songnumber = pAction->getParameter1().toInt(&ok,10);
		return setSong( songnumber );
	}

	if( sActionString == "PLAYLIST_NEXT_SONG"){
		int songnumber = Playlist::get_instance()->getActiveSongNumber();
		return setSong( ++songnumber );
	}

	if( sActionString == "PLAYLIST_PREV_SONG"){
		int songnumber = Playlist::get_instance()->getActiveSongNumber();
		return setSong( --songnumber );
	}

	if( sActionString == "RECORD_READY"){
		if ( pEngine->getState() != STATE_PLAYING ) {
			if (!Preferences::get_instance()->getRecordEvents()) {
				Preferences::get_instance()->setRecordEvents(true);
			}
			else {
				Preferences::get_instance()->setRecordEvents(false);
			}
		}
		return true;
	}
	if( sActionString == "RECORD/STROBE_TOGGLE"){
		if (!Preferences::get_instance()->getRecordEvents()) {
			Preferences::get_instance()->setRecordEvents(true);
		}
		else {
			Preferences::get_instance()->setRecordEvents(false);
		}
		return true;
	}

	if( sActionString == "RECORD_STROBE"){

		if (!Preferences::get_instance()->getRecordEvents()) {
			Preferences::get_instance()->setRecordEvents(true);
		}
		return true;
	}

	if( sActionString == "RECORD_EXIT"){

		if (Preferences::get_instance()->getRecordEvents()) {
			Preferences::get_instance()->setRecordEvents(false);
		}
		return true;
	}

	if( sActionString == "TOGGLE_METRONOME"){

		Preferences::get_instance()->m_bUseMetronome = !Preferences::get_instance()->m_bUseMetronome;
		return true;
	}

	if( sActionString == "UNDO_ACTION"){
		EventQueue::get_instance()->push_event( EVENT_UNDO_REDO, 0);// 0 = undo
		return true;
	}

	if( sActionString == "REDO_ACTION"){
		EventQueue::get_instance()->push_event( EVENT_UNDO_REDO, 1);// 1 = redo
		return true;
	}
	
	 // hack
	if( sActionString == "BPM_CC_ABSOLUTE" ){
		AudioEngine::get_instance()->lock( RIGHT_HERE );
		
		int cc_param = 1;

		//this Action should be triggered only by CC commands

		bool ok;
		cc_param = pAction->getParameter2().toInt(&ok,10);
		
		int min_bpm = 40;
		int max_bpm = 200;
		
		int curr = linear_trans (min_bpm, max_bpm, 0, 127, cc_param);
		pEngine->setBPM(curr);
		
		// log bpm
		ofstream myfile;
		myfile.open ("bpm-log.txt");
		myfile << curr;
		myfile.close();
		
		m_nLastBpmChangeCCParameter = cc_param;

		AudioEngine::get_instance()->unlock();

		return true;
	}
	// Hack: change drum mode
	if( sActionString == "DRUM_MODE"){
		drum_mode = 1;
		return false;
	}
	
	if( sActionString == "LOOP_MODE"){
		drum_mode = 0;
		return false;
	}
	
	if( sActionString == "FX_MODE"){
		drum_mode = 0;
		return false;
	}
	
	// hack
	if (sActionString == "LOAD_NEXT_DRUMKIT")
	{
		if (drum_mode == 1)
		{
			bool ok;
			if ( pAction->getParameter2().toInt(&ok,10) == 127 )
			{
				if ( current_drumkit + 1 < drumkit_info_list.size() )
				{
					current_drumkit++;
					
					AudioEngine::get_instance()->lock( RIGHT_HERE );
					pEngine->loadDrumkit ( drumkit_info_list[current_drumkit] );
					AudioEngine::get_instance()->unlock();
					
					return true;
				}
			}
		}
		
		return false;
	}
	
	if (sActionString == "LOAD_PREV_DRUMKIT")
	{
		if (drum_mode == 1)
		{
			bool ok;
			if ( pAction->getParameter2().toInt(&ok,10) == 127 )
			{
				if ( current_drumkit - 1 >= 0 )
				{
					current_drumkit--;
					AudioEngine::get_instance()->lock( RIGHT_HERE );
					pEngine->loadDrumkit ( drumkit_info_list[current_drumkit] );
					AudioEngine::get_instance()->unlock();
					return true;
				}
			}
		}
		
		return false;
	}
	
	// hack
	/*
	if (drum_mode == 1)
	{
		for (int i=1; i<=25; i++)
		{
			string currActionString = string ("LOAD_SONG_") + to_string (i);
			if( sActionString.toStdString() == currActionString)
			{
				bool ok;
				if ( pAction->getParameter2().toInt(&ok,10) == 127 )
				{
					int nState = pEngine->getState();
					bool setsong = setSong(i - 1);
					return true;
				}
			}
		}
	}*/
	
	return false;
}
