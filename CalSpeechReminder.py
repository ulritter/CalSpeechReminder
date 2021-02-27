##!/usr/bin/env python
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
# Program exit via console ^C or exit character specified
# in prefs.json
#
# (c) ulritter, 2021, GPL License 3.0
#==========================================================
#
# TODO: sound subdirectory
# TODO: better screen output
# TODO: run as a daemon
# TODO: include logging
# TODO: move global variables to classes
# TODO: reload prefs file
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
import locale
import threading
from threading import Event
import platform
from datetime import date
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from pydub.utils import get_player_name
import tempfile
import signal
import subprocess
import dateutil
import dateutil.parser
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

global exit
exit = Event()

# Code for getting keyboard input in a non-blocking way
global isWindows

isWindows = False
try:
    from win32api import STD_INPUT_HANDLE
    from win32console import GetStdHandle, KEY_EVENT, ENABLE_ECHO_INPUT, ENABLE_LINE_INPUT, ENABLE_PROCESSED_INPUT
    isWindows = True
except ImportError as e:
    import sys
    import select
    import termios

#
#============================================================
#========= begin customization section          =============
#========= define defaults als global variables =============
#========= read config file "prefs.json" ,      =============
#========= in case of read fail use defaults    =============
#============================================================

#============================================================
def load_default_language():
    """Populate language specific variables with the default strings"""
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
    global str_signal
    global str_exit_msg
  
    language = 'en_US'
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
    str_wrongdir =    'is the wrong directory'
    str_signal = 'Exiting after signal: '
    str_exit_msg = 'One of the following keys terminates the program: '

#
#============================================================
def load_defaults():
    """Populate variable with the default values"""
    global status_output
    global silence_file
    global alert_sound
    global str_divider
    global str_initial_sound_file
    global str_alert_sound_file
    global str_tts_sound_file
    global str_play_sound_file
    global alerts
    global number_events
    global refresh_timer
    global status_output
    global str_exit_chars

    load_default_language()
    # operation system command to clear screen
    status_output = True
    silence_file = ''
    str_exit_chars = 'xXqQ'
    str_divider = '==================================================================='
    # StarTrek Transporter sound on startup - just for fun
    str_initial_sound_file = 'transporter.mp3'
    #theater gong :-)
    str_alert_sound_file = 'gong.mp3'
    # temp file for generated tts sound
    str_tts_sound_file = '_stmp.mp3'
    str_play_sound_file = '_tmp.mp3'
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

#
#============================================================ 
def get_prefs(prefs_file):
    """Load preferences and localized strings from prefs.json"""
    global status_output
    global alert_sound
    global str_divider
    global str_initial_sound_file
    global str_alert_sound_file
    global str_tts_sound_file
    global str_play_sound_file
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
    global str_exit_chars 
    global str_signal
    global str_exit_msg
    global silence_file
    
    try:
        with open(prefs_file) as f:
            try:
                _prefs = json.load(f)
                if _prefs['status_output'] == 'on':
                    status_output = True
                else:
                    status_output = False
                
                if _prefs['str_alert_sound'] == 'on':
                    alert_sound = True
                else:
                    alert_sound = False
                silence_file = _prefs['silence_file']
                language = _prefs['language']
                str_exit_chars = _prefs['str_exit_chars']
                str_divider = _prefs['str_divider']
                str_initial_sound_file = _prefs['str_initial_sound_file']
                str_alert_sound_file = _prefs['str_alert_sound_file']
                str_tts_sound_file = _prefs['str_tts_sound_file']
                str_play_sound_file = _prefs['str_play_sound_file']
                number_events = int(_prefs['number_events'])
                refresh_timer = int(_prefs['refresh_timer'])
            
                alerts=[]
                for alert in _prefs['alerts']:
                    alerts.append(int(alert['alert_time']))
                
                _language_found = False
                for _locale in _prefs['locales']:
                    if _locale['lang'] == language:
                        _language_found = True
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
                        str_signal = _locale['str_signal']
                        str_exit_msg = _locale['str_exit_msg']
                    
                # if the prefs.json "language" entry is not matched by any of the translations
                # fill default language entries         
                if not _language_found:
                    print('Language ', language,' not found. Still starting, but with defaults ...')
                    time.sleep(5)
                    load_default_language()
                
            # fill defaults in case of any json parsing issue (delimiter missing, etc)            
            except (ValueError, KeyError) as jerr:
                print('Value or Key Error: Please check prefs file. Still starting, but with defaults ...:', jerr)
                time.sleep(5)
                load_defaults()
                
    except (EnvironmentError) as jerr:
        print('Environment error. Please check prefs file. Still starting, but with defaults ...:', jerr)
        time.sleep(5)
        load_defaults()
    
