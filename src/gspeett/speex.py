from ctypes import *
import ctypes.util
import sys
import logging

libspeex_name = ctypes.util.find_library('speex')

if not libspeex_name:
    logging.getLogger('gspeett').critical("libspeex not found! Is it installed?")
    sys.exit(1)

speexDll = CDLL(libspeex_name)

#defines copied from: http://speex.org/docs/api/speex-api-reference/group__Codec.html
SPEEX_SET_ENH = 0                   #Set enhancement on/off (decoder only)
SPEEX_GET_ENH = 1                   #Get enhancement state (decoder only)
SPEEX_GET_FRAME_SIZE = 3            #Obtain frame size used by encoder/decoder
SPEEX_SET_QUALITY = 4               #Set quality value
SPEEX_SET_MODE = 6                  #Set sub-mode to use
SPEEX_GET_MODE = 7                  #Get current sub-mode in use
SPEEX_SET_LOW_MODE = 8              #Set low-band sub-mode to use (wideband only)
SPEEX_GET_LOW_MODE = 9              #Get current low-band mode in use (wideband only)
SPEEX_SET_HIGH_MODE = 10            #Set high-band sub-mode to use (wideband only)
SPEEX_GET_HIGH_MODE = 11            #Get current high-band mode in use (wideband only)
SPEEX_SET_VBR = 12                  #Set VBR on (1) or off (0)
SPEEX_GET_VBR = 13                  #Get VBR status (1 for on, 0 for off)
SPEEX_SET_VBR_QUALITY = 14          #Set quality value for VBR encoding (0-10)
SPEEX_GET_VBR_QUALITY = 15          #Get current quality value for VBR encoding (0-10)
SPEEX_SET_COMPLEXITY = 16           #Set complexity of the encoder (0-10)
SPEEX_GET_COMPLEXITY = 17           #Get current complexity of the encoder (0-10)
SPEEX_SET_BITRATE = 18              #Set bit-rate used by the encoder (or lower)
SPEEX_GET_BITRATE = 19              #Get current bit-rate used by the encoder or decoder
SPEEX_SET_HANDLER = 20              #Define a handler function for in-band Speex request
SPEEX_SET_USER_HANDLER = 22         #Define a handler function for in-band user-defined request
SPEEX_SET_SAMPLING_RATE = 24        #Set sampling rate used in bit-rate computation
SPEEX_GET_SAMPLING_RATE = 25        #Get sampling rate used in bit-rate computation
SPEEX_RESET_STATE = 26              #Reset the encoder/decoder memories to zero
SPEEX_GET_RELATIVE_QUALITY = 29     #Get VBR info (mostly used internally)
SPEEX_SET_VAD = 30                  #Set VAD status (1 for on, 0 for off)
SPEEX_GET_VAD = 31                  #Get VAD status (1 for on, 0 for off)
SPEEX_SET_ABR = 32                  #Set Average Bit-Rate (ABR) to n bits per seconds
SPEEX_GET_ABR = 33                  #Get Average Bit-Rate (ABR) setting (in bps)
SPEEX_SET_DTX = 34                  #Set DTX status (1 for on, 0 for off)
SPEEX_GET_DTX = 35                  #Get DTX status (1 for on, 0 for off)
SPEEX_SET_SUBMODE_ENCODING = 36     #Set submode encoding in each frame (1 for yes, 0 for no, setting to no breaks the standard)
SPEEX_GET_SUBMODE_ENCODING = 37     #Get submode encoding in each frame
SPEEX_GET_LOOKAHEAD = 39            #Returns the lookahead used by Speex
SPEEX_SET_PLC_TUNING = 40           #Sets tuning for packet-loss concealment (expected loss rate)
SPEEX_GET_PLC_TUNING = 41           #Gets tuning for PLC
SPEEX_SET_VBR_MAX_BITRATE = 42      #Sets the max bit-rate allowed in VBR mode
SPEEX_GET_VBR_MAX_BITRATE = 43      #Gets the max bit-rate allowed in VBR mode
SPEEX_SET_HIGHPASS = 44             #Turn on/off input/output high-pass filtering
SPEEX_GET_HIGHPASS = 45             #Get status of input/output high-pass filtering
SPEEX_GET_ACTIVITY = 47             #Get "activity level" of the last decoded frame, i.e. how much damage we cause if we remove the frame
SPEEX_SET_PF = 0                    #Equivalent to SPEEX_SET_ENH
SPEEX_GET_PF = 1                    #Equivalent to SPEEX_GET_ENH
SPEEX_MODE_FRAME_SIZE = 0           #Query the frame size of a mode
SPEEX_SUBMODE_BITS_PER_FRAME = 1    #Query the size of an encoded frame for a particular sub-mode
SPEEX_LIB_GET_MAJOR_VERSION = 1     #Get major Speex version
SPEEX_LIB_GET_MINOR_VERSION = 3     #Get minor Speex version
SPEEX_LIB_GET_MICRO_VERSION = 5     #Get micro Speex version
SPEEX_LIB_GET_EXTRA_VERSION = 7     #Get extra Speex version
SPEEX_LIB_GET_VERSION_STRING = 9    #Get Speex version string
SPEEX_NB_MODES = 3                  #Number of defined modes in Speex

                                    #Encoding/Decoding Modes:
