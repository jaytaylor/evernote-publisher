#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EverNote WebClipper publisher.

@author Jay Taylor [@jtaylor]
@date 2013-06-30
"""

import settings
from .errorcodes import *

from evernote.api.client import EvernoteClient
from evernote.edam.notestore.ttypes import NoteFilter

import base64, sys
try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import simplejson as json
except ImportError:
    import json


class Collector(object):
    """Note collector."""
    def __init__(self, notebookName):
        """@param notebookName str Notebook name (or name fragment)."""
        self.notebookName = notebookName
        self.client = EvernoteClient(
            consumer_key=settings.consumerKey,
            consumer_secret=settings.consumerSecret,
            token=settings.developerToken,
            sandbox=False
        )
        self.noteStore = self.client.get_note_store()
        
    def getNoteList(self):
        """Retrieve the NoteList for the named notebook."""
        #"""
        notebooks = self.noteStore.listNotebooks()

        filteredNotebooks = filter(lambda nb: self.notebookName.lower() in nb.name.lower(), notebooks)

        if len(filteredNotebooks) < 1:
            sys.stderr.write('error: requested notebook "{0}" not found (candidates were: {1})\n'.format(self.notebookName, ', '.join(map(lambda nb: nb.name, notebooks))))
            sys.exit(ERR_NOTEBOOK_NOT_FOUND)

        notebook = filteredNotebooks[0]
        print 'info: found notebook "{0}"'.format(notebook.name)

        searchFilter = NoteFilter(order=1, ascending=False, notebookGuid=notebook.guid)
        noteList = self.noteStore.findNotes(developerToken, searchFilter, 0, 10000)
        with open('/tmp/search', 'w') as fh:
            fh.write(pickle.dumps(noteList))
        """
        with open('/tmp/search', 'r') as fh:
            noteList = pickle.load(fh)
        """
        return noteList


    def run(self):
        """Retrieve the latest notes."""
        noteList = self.getNoteList()

        for note in noteList.notes:
            # args: authenticationToken, guid, withContent, withResourcesData, withResourcesRecognition, withResourcesAlternateData
            note = self.noteStore.getNote(developerToken, note.guid, True, True, True, True)
            out = '''
    title: {title}
    created: {created}
    updated: {updated}
    deleted: {deleted}
    content: {content}
    tags: {tags}
            '''.format(
                title=note.title,
                created=note.created,
                updated=note.updated,
                deleted=note.deleted,
                content=note.content,
                tags=', '.join(note.tagNames) if note.tagNames is not None else '',
            ).strip()
            print type(note.contentHash), note.contentHash
            data = {
                'title': note.title,
                'guid': note.guid,
                'created': note.created,
                'updated': note.updated,
                'deleted': note.deleted,
                'b64Content': base64.b64encode(note.content),
                'b64ContentHash': base64.b64encode(note.contentHash),
                'contentLength': note.contentLength,
                'tagNames': note.tagNames,
                'tagGuids': note.tagGuids,
            }

            #print dir(note)
            #print str(note.attributes
            with open('{0}/{1}.pickle'.format(settings.DATA_PATH, note.created), 'w') as fh:
                pickle.dump(note, fh)

            with open('{0}/{1}.json'.format(settings.DATA_PATH, note.created), 'w') as fh:
                json.dump(data, fh)







