# -*- coding: utf-8 -*-

"""Renderer."""

import settings
import glob

try:
    import cPickle as pickle
except ImportError:
    import pickle


def renderNote(fileName):
    """Render a single note."""
    settings.OUTPUT_PATH


def render():
    """Read and render Note data."""
    serializedDataFiles = glob.iglob('{0}/*.pickle'.format(settings.DATA_PATH))
    for fileName in serializedDataFiles:
        with open(fileName, 'r') as fh:
            note = pickle.load(fh)

