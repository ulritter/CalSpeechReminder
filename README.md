
This little script reads the content of a Google Calendar and gives meeting alerts by reading the meeting subjects via text-to-speech

This was originally built to run on a Raspberry Pi using Python 2.7 but may equally be able to run on any other system with the necessary
adaptions like the operating system commands etc.

A quick summary and step by step tutorial for gaining access to Google calendar can be found here:
https://developers.google.com/calendar/quickstart/python

These installs might become necessary along the process:

pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

pip install gTTS pyttsx3 playsound

pip install pydub

pip install datetime

sudo apt-get install fswebcam




