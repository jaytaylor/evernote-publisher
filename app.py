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

def main():
    initialize()

    if len(sys.argv) < 2:
        sys.stderr.write('error: missing required parameter: action\n')
        sys.exit(ERR_MISSING_REQUIRED_PARAM)

    action = sys.argv[1].lower()

    if action == 'help':
        sys.stderr.write('''
available commands:
    collect [notebook-name] - retrieve and organize the latest notes
    generate                - alias to `rebuild'
    generate-indices        - alias to `rebuild-indices'
    rebuild                 - rebuild static site
    rebuild-indices         - rebuild static site indices *only*
    refresh [notebook-name] - collect + rebuild

usage: {0} [action] [additional parameters?]
'''.format(sys.argv[0]))

    if action in ('collect', 'refresh'):
        if len(sys.argv) < 3:
            sys.stderr.write('error: missing required parameter: notebook-name\n')
            sys.exit(ERR_MISSING_REQUIRED_PARAM)

        myNotebook = sys.argv[2]
        Collector(myNotebook).run()

    elif action in ('rebuild', 'generate', 'refresh'):
        generator = HtmlGenerator()
        generator.generate()

    elif action in ('rebuild-indices', 'generate-indices', 'refresh-indices'):
        generator = HtmlGenerator()
        generator.generateIndices()

    else:
        sys.stderr.write('error: unrecognized action: "{0}", view help by running `{1} help`\n'.format(action, sys.argv[0]))
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.stderr.write(('-' * 80) + '\n')
        sys.stderr.write('Yikes... there was a problem.\n')
        sys.stderr.write('if it looks like a token auth issue you can grab a new one from:\n')
        sys.stderr.write('https://www.evernote.com/api/DeveloperToken.action\n')
        sys.stderr.write(('-' * 80) + '\n')
        raise

