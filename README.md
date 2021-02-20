# Speech Output fro Google calendar

### This little script reads the content of a Google Calendar and gives meeting alerts by reading the meeting subjects via text-to-speech.

This was originally built to run on a Raspberry Pi using Python 2.7 but may equally be able to run on any other system with the necessary adaptions like the operating system commands etc.

The scripts reads the prefs.json file to load preferences. The explanation of these preferences are here:

	"status_output": if "on" the script turns verbose displaying console messages
	"str_clear": command for os.system() to clear the screen, e.g. 'clear' in Linux or 'cls' in Windows
	"str_divider": line in ascii to have a visual speration of data
	"str_initial_sound_file": sound file played on startup
	"str_alert_sound": if "on" the sound in the "str_alert_sound_file" below is played before the calender text-to-speech output
	"str_alert_sound_file": sound file played on alert if "str_alert_sound" above in "on"
	"str_tts_sound_file": "temp soundfile where the text-to-speech conversion result is stored
	"number_events": number of calendar entries to be read head 
	"refresh_timer": how often (minutes) 
	"alerts": list of "alert_time" values to trigger the output of alert reminder messages

	"language": the actual language to be used IMPORTANT: this is the only place which defines the actul language to be used
	
	"locales": translation packet for the different strings / meesages in use
    	"lang": identifier tag for the translation packet below - DO NOT CHANGE -
    	"str_lookahead": string like "Maximum number of events in preview: "
    	"str_begins": string like "begins in",
    	"str_minutes": string like "minutes",
    	"str_one_minute": string like "one minute",
    	"str_no_event": string like "No upcoming events found",
    	"str_reloaded": string like "Events reloaded at",
    	"str_on": string like "on",
    	"str_stints": string like "Passes: ",
    	"str_iteration": string like "Minutes in pass:",
    	"str_upcoming": string like "Getting the next ",
    	"str_events": string like " events ..."
    	"str_nodir": string like " does not exist or is not a directory",
    	"str_wrongdir": string like " is the wrong directory"
    	
    	New languages can be added by adding new "locales" translation packets

A quick summary and step by step tutorial for gaining access to Google calendar can be found here:
https://developers.google.com/calendar/quickstart/python

These installs might become necessary along the process:

pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

pip install gTTS pyttsx3 playsound

pip install pydub

pip install datetime

pip install python-dateutil

pip install pathlib

The scipt can be called without parameters. In this case it expects to be invoked from within its base directory. If it is being invoked from outside its base directory (e.g. via desktop icon) the absolute or relative path to the base directory (where sound files and the prefs.json preference file are expected) can be given via command line parameter.

Usage:  CalSpeechReminder.py \[-d | --dir \<base directory\>\] 

or

Usage:  CalSpeechReminder.py \[-h | --help\]

printing some help output

--------------------------------------------------------


While the script is designed to run on Linux, MacOs, and Windows, I use it on a Raspberry Pi. Though, here's an example for Raspbian on how to put it as an icon on the desktop (the cal.png) icon is included:


[Desktop Entry]
Name=CalSpeech
Type=Application
#Exec=lxterminal -t "CalSpeech" --working-directory=/home/pi/CalSpeechReminder/ -e python CalSpeechReminder.py
Exec=/usr/bin/python /home/pi/CalSpeechReminder/CalSpeechReminder.py -d /home/pi/CalSpeechReminder
Icon=/home/pi/CalSpeechReminder/cal.png
Comment=Spoken Calendar Reminders
Terminal=true
X-KeepTerminal=true
StartupNotify=true