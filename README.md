This little script reads the content of a Google Calendar and gives meeting alerts by reading the meeting subjects via text-to-speech

This was originally built to run on a Raspberry Pi using Python 2.7 but may equally be able to run on any other system with the necessary
adaptions like the operating system commands etc.

The scripts reads a json file to load preferences. The explanation of these preferences are here:

	"str_clear": command for os.system() to clear scren, e.g. 'clear' in Linux or 'cls' imn Windows
	"str_divider": line in ascii to have a visual speration of data
	"str_initial_sound_file": sound file played on startup
	"str_alert_sound_file": sound file played on alert
	"str_tts_sound_file": "temp soundfile fot text-to-speech
	"number_events": number of calendar entries to be read head 
	"refresh_timer": how often (minutes) 
	"alerts": list of "alert_time" values to trigger the output of alert reminder messages

	"language": the actual language to be used IMPORTANT: this is the only place which defines the actul language to be used
	
	"locales": translation packet for the different strings / meesages in use
    	"lang": identifier tag for the translation packet below - DO NOT CHANGE -
    	"str_begins": string like "begins in",
    	"str_minutes": string like "minutes",
    	"str_one_minute": string like "one minute",
    	"str_no_event": string like "No upcoming events found",
    	"str_reloaded": string like "Events reloaded at",
    	"str_iteration": string like "Iteration:",
    	"str_upcoming": "string likeGetting the next ",
    	"str_events": string like " events ...".
    	
    	New languages can be added by adding new "locales" translation packets

A quick summary and step by step tutorial for gaining access to Google calendar can be found here:
https://developers.google.com/calendar/quickstart/python

These installs might become necessary along the process:

pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

pip install gTTS pyttsx3 playsound

pip install pydub

pip install datetime

pip install python-dateutil





