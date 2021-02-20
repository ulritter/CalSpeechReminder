#!/usr/bin/python
# -*- coding: utf-8 -*-
#==========================================================
# This script reads the content of a Google Calendar 
# and gives meeting alerts by reading them via 
# text-to-speech (tts)
# 
# This was originally built to run on a Raspberry Pi using 
# Python 2.7 but may equally be able to run on any other 
# system with the necessary adaptions like the operating 
# system commands etc.
#
# Program exit via console ^C in this version
#
# (c) ulritter, 2021, GPL License 3.0
#==========================================================
#
# TODO: sound subdirectory
# TODO: better screen output
# TODO: run as a daemon
# TODO: better exit
#
from __future__ import print_function
from pathlib import Path
import datetime
import pickle
import os
import os.path
import sys, getopt
import urllib3
import time
import threading
import platform
from datetime import date
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from pydub.utils import get_player_name
import tempfile
import subprocess
import dateutil
import dateutil.parser
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
#
#============================================================
#========= begin customization section          =============
#========= define defaults als global variables =============
#========= read config file "prefs.json" ,      =============
#========= in case of read fail use defaults    =============
#============================================================
#
def LoadDefaultLanguage():
	global language
	global str_lookahead
	global str_begins
	global str_minutes 
	global str_one_minute
	global str_no_event
	global str_reloaded 
	global str_stints
	global str_iteration
	global str_upcoming
	global str_events
	global str_on
	global str_nodir
	global str_wrongdir
	
	language = 'en'
	str_lookahead = 'Maximum number of events in preview: '
	str_begins = 'begins in'
	str_minutes = 'minutes'
	str_one_minute = 'one minute'
	str_no_event = 'No upcoming events found'
	str_reloaded = 'Events last reloaded at'
	str_on = 'on'
	str_stints ='Passes: '
	str_iteration = 'Minutes in pass:'
	str_upcoming = 'Getting the next '
	str_events = ' events ...'
	str_nodir =  'does not exist or is not a directory'
	str_wrongdir =  'is the wrong directory'

def LoadDefaults():
	global status_output
	global alert_sound
	global str_divider
	global str_initial_sound_file
	global str_alert_sound_file
	global str_tts_sound_file
	global alerts
	global number_events
	global refresh_timer
	global status_output

	LoadDefaultLanguage()
	# operation system command to clear screen
	status_output = True
	str_divider = '==================================================================='
	# StarTrek Transporter sound on startup - just for fun
	str_initial_sound_file = 'transporter.mp3'
	#theater gong :-)
	str_alert_sound_file = 'gong.mp3'
	# temp file for generated tts sound
	str_tts_sound_file = 'speech.mp3'
	# countdown delta minutes to trigger alert messages
	alerts = [1,5,10]
	# get next n google calendar events beginning from now
	# could also be less since we re-read the calender in a
	# rolling process
	number_events = 10
	# refresh time
	refresh_timer = 10
	# decides whether we play a sound (loke gong etc.) before we speak the string
	alert_sound = True	

class LangNotFound(Exception):
	pass
	
