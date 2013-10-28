import sys
from datetime import datetime
import logging

# Sound related
import pyaudio
import speex
import audioop

# Web related
import urllib2
import urllib
import json
import re, htmlentitydefs

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
        self._speex_encoder.initialize(quality = 8, vbr = 1) # Initialize encoder as in Google Chromium (-> audio_encoder.cc): wide band, q8, vbr

        self.VOLUME_THRESHOLD = 0 # Volume threshold, for silence detection. It is computed before each recording.
        self.SECONDS_SILENCE_BEFORE_STOP = 0.5 #After this amount of detected silence, the mic recording stops
        
        self._SILENCE_SAMPLE_BUFFER_SIZE = 30 #Amount of sample to observe before positively detecting a silence.
        
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


    def mic(self, seconds=0):
        """ Starts a recording session of the microphone.
        
        If 'seconds' is given and superior to 0, the recording lasts for the given
        amount of time.
        Else, the recording stops when a silence longer than SECONDS_SILENCE_BEFORE_STOP
        is detected.
        """
        
        if not self._mic_isinit:
            self.init_mic()
        
        auto_detect_end = True if seconds == 0 else False

        # Only useful if auto_detect_end == True
        _MAX_SAMPLES_BEFORE_STOP = int(self.SAMPLING_RATE / self.samples_per_packet * self.SECONDS_SILENCE_BEFORE_STOP)
        _samples_before_stop = _MAX_SAMPLES_BEFORE_STOP
        _sample_buffer = 0
        _sample_eater = 0
        _recording_started = False
        
        encoded_stream = "" 
        
        for i in range(8):
            self._stream.read(self.samples_per_packet) #Read some sample to let the mic settle down

        # Read some samples to compute average background noise
        noise_level = 0
        samples_for_noise_measurement = 10
        for i in range(samples_for_noise_measurement):
            data = self._stream.read(self.samples_per_packet)
            noise_level += audioop.rms(data, 2)
        self.VOLUME_THRESHOLD = int(noise_level / samples_for_noise_measurement) + 20
        self._logger.debug("Measured average noise level: " + str(self.VOLUME_THRESHOLD))

        
        if auto_detect_end:
            seconds = 6
            self._logger.debug("Recording... (" + str(seconds) + "s max)")
        else:
            self._logger.debug("Recording for " + str(seconds) + "s...")
            
        for i in range(0, seconds * self.SAMPLING_RATE / self.samples_per_packet ):
            
            _sample_buffer = max(0, _sample_buffer - _sample_eater)
            
            data = self._stream.read(self.samples_per_packet)       #Read data from the mic.
            
            level = audioop.rms(data, 2) # 2 because of paInt16
            
            if level < self.VOLUME_THRESHOLD:
                _sample_eater = 1 # Will empty the _sample_buffer
                
            else: # Speech detected
                if auto_detect_end:
                    # Reset the amount of samples to wait before stopping
                    _samples_before_stop = _MAX_SAMPLES_BEFORE_STOP
                    
                if _sample_buffer < self._SILENCE_SAMPLE_BUFFER_SIZE:
                    _sample_eater = -2 # Will fill the _sample_buffer
                else:
                    _sample_eater = 0
            
            if _sample_buffer == 0:
                #Silence!!
                if auto_detect_end:
                    if not _samples_before_stop and _recording_started:
                        break
                    _samples_before_stop -= 1
            else:
                if not _recording_started:
                    self._logger.debug("Speaker started to speak!")
                    _recording_started = True
                    
                encoded_stream += self._speex_encoder.encode_with_header_byte(data) #Encode the data.

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






