#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EverNote WebClipper publisher.

@author Jay Taylor [@jtaylor]
@date 2013-06-30
"""

import os, sys
import settings
from lib.errorcodes import *
from lib.collector import Collector
from lib.generator import HtmlGenerator


def initialize():
    """Cleanup settings and initialize app data directories."""
    if settings.DATA_PATH.endswith('/'):
        settings.DATA_PATH = settings.DATA_PATH[0:-1]
    if settings.OUTPUT_PATH.endswith('/'):
        settings.OUTPUT_PATH = settings.OUTPUT_PATH[0:-1]

    for path in [settings.DATA_PATH, settings.OUTPUT_PATH]:
        if not os.path.exists(path):
            os.mkdir(path)


if __name__ == '__main__':
    initialize()

    if len(sys.argv) < 2:
        sys.stderr.write('error: missing required parameter: action\n')
        sys.exit(ERR_MISSING_REQUIRED_PARAM)

    action = sys.argv[1].lower()

    if action == 'help':
        sys.stderr.write('''
available commands:
    collect [notebook-name] - retrieve and organize the latest notes
    rebuild                 - rebuild static site

usage: {0} [action] [additional parameters?]
'''.format(sys.argv[0]))

    elif action == 'collect':
        if len(sys.argv) < 3:
            sys.stderr.write('error: missing required parameter: notebook-name\n')
            sys.exit(ERR_MISSING_REQUIRED_PARAM)

        myNotebook = sys.argv[2]
        Collector(myNotebook).run()

    elif action == 'rebuild':
        generator = HtmlGenerator()
        generator.generate()

    else:
        sys.stderr.write('error: unrecognized action: "{0}", view help by running `{1} help`\n'.format(action, sys.argv[0]))
        sys.exit(1)