def get_prefs(prefs_file):
	global status_output
	global alert_sound
	global str_divider
	global str_initial_sound_file
	global str_alert_sound_file
	global str_tts_sound_file
	global alerts
	global number_events
	global refresh_timer
	global status_output
	global language
	global str_lookahead
	global str_begins
	global str_minutes 
	global str_one_minute
	global str_no_event
	global str_reloaded 
	global str_stints
	global str_iteration
	global str_upcoming
	global str_events
	global str_on
	global str_nodir
	global str_wrongdir	

	
	try:
		with open(prefs_file) as f:
			try:
				prefs = json.load(f)
				if prefs['status_output'] == 'on':
					status_output = True
				else:
					status_output = False
				
				if prefs['str_alert_sound'] == 'on':
					alert_sound = True
				else:
					alert_sound = False
				
				language = prefs['language']
				str_divider = prefs['str_divider']
				str_initial_sound_file = prefs['str_initial_sound_file']
				str_alert_sound_file = prefs['str_alert_sound_file']
				str_tts_sound_file = prefs['str_tts_sound_file']
				number_events = int(prefs['number_events'])
				refresh_timer = int(prefs['refresh_timer'])
			
				alerts=[]
				for alert in prefs['alerts']:
					alerts.append(int(alert['alert_time']))
				
				language_found = False
				for _locale in prefs['locales']:
					if _locale['lang'] == language:
						language_found = True
						str_lookahead = _locale['str_lookahead']
						str_begins = _locale['str_begins']
						str_minutes = _locale['str_minutes']
						str_one_minute = _locale['str_one_minute']
						str_no_event = _locale['str_no_event']
						str_reloaded = _locale['str_reloaded']
						str_on = _locale['str_on']
						str_stints = _locale['str_stints']
						str_iteration = _locale['str_iteration']
						str_upcoming = _locale['str_upcoming']
						str_events = _locale['str_events']
						str_nodir = _locale['str_nodir']
						str_wrongdir = _locale['str_wrongdir']
					
				# if the prefs.json "language" entry is not matched by any of the translations
				# fill default language entries 		
				if not language_found:
					print('Language ', language,' not found. Still starting, but with defaults ...')
					time.sleep(5)
					LoadDefaultLanguage()
				
			# fill defaults in case of any json parsing issue (delimiter missing, etc)			
			except (ValueError, KeyError) as jerr:
				print('Value or Key Error: Please check prefs file. Still starting, but with defaults ...:', jerr)
				time.sleep(5)
				LoadDefaults()
				
	except (EnvironmentError) as jerr:
		print('Environment error. Please check prefs file. Still starting, but with defaults ...:', jerr)
		timr.sleep(5)
		LoadDefaults()
	
#
#============================================================
#========= end customization section ========================
#============================================================
#

def clearscreen():
	os.system(str_clear)

def get_events(number_events):
	# code snippet from Google Developer website: https://developers.google.com/calendar/quickstart/python
	# the website also includes instructions on how to set up the integration
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(filepath+'.'+path_delim+'token.pickle'):
        with open(filepath+'.'+path_delim+'token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    startlooking = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    	
    events_result = service.events().list(calendarId='primary', timeMin=startlooking,
                                        maxResults=number_events, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])
    return (events)

# function to supress output while playing mp3 files
# modified clone of original pydub code
def _play_with_ffplay_suppress(seg):
	PLAYER = get_player_name()
	# create temporary mp3 file for audio output since "with NamedTemporaryFile("w+b", suffix=".mp3") as f:"
	# as used in original pydub code comes up with double back slash errors in Windows
	if os.path.exists(filepath+'.'+path_delim):
		with open(filepath+'.'+path_delim+'tmp.mp3', 'wb') as f:
			seg.export(f.name, "mp3")
			devnull = open(os.devnull, 'w')
			subprocess.call([PLAYER,"-nodisp", "-autoexit", "-hide_banner", f.name],stdout=devnull, stderr=devnull) 

        
# text-to-speech output of a given character string
def speak(speak_text,speak_lang,alert_sound):
	# convert string to speech
	tts = gTTS(text = speak_text, lang = speak_lang, slow = False)
	tts.save(filepath+str_tts_sound_file)
	# build output sound file
	music = AudioSegment.empty()
	if alert_sound:
		# if there is a gong or alike (prefs.json) defined then add the sound to the output
		music += AudioSegment.from_mp3(filepath+str_alert_sound_file)
	# add converted string	
	music += AudioSegment.from_mp3(filepath+str_tts_sound_file)
	# crank it out ...
	_play_with_ffplay_suppress(music)