#
#============================================================
#========= end customization section ========================
#============================================================
#

#============================================================
class key_poller():
    """Non-blocking poll for key strokes in either Windows of Linux environments"""
    def __enter__(self):
        global isWindows
        if isWindows:
            self.readHandle = GetStdHandle(STD_INPUT_HANDLE)
            self.readHandle.SetConsoleMode(ENABLE_LINE_INPUT|ENABLE_ECHO_INPUT|ENABLE_PROCESSED_INPUT)
            self.curEventLength = 0
            self.curKeysLength = 0

            self.capturedChars = []
        else:
            # Save the terminal settings
            self.fd = sys.stdin.fileno()
            self.new_term = termios.tcgetattr(self.fd)
            self.old_term = termios.tcgetattr(self.fd)

            # New terminal setting unbuffered
            self.new_term[3] = (self.new_term[3] & ~termios.ICANON & ~termios.ECHO)
            termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.new_term)

        return self

    def __exit__(self, type, value, traceback):
        if isWindows:
            pass
        else:
            termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old_term)

    def poll(self):
        if isWindows:
            if not len(self.capturedChars) == 0:
                return self.capturedChars.pop(0)

            eventsPeek = self.readHandle.PeekConsoleInput(10000)

            if len(eventsPeek) == 0:
                return None

            if not len(eventsPeek) == self.curEventLength:
                for curEvent in eventsPeek[self.curEventLength:]:
                    if curEvent.EventType == KEY_EVENT:
                        if ord(curEvent.Char) == 0 or not curEvent.KeyDown:
                            pass
                        else:
                            curChar = str(curEvent.Char)
                            self.capturedChars.append(curChar)
                self.curEventLength = len(eventsPeek)

            if not len(self.capturedChars) == 0:
                return self.capturedChars.pop(0)
            else:
                return None
        else:
            dr,dw,de = select.select([sys.stdin], [], [], 0)
            if not dr == []:
                return sys.stdin.read(1)
            return None

#
#============================================================
# Clear the console screen
#============================================================
def clear_screen():
    os.system(str_clear)

#
#============================================================
# Load events from Google Calendar
#============================================================
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
        
#
#============================================================

def _play_with_ffplay_suppress(seg):
    """ Play mp3 files without console output
    modified clone of original pydub code"""
    PLAYER = get_player_name()
    # create temporary mp3 file for audio output since "with NamedTemporaryFile("w+b", suffix=".mp3") as f:"
    # as used in original pydub code comes up with double back slash errors in Windows
    if os.path.exists(filepath+'.'+path_delim):
        with open(filepath+'.'+path_delim+str_play_sound_file, 'wb') as f:
            seg.export(f.name, "mp3")
            devnull = open(os.devnull, 'w')
            subprocess.call([PLAYER, "-nodisp", "-autoexit", "-hide_banner", f.name], stdout=devnull, stderr=devnull)

#
#============================================================                
def speak_string(speak_text, speak_lang, alert_sound):
    """ Convert text to speech and trigger audio output
    with optional leading alert sound (gong etc)"""
    
    _tts = gTTS(text = speak_text, lang = speak_lang, slow = False)
    _tts.save(filepath+str_tts_sound_file)
    # build output sound file
    _sound_segment = AudioSegment.empty()

    # add silence to the beginning, might be needed in same scenarios with sound output via HDMI
    # controlled by "silence_file" entry in prefs.json
    if os.path.isfile(filepath+silence_file):
        _sound_segment += AudioSegment.from_mp3(filepath+silence_file)
        
    if alert_sound:
        # if there is a gong or alike (prefs.json) defined then add the sound to the output
        _sound_segment += AudioSegment.from_mp3(filepath+str_alert_sound_file)
    # add converted string    
    _sound_segment += AudioSegment.from_mp3(filepath+str_tts_sound_file)
    # crank it out ...
    _play_with_ffplay_suppress(_sound_segment)


#
#============================================================
def check_keyboard_input(exit):
    """check console input and flag event if exit character was 
    pressed - supposed to be invoked as thread"""
    with key_poller() as _keyPoller:
        while not exit.is_set():
            _c = _keyPoller.poll()
            if not _c is None:
                if _c in str_exit_chars:
                    # quit condition
                    wrapup_and_quit()
            exit.wait(0.5)

