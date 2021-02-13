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
# todo: sound subdirectory, better screen output, run as a daemon
#
from __future__ import print_function
import datetime
import pickle
import os
import os.path
import urllib3
import time
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
	global str_begins
	global str_minutes 
	global str_one_minute
	global str_no_event
	global str_reloaded 
	global str_iteration
	global str_upcoming
	global str_events
	language = 'en'
	str_begins = 'begins in'
	str_minutes = 'minutes'
	str_one_minute = 'one minute'
	str_no_event = 'No upcoming events found'
	str_reloaded = 'Events reloaded at'
	str_iteration = 'Iteration:'
	str_upcoming = 'Getting the next '
	str_events = ' events ...'

def LoadDefaults():
	global status_output
	global str_clear
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
	status_output = Truex
	str_clear = 'clear'
	str_divider = '==================================================================='
	# StarTrek Transporter sound on startup - just for fun
	str_initial_sound_file = './transporter.mp3'
	#theater gong :-)
	str_alert_sound_file = './gong.mp3'
	# temp file for generated tts sound
	str_tts_sound_file = './speech.mp3'
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
	
try:
	with open('prefs.json') as f:
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
			str_clear = prefs['str_clear']
			str_divider = prefs['str_divider']
			str_initial_sound_file = prefs['str_initial_sound_file']
			str_alert_sound_file = prefs['str_alert_sound_file']
			str_tts_sound_file = prefs['str_tts_sound_file']
			str_clear = prefs['str_clear']
			number_events = int(prefs['number_events'])
			refresh_timer = int(prefs['refresh_timer'])
			alerts=[]
			for alert in prefs['alerts']:
				alerts.append(int(alert['alert_time']))
			language_found = False
			for locale in prefs['locales']:
				if locale['lang'] == language:
					language_found = True
					str_begins = locale['str_begins']
					str_minutes = locale['str_minutes']
					str_one_minute = locale['str_one_minute']
					str_no_event = locale['str_no_event']
					str_reloaded = locale['str_reloaded']
					str_iteration = locale['str_iteration']
					str_upcoming = locale['str_upcoming']
					str_events = locale['str_events']
					
			# if the prefs.json "language" entry is not matched by any of the translations
			# raise an exception
			if not language_found:
				raise LangNotFound()
				
		# fill defaults in case of any json parsing issue (delimiter missing, etc)			
		except ValueError:
			LoadDefaults()
			
# fill default language entries in case we have no match for language in the prefs file			
except LangNotFound:
	LoadDefaultLanguage() 
	
# fill defaults in case we have probelems reaading the prefs file	
except EnvironmentError: 
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
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
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

    if status_output:
    	clearscreen()
    	print(str_upcoming,number_events,str_events)
    	time.sleep(3)
    events_result = service.events().list(calendarId='primary', timeMin=startlooking,
                                        maxResults=number_events, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])
    return (events)

# function to supress output while playing mp3 files
def _play_with_ffplay_suppress(seg):
	PLAYER = get_player_name()
	with tempfile.NamedTemporaryFile("w+b", suffix=".mp3") as f:
		seg.export(f.name, "mp3")
		devnull = open(os.devnull, 'w')
		subprocess.call([PLAYER,"-nodisp", "-autoexit", "-hide_banner", f.name],stdout=devnull, stderr=devnull)   
        
# text-to-speech output of a given character strimg
def speak(speak_text,speak_lang,alert_sound):
	tts = gTTS(text = speak_text, lang = speak_lang, slow = False)
	tts.save(str_tts_sound_file)
	if alert_sound:
		music = AudioSegment.from_mp3(str_alert_sound_file)
		_play_with_ffplay_suppress(music)
	music = AudioSegment.from_mp3(str_tts_sound_file)
	_play_with_ffplay_suppress(music)


def main():
	# disable warnings we might get from text to speech module
	urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
	# set language and text snippets for text to speech
	#
	if status_output:
		clearscreen()
		music = AudioSegment.from_mp3(str_initial_sound_file)
		_play_with_ffplay_suppress(music)

	#
	events = get_events(number_events)
	#reset counter 
	counter = 0

	#
	last = dateutil.parser.parse(datetime.datetime.now().isoformat())
    
  #endless loop, waiting for keyboard interrupt or empty calendar
	while True:
    # we need to be able to subtract the time stamps, hence we need to force both to the same format	
		now = dateutil.parser.parse(datetime.datetime.now().isoformat())
		
		if not events and status_output:
			clearscreen()
			print(str_no_event)
			break
			
		if status_output:
				clearscreen()
				print(str_divider)
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
			
			# time differnce between now and event in minutes
			timeDiff=int(((dtu-now).total_seconds())/60)
			
			if status_output:
				print(summary, ' ', str_begins,' ', timeDiff,str_minutes)

			# if we have hit one of the alert times alert via sound & text-to-speech 
			for alert_time in alerts:
				if timeDiff == alert_time:
					speak(summary + str_begins + str(timeDiff) + str_minutes,language, alert_sound)

		# reload calendar every refresh_timer minutes  
		counter = counter + 1  	
		if counter > (refresh_timer - 1):
			events = get_events(number_events)
			counter = 0
			last = now  	
				
		if status_output:
			print(str_divider)
			print(str_iteration,' ',counter,' ',str_reloaded,' ', last)
				
		time.sleep(60)
	 
        
if __name__ == '__main__':
    main()