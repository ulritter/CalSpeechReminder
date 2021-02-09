#!/usr/bin/python
# This script reads the content of a Google Calendar 
# and gives meeting alerts by reading them via text-to-speech
#
from __future__ import print_function
import datetime
import pickle
import os.path
import urllib3
import time
from datetime import date
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import dateutil
import dateutil.parser
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


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
    # startlooking = datetime.datetime.now()
    print('Getting the upcoming ',number_events,' events')
    events_result = service.events().list(calendarId='primary', timeMin=startlooking,
                                        maxResults=number_events, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])
    
    return (events)


def speak(speak_text,speak_lang):
	# text-to-speech  the strimg
	tts = gTTS(text = speak_text, lang = speak_lang, slow = False)
	tts.save("speech.mp3")
	music = AudioSegment.from_mp3('./gong.mp3')
	play(music)
	music = AudioSegment.from_mp3('./speech.mp3')
	play(music)


def main():
	monitor = True
	camera_present = True
	
	# disable warnings we might get from text to speech module
	urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
	# set language and text snippets for text to speech
	language = 'de'
	str_begins = 'beginnt in'
	str_minutes = 'Minuten'
	str_one_minute = 'einer Minute'
	# get next n google calendar events beginning from now 
	n = 20
	events = get_events(n)
	#reset counter 
	counter = 0
	# refresh timer
	refresh_timer = 10
	last = dateutil.parser.parse(datetime.datetime.now().isoformat())
    
  #endless loop, waiting for keyboard interrupt or empty calendar
	while True:
    # we need to be able to subtract the time stamps, hence we need to force both to the same format	
		now = dateutil.parser.parse(datetime.datetime.now().isoformat())
		
		if not events:
			print('No upcoming events found.')
			break
			
		if monitor:
				os.system('clear')
				print('====================================================')
		# go through our event list
		for event in events:
			# get the event's start time
			start = event['start'].get('dateTime')
			
			# get event description
			summary = event.get('summary')
			
			# we need to be able to subtract the time stamps, hence we need to force naive (time zone un-aware) representation
			dtu = dateutil.parser.parse(start).replace(tzinfo=None)
			
			# time differnce between now and event in minutes
			timeDiff=int(((dtu-now).total_seconds())/60)
			
			if monitor:
				print(summary, ' ', str_begins,' ', timeDiff,str_minutes)

			# alert via sound output 
			if (timeDiff > 1) and (timeDiff == 5):
				speak(summary + str_begins + str(timeDiff) + str_minutes,language)
			elif (timeDiff <= 1) and (timeDiff > 0):
				speak(summary + str_begins + str_one_minute,language)

		# take a snapshot if camera present
		if camera_present:
			os.system ('fswebcam -r 1280x720 image2.jpg >/dev/null 2>&1')
			
		# reload calendar every refresh_timer  minutes  
		counter = counter + 1  	
		if counter > (refresh_timer - 1):
			events = get_events(n)
			counter = 0
			last = now  	
				
		if monitor:
				print('====================================================')
				print('Events reloaded at', last)
				
		time.sleep(60)
	 
        
if __name__ == '__main__':
    main()