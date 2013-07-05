#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EverNote WebClipper publisher.

@author Jay Taylor [@jtaylor]
@date 2013-06-30
"""

import os, sys
from lib.errorcodes import *
from lib.collector import Collector
from lib.generator import generate


def initialize():
    """Initialize app data directories."""
    os.mkdir('data') if not os.path.exists('data') else ''


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

    elif action == 'generate':
        generate()

    else:
        sys.stderr.write('error: unrecognized action: "{0}", view help by running `{1} help`\n'.format(action, sys.argv[0]))
        sys.exit(1)
