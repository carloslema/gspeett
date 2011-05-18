 #!/usr/bin/env python
 # -*- coding: utf-8 -*-

import os
from distutils.core import setup

setup(name='gSpeett',
      version='1.2',
      license='BSD',
      description='Python bindings to the Google speech recognition service',
      long_description='gSpeett offers a very simple Python API to the Google speech recognition service. It supports FLAC files or microphone input (with Speex encoding)',
      author='OpenRobots team',
      author_email='openrobots@laas.fr',
      url='http://www.openrobots.org',
      package_dir = {'': 'src'},
      packages=['gspeett'],
      scripts=['scripts/gspeett']
      )
