import pyaudio
import speex
import sys
import urllib2
import urllib
import json
import re, htmlentitydefs
from datetime import datetime
import logging

GSPEETT_VERSION="1.2"

RECOGNIZE_URL= "http://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&pfilter=2&"

LANG_EN= "en-US"
LANG_FR= "fr-FR"

#status_codes 
STATUS_OK = 0
STATUS_ABORTED = 1
STATUS_AUDIO = 2
STATUS_NETWORK = 3
STATUS_NO_SPEECH = 4
STATUS_NO_MATCH = 5
STATUS_BAD_GRAMMAR = 6

SPEEX_CONTENT= "audio/x-speex-with-header-byte"
FLAC_CONTENT= "audio/x-flac"

class GoogleTranslator:

    def __init__(self, google_api_key, to = "en"):
        if to:
            to = to.split("-")[0] # convert en-US -> en
            
        self.to = to
        self._key = google_api_key

    def translate(self, text, to=None):
        
        if to:
            to = to.split("-")[0] # convert en-US -> en
            
        text = text.decode('utf-8')
        text = text.encode('ascii', 'ignore')
        url = "https://www.googleapis.com/language/translate/v2?"
        values = urllib.urlencode(
                {"key": self._key,
                 "target": (to if to else self.to),
                 "q": text})

        url += values
        logging.getLogger('gspeett').debug(url)
        response = urllib2.urlopen(urllib2.Request(url))

        return self.unescape(urllib.unquote(json.load(response)['data']['translations'][0]['translatedText']))
        
        ##
        # Removes HTML or XML character references and entities from a text string.
        #
        # @param text The HTML (or XML) source text.
        # @return The plain text, as a Unicode string, if necessary.
        #
        # Taken from http://effbot.org/

    def unescape(self, text):
        def fixup(m):
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text # leave as is
        return re.sub("&#?\w+;", fixup, text)

class GoogleVoiceRecognition:

    def __init__(self, lang=LANG_EN):
      
        self.SAMPLING_RATE = 16000
        self.lang = lang
        self._mic_isinit = False
        self._stream = None
        self._logger = logging.getLogger('gspeett')
        
        self._logger.debug("Created a recognizer for " + lang)
        
    def __del__(self):
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._pyaudio.terminate()
            self._speex_encoder.destroy()

    def init_mic(self):

        self._logger.debug("Init speex")
        self._speex_encoder = speex.Encoder()
        self._speex_encoder.initialize(speex.SPEEX_MODEID_WB, quality = 8, vbr = 1) # Initialize encoder as in Google Chromium (-> audio_encoder.cc): wide band, q8, vbr

        # pyaudio constants
        self.samples_per_packet = 320
        
        #For some reason, this way of computing samples_per_packet does not work
        #self.PACKET_LENGTH = 100.0 #ms
        #self.samples_per_packet = int(self.SAMPLING_RATE * self.PACKET_LENGTH / 1000) # 100ms for a sampling rate of 16kHz -> samples_per_packet = 1600
        

        self._logger.debug("Init mic input")
        FORMAT = pyaudio.paInt16
        CHANNELS = 1

        self._pyaudio = pyaudio.PyAudio()

        self._stream = self._pyaudio.open(format = FORMAT,
                            channels = CHANNELS, 
                            rate = self.SAMPLING_RATE, 
                            input = True,
                            output = False,
                            frames_per_buffer = self.samples_per_packet)
                            
        self._mic_isinit = True
        
        self._logger.debug("Ready to record")


    def mic(self, seconds=2):
        
        if not self._mic_isinit:
            self.init_mic()

        self._logger.debug("Recording for " + str(seconds) + "s...")

        encoded_stream = "" 

        for i in range(0, seconds * self.SAMPLING_RATE / self.samples_per_packet ):
                data = self._stream.read(self.samples_per_packet)       #Read data from the mic.
                encoded_stream += self._speex_encoder.encode_with_header_byte(data)        #Encode the data.

        t0 = datetime.now()
        res = self.request_recognition(encoded_stream, SPEEX_CONTENT)

        self._logger.debug("Recognition request duration: " + str((datetime.now() - t0).microseconds / 1000) + "ms.")

        self._logger.debug(str(res))
        if res['status'] != STATUS_OK:
            self._logger.warning("We could not recognize the sentence!")

        return [a['utterance'].encode('utf-8') for a in res['hypotheses']]

    def flac(self, path):

        sample = ""
        with open(path, 'r') as f:
                sample = f.read()

        res = self.request_recognition(sample, FLAC_CONTENT)

        if res['status'] != STATUS_OK:
            self._logger.warning("We could not recognize the sentence! Check you're sending a FLAC file sampled at 16kHz.")

        return [a['utterance'].encode('utf-8') for a in res['hypotheses']]


    def request_recognition(self, data, contenttype = SPEEX_CONTENT):

        self._logger.debug("Sending the audio content to Google servers...")

        headers = {'Content-Type': contenttype + '; rate=' + str(self.SAMPLING_RATE)}

        response = urllib2.urlopen(urllib2.Request(
                        RECOGNIZE_URL + "lang=" + self.lang, 
                        data, headers))

        return json.load(response)






