#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EverNote WebClipper publisher.

@author Jay Taylor [@jtaylor]
@date 2013-06-30
"""

import settings, os
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

TAG_CACHE_FILENAME = 'data/.tagCache.pickle'


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
        self.tagCache = {}
        self._loadTagCache()

    def _loadTagCache(self):
        """Try to load tag cache from disk."""
        print 'info: loading tag cache..'

        try:
            with open(TAG_CACHE_FILENAME, 'r') as fh:
                self.tagCache = pickle.loads(fh.read())
            print 'info: tag cache successfully loadded'

        except Exception, e:
           print 'error: failed to load tag cache: {0}'.format(e)

    def __del__(self):
        """Persist tag cache to disk."""
        if len(self.tagCache) == 0:
           return

        print 'info: shutdown: saving tag cache to disk...'
        with open(TAG_CACHE_FILENAME, 'w') as fh:
            fh.write(pickle.dumps(self.tagCache))
        
    def getNoteList(self):
        """Retrieve the NoteList for the named notebook."""
        """
        notebooks = self.noteStore.listNotebooks()

        filteredNotebooks = filter(lambda nb: self.notebookName.lower() in nb.name.lower(), notebooks)

        if len(filteredNotebooks) < 1:
            sys.stderr.write('error: requested notebook "{0}" not found (candidates were: {1})\n'.format(self.notebookName, ', '.join(map(lambda nb: nb.name, notebooks))))
            sys.exit(ERR_NOTEBOOK_NOT_FOUND)

        notebook = filteredNotebooks[0]
        print 'info: found notebook "{0}"'.format(notebook.name)

        searchFilter = NoteFilter(order=1, ascending=False, notebookGuid=notebook.guid)
        noteList = self.noteStore.findNotes(settings.developerToken, searchFilter, 0, 10000)
        if not os.path.exists('/tmp/search'):
            os.makedirs('/tmp/search')
        with open('/tmp/search', 'w') as fh:
            fh.write(pickle.dumps(noteList))
        """
        with open('/tmp/search', 'r') as fh:
            noteList = pickle.load(fh)
        """
        #"""
        return noteList

    def getNote(self, guid):
        """Given a note guid, retrieves and returns the full note."""
        return self.noteStore.getNote(settings.developerToken, guid, True, True, True, True)

    def _resolveGuidToTag(self, guid):
        """Given a tag guid, will look in cache and return cached item, otherwise will pull the tag from the Evernote API."""
        if guid in self.tagCache:
           # Read from cache.
           return self.tagCache[guid]

        # Otherwise, retrieve a fresh list of all tags on the account.
        print 'info: fetching full tag list for the account'
        tags = self.noteStore.listTags(settings.developerToken)
        for tag in tags:
            # Add to cache.
            self.tagCache[tag.guid] = tag

        if guid in self.tagCache:
            # Return cached
            return self.tagCache[guid]

        # Otherwise, this is unexpected.  Attempt a direct lookup.
        print 'warn: requested tag guid not found in full listing, will attempt a direct lookup'
        tag = self.noteStore.getTag(settings.developerToken, guid)
        # Add to cache.
        self.tagCache[tag.guid] = tag
        return tag

    @staticmethod
    def _tagToDict(tag):
        """Convert a Tag object to a dict representation."""
        return dict(map(lambda key: (key, getattr(tag, key)), ('updateSequenceNum', 'guid', 'name', 'parentGuid')))

    def getTags(self, note):
        """Given a note, retrieves associated tag records and converts them to dicts."""
        print 'guids=',note.tagGuids
        return map(self._tagToDict, map(self._resolveGuidToTag, note.tagGuids or []))

    def run(self):
        """Retrieve the latest notes."""
        noteList = self.getNoteList()

        for partialNote in noteList.notes:
            # args: authenticationToken, guid, withContent, withResourcesData, withResourcesRecognition, withResourcesAlternateData
            note = self.getNote(partialNote.guid)
            tags = self.getTags(note)
#            out = '''
#    title: {title}
#    created: {created}
#    updated: {updated}
#    deleted: {deleted}
#    content: {content}
#    tags: {tags}
#            '''.format(
#                title=note.title,
#                created=note.created,
#                updated=note.updated,
#                deleted=note.deleted,
#                content=note.content,
#                tags=', '.join(note.tagNames) if note.tagNames is not None else '',
#            ).strip()
            #print type(note.contentHash), note.contentHash
            print dir(note)
            print note.tagNames
            data = {
                'title': u'{0}'.format(note.title.decode('unicode-escape')).encode('utf-8'),
                #'b64Title': base64.b64encode(note.title),
                'guid': note.guid,
                'created': note.created,
                'updated': note.updated,
                'deleted': note.deleted,
                'b64Content': base64.b64encode(note.content),
                'b64ContentHash': base64.b64encode(note.contentHash),
                'contentLength': note.contentLength,
                'tags': tags,
                'tagNames': note.tagNames,
                'tagGuids': note.tagGuids,
            }

            #print dir(note)
            #print str(note.attributes
            with open('{0}/{1}.pickle'.format(settings.DATA_PATH, note.created), 'w') as fh:
                pickle.dump(note, fh)

            with open('{0}/{1}.json'.format(settings.DATA_PATH, note.created), 'w') as fh:
                json.dump(data, fh)