SPEEX_MODEID_NB = 0                 #modeID for the defined narrowband mode
SPEEX_MODEID_WB = 1                 #modeID for the defined wideband mode
SPEEX_MODEID_UWB = 2                #modeID for the defined ultra-wideband mode

class SpeexBits(Structure):
    _fields_ = [('chars', c_char_p)
                , ('nbBits', c_int)
                , ('charPtr', c_int)
                , ('bitPtr', c_int)
                , ('owner', c_int)
                , ('overflow', c_int)
                , ('buf_size', c_int)
                , ('reserved1', c_int)
                , ('reserved2', c_void_p)
                ]

class Encoder:
    def initialize(self, quality = 5, vbr = 0):
        self.bits = SpeexBits()
        speexDll.speex_bits_init(byref(self.bits))

        self.state = speexDll.speex_encoder_init(speexDll.speex_wb_mode)

        self.samples_per_frame = self.control(SPEEX_GET_FRAME_SIZE)
        if self.samples_per_frame <= 0:
            raise(Exception("SPEEX encoder returned 0 samples per frame"))
        #print("SPEEX: Samples per frame: " + str(self.samples_per_frame))

        self.control(SPEEX_SET_VBR, vbr)
        self.control(SPEEX_SET_QUALITY, quality)
        self.control(SPEEX_SET_COMPLEXITY, 3)
        self.control(SPEEX_SET_HIGHPASS, 1)

        self.buffer = create_string_buffer(20000)

    def encode(self, data):
        self.buffer.value = data
        speexDll.speex_bits_reset(byref(self.bits))
        speexDll.speex_encode_int(self.state, self.buffer, byref(self.bits))
        written = speexDll.speex_bits_write(byref(self.bits), self.buffer, len(self.buffer))
        return string_at(self.buffer, written)

    def encode_with_header_byte(self, data):
        self.buffer.value = data
        speexDll.speex_bits_reset(byref(self.bits))
        speexDll.speex_encode_int(self.state, self.buffer, byref(self.bits))
        written = speexDll.speex_bits_write(byref(self.bits), self.buffer, len(self.buffer))
        return chr(written) + string_at(self.buffer, written)

    def destroy(self):
        speexDll.speex_encoder_destroy(self.state)
        speexDll.speex_bits_destroy(byref(self.bits))

    def control(self, request, val = None):
        if val: #Assume we set a value
            tmp = c_int()
            tmp.value = val
            speexDll.speex_encoder_ctl(self.state, request, byref(tmp))
        else: #Assume we get a value
            tmp = c_int()
            speexDll.speex_encoder_ctl(self.state, request, byref(tmp))
            return tmp.value

class Decoder:
    def initialize(self, mode=SPEEX_MODEID_UWB):
        self.state = speexDll.speex_decoder_init(speexDll.speex_lib_get_mode(mode))
        self.bits = SpeexBits()
        speexDll.speex_bits_init(byref(self.bits))
        self.buffer = create_string_buffer(2000)

    def decode(self, data):
        self.buffer.value = data
        speexDll.speex_bits_read_from(byref(self.bits), self.buffer, len(data))
        speexDll.speex_decode_int(self.state, byref(self.bits), self.buffer)
        return string_at(self.buffer, 640)

    def decode_with_header_byte2(self, encoded_data):
        return self.decode(encoded_data[1:])

    def destroy(self):
        speexDll.speex_decoder_destroy(self.state)
        speexDll.speex_bits_destroy(byref(self.bits))