def main(argv):
	# operating system specific settings
	global path_delim
	global str_clear
	if platform.system() == 'Windows':
		path_delim = '\\'
		str_clear = 'cls'
	else:
		path_delim = '/'
		str_clear = 'clear'
	
	global filepath
	filepath = ''
	
	#just to have some strings in place
	LoadDefaults()

	# if argument given we expect help as argument or the working directory as an option
	if len(sys.argv) > 1:
		try:
			opts, args = getopt.getopt(argv,"hd:",["dir="])
		except getopt.GetoptError:
			print ('Usage: ', str(sys.argv[0]), '-d <base directory> ')
			sys.exit(2)
		for opt, arg in opts:
			if opt in ("-h", "--help"):
				print (os.path.basename(str(sys.argv[0])),'-d <base directory>')
				sys.exit()
			elif opt in ("-d", "--dir"):
				filepath = arg+path_delim
		
		if not Path(filepath).is_dir():
			print (filepath, str_nodir)
			sys.exit(2)
		elif not Path(filepath+path_delim+'prefs.json').is_file():
			print (filepath, str_wrongdir)
			sys.exit(2)
				
	prefsfile = filepath+'.'+path_delim+'prefs.json'			
	get_prefs(prefsfile)

	# disable warnings we might get from text to speech module
	urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
	# 
	#
	if status_output:
		clearscreen()
		music = AudioSegment.from_mp3(filepath+str_initial_sound_file)

		threading.Thread(target=_play_with_ffplay_suppress, args=(music,)).start()
		# code without threading:
		#_play_with_ffplay_suppress(music)
	#
	events = get_events(number_events)
	#reset counter 
	counter = 0
	stints = 1

	#
	last = dateutil.parser.parse(datetime.datetime.now().isoformat())
    
  #endless loop, waiting for keyboard interrupt
	while True:
    # we need to be able to subtract the time stamps, hence we need to force both to the same format	
		now = dateutil.parser.parse(datetime.datetime.now().isoformat())

		if status_output:
			clearscreen()
			print(str_lookahead, number_events)
			print(str_divider)
			if not events :
				print(str_no_event)

		#
		# go through our event list
		# it is somewhat redundant to scan the entire list if the parameters "number_events" and "refresh_timer"
		# create a too wide angle, but it leaves more control via parameters this way and the code is simpler
		#
		for event in events:
			# get the event start time
			start = event['start'].get('dateTime')
			
			# get event description
			summary = event.get('summary')
			
			# we need to be able to subtract the time stamps, hence we need to force naive (time zone un-aware) representation
			dtu = dateutil.parser.parse(start).replace(tzinfo=None)
			
			# time difference between now and event in minutes
			timeDiff=int(((dtu-now).total_seconds())/60)
			
			if status_output:
				print(summary, ' ', str_begins,' ', timeDiff,str_minutes)

			# if we have hit one of the alert times alert via sound & text-to-speech 
			for alert_time in alerts:
				if timeDiff == alert_time:
					if timeDiff == 1:
						threading.Thread(target=speak, args=(summary + str_begins + str_one_minute,language,alert_sound)).start()
						# code without threading:
						#speak(summary + str_begins + str_one_minute,language, alert_sound)
					else:
						threading.Thread(target=speak, args=(summary + str_begins + str(timeDiff) + str_minutes,language,alert_sound)).start()
						# code without threading:
						#speak(summary + str_begins + str(timeDiff) + str_minutes,language, alert_sound)

		if status_output:
			print(str_divider)
			print(str_iteration,' ',counter+1,'   ', str_stints, stints)
			print(str_reloaded,' ', last.strftime("%H:%M:%S"),str_on,last.strftime("%d-%b-%Y"))
			
		time.sleep(60)
		
		# reload calendar every refresh_timer minutes  
		counter = counter + 1  	
		if counter >=	 (refresh_timer):
			events = get_events(number_events)
			counter = 0
			stints = stints + 1
			last = now  	
    
if __name__ == '__main__':
    main(sys.argv[1:])