 #!/usr/bin/env python
 # -*- coding: utf-8 -*-

import os
from distutils.core import setup

setup(name='gSpeett',
      version='1.3',
      license='BSD',
      description='Python bindings to the Google speech recognition service',
      long_description='gSpeett offers a very simple Python API to the Google speech recognition service. It supports FLAC files or microphone input (with Speex encoding)',
      author='Séverin Lemaignan',
      author_email='severin.lemaignan@epfl.ch',
      package_dir = {'': 'src'},
      packages=['gspeett'],
      scripts=['scripts/gspeett']
      )
