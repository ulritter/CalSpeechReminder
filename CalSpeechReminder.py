#!/usr/bin/python
#==========================================================
# This script reads the content of a Google Calendar 
# and gives meeting alerts by reading them via 
# text-to-speech (tts)
#
# used this to remind my son of upcoming home schooling 
# video events, hence also the camera code :-)
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
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
#
#==========================================================
#========= begin customization section ====================
#==========================================================
#
status_output = True
language = 'de'
# operation system command to clear screen
str_clear = 'clear'
# strings for tts and console output
str_begins = 'beginnt in'
str_minutes = 'Minuten'
str_one_minute = 'einer Minute'
str_no_event = 'Keine bevorstehende Ereignisse gefunden'
str_reloaded = 'Ereignisse neu geladen um'
str_iteration = 'Iteration:'
str_divider = '==================================================================='
# StarTrek Transporter sound on startup - just for fun
str_initial_sound_file = './transporter.mp3'
# theater gong :-)
str_alert_sound_file = './gong.mp3'
# temp file for generated tts sound
str_tts_sound_file = './speech.mp3'
camera_present = True
str_take_picture = 'fswebcam -r 1280x720 image2.jpg >/dev/null 2>&1'
# countdown minutes
first_gong_time = 5
second_gong_time = 1
# get next n google calendar events beginning from now
# could also be less since we re-read the calender in a
# rolling process
number_events = 10
# refresh timer
refresh_timer = 10
#
#==========================================================
#========= end customization section ======================
#==========================================================
#


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

    print('Getting the upcoming ',number_events,' events')
    events_result = service.events().list(calendarId='primary', timeMin=startlooking,
                                        maxResults=number_events, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])
    return (events)

#rhp-custom function to supress output while playing mp3 files
def _play_with_ffplay_suppress(seg):
	PLAYER = get_player_name()
	with tempfile.NamedTemporaryFile("w+b", suffix=".mp3") as f:
		seg.export(f.name, "mp3")
		devnull = open(os.devnull, 'w')
		subprocess.call([PLAYER,"-nodisp", "-autoexit", "-hide_banner", f.name],stdout=devnull, stderr=devnull)
        
        
# text-to-speech output of a given character strimg
def speak(speak_text,speak_lang,gong):
	tts = gTTS(text = speak_text, lang = speak_lang, slow = False)
	tts.save(str_tts_sound_file)
	if gong:
		music = AudioSegment.from_mp3(str_alert_sound_file)
		_play_with_ffplay_suppress(music)
	music = AudioSegment.from_mp3(str_tts_sound_file)
	_play_with_ffplay_suppress(music)

def clearscreen():
	os.system(str_clear)

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
	#
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

			# alert via sound & text-to-speech 
			if timeDiff == first_gong_time:
				speak(summary + str_begins + str(timeDiff) + str_minutes,language, True)
			elif timeDiff == second_gong_time:
				speak(summary + str_begins + str_one_minute,language, True)

		# take a snapshot if camera present
		if camera_present:
			os.system (str_take_picture)
			
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