#
#============================================================
def print_usage():
    """Print Usage message"""
    print('Usage:')
    print(os.path.basename(str(sys.argv[0])), ' or')
    print(os.path.basename(str(sys.argv[0])), '[-h|--help] or ')
    print(os.path.basename(str(sys.argv[0])), '[[-d|--dir <base directory>]')
#
#============================================================
def main(argv):
    """main function with evaluation of input parameters
    and main loop"""
		
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
    load_defaults()

    # TODO: input parameters evauation as function
    # if argument given we expect help as argument or the working directory as an option
    if len(sys.argv) > 1:
        # TODO: Better help texts
        try:
            opts, args = getopt.getopt(argv, "hd:", ["help", "dir="])
        except getopt.GetoptError:
            print_usage()
            sys.exit(2)
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print_usage()
                sys.exit()
            elif opt in ("-d", "--dir"):
                filepath = arg+path_delim
        
        if not Path(filepath).is_dir():
            print (filepath, str_nodir)
            sys.exit(2)
        elif not Path(filepath+path_delim+'prefs.json').is_file():
            print (filepath, str_wrongdir)
            sys.exit(2)
                
    # load preferences from prefs.json
    prefsfile = filepath+'.'+path_delim+'prefs.json'            
    get_prefs(prefsfile)

    locale.setlocale(locale.LC_TIME, language+'.utf-8')
    # disable warnings we might get from text to speech module
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    # 
    #
    if status_output:
        clear_screen()
        music = AudioSegment.empty()
    
        # add silence to the beginning, might be needed in same scenarios with sound output via HDMI
        if os.path.isfile(filepath+silence_file):
            music += AudioSegment.from_mp3(filepath+silence_file)
            
        music += AudioSegment.from_mp3(filepath+str_initial_sound_file)
        threading.Thread(target=_play_with_ffplay_suppress, args=(music,)).start()
    #
    events = get_events(number_events)

    counter = 0
    stints = 1

    #
    last = dateutil.parser.parse(datetime.datetime.now().isoformat())

    # start thread to check keyboard input in background
    threading.Thread(target=check_keyboard_input, args=(exit,)).start()
    
    # loop, waiting for keyboard interrupt or exit character pressed
    while not exit.is_set():

        # we need to be able to subtract the time stamps, hence we need to force both to the same format    
        now = dateutil.parser.parse(datetime.datetime.now().isoformat())

        if status_output:
            clear_screen()
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

            # Once we have encountered one of the alert times, play alert via sound & text-to-speech 
            for alert_time in alerts:
                if timeDiff == alert_time:
                    if timeDiff == 1:
                        #"language" is a 5 character locale string like "en_US". Text-to-speech only needs e.g."en", so we do 
                        # language[:2] to get the firsdt two characters
                        threading.Thread(target=speak_string, args=(summary + str_begins + str_one_minute, language[:2], alert_sound)).start()
                    else:
                        threading.Thread(target=speak_string, args=(summary + str_begins + str(timeDiff) + str_minutes, language[:2], alert_sound)).start()

        if status_output:
            print(str_divider)
            print(str_iteration,' ',counter+1,'     ', str_stints, stints)

            print(str_reloaded,' ', last.strftime("%H:%M:%S %a, %d-%b-%Y"))
            print(str_exit_msg, str_exit_chars)
            
        # wait a minute or exit if event is set
        exit.wait(60)
        
        # reload calendar every refresh_timer minutes    
        counter = counter + 1     
        if counter >=    (refresh_timer):
            events = get_events(number_events)
            counter = 0
            stints = stints + 1
            last = now   
                 
#
#============================================================             
def wrapup_and_quit():
    """remove temp files and set exit flag"""
    global filepath
    if filepath == '':
        filepath = '.'
    if Path(filepath+path_delim+str_tts_sound_file).exists():
        os.remove(filepath+path_delim+str_tts_sound_file)

    if Path(filepath+path_delim+str_play_sound_file).exists():
        os.remove(filepath+path_delim+str_play_sound_file)
    exit.set()     
       
#
#============================================================             
def leave_on_signal(signo, _frame):
    """also quit on signal"""
    print(str_signal, signo)
    wrapup_and_quit()     

#
#============================================================             
if __name__ == '__main__':
    
        
    for sig in ('TERM', 'INT'):
    #for sig in ('TERM', 'HUP', 'INT'): <=== SIGHUP is not defined in Windows
        signal.signal(getattr(signal, 'SIG'+sig), leave_on_signal);
    
    main(sys.argv[1:])

