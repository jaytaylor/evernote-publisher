#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EverNote WebClipper publisher.

@author Jay Taylor [@jtaylor]
@date 2013-06-30
"""

import base64
import glob
import os
import settings
import simplejson
import sys
import time

import bs4
import evernote.api.client
import evernote.api.client
import evernote.edam.notestore.ttypes

from .errorcodes import *
from .logger import logger

try:
    import cPickle as pickle
except ImportError:
    logger.warn('cPickle import failed, falling back to plain pickle')
    import pickle

TAG_CACHE_FILENAME = 'data/.tagCache.pickle'

class Collector(object):
    """Note collector."""

    def __init__(self, notebookName):
        """@param notebookName str Notebook name (or name fragment)."""
        self.notebookName = notebookName
        self.client = evernote.api.client.EvernoteClient(
            consumer_key=settings.consumerKey,
            consumer_secret=settings.consumerSecret,
            token=settings.developerToken,
            sandbox=False
        )
        self.noteStore = self.client.get_note_store()
        self.tagCache = {}
        self.loadTagCache()
        self.remoteNoteCounts = None

    def run(self):
        """Retrieve the latest notes."""
        notebook = self.resolveNotebook()
        offset = 0
        noteList = self.getNoteList(notebook, offset)
        while len(noteList.notes) > 0:
            numUpdated = self.hydrateAndStore(noteList.notes)
            # If no updates were applied and the local and remote counts match.
            if numUpdated == 0 and self.localCountsMatchRemote(notebook):
                # Then things are probably already in sync.
                return
            offset += len(noteList.notes)
            noteList = self.getNoteList(notebook, offset)

    def resolveNotebook(self):
        notebooks = self.noteStore.listNotebooks()

        filteredNotebooks = [nb for nb in notebooks if self.notebookName.lower() in nb.name.lower()]

        if len(filteredNotebooks) < 1:
            logger.error('requested notebook "{0}" not found (candidates were: {1})\n'.format(self.notebookName, ', '.join([nb.name for nb in notebooks])))
            sys.exit(ERR_NOTEBOOK_NOT_FOUND)

        notebook = filteredNotebooks[0]
        logger.info('found notebook "{0}"'.format(notebook.name))
        return notebook

    def getNoteList(self, notebook, offset):
        """Retrieve the NoteList for the named notebook."""
        pageSize = 49
        noteList = self.noteStore.findNotes(settings.developerToken, self.defaultSearchFilter(notebook), offset, pageSize)
        logger.debug('-> offset=%s count=%s' % (offset, len(noteList.notes)))
        return noteList

    def hydrateAndStore(self, partialNotes):
        numUpdated = 0
        for partialNote in partialNotes:
            #if partialNote.guid != '26cd3186-1044-4d0c-b1a3-7ec47f1a0549':
            #    continue
            #if '%s' % partialNote.created != '1467826537000':
            #    continue
            # args: authenticationToken, guid, withContent, withResourcesData, withResourcesRecognition, withResourcesAlternateData
            jsonFileName = '{0}/{1}.json'.format(settings.DATA_PATH, partialNote.created)
            pickleFileName = '{0}/{1}.pickle'.format(settings.DATA_PATH, partialNote.created)
            if os.path.exists(jsonFileName) and os.path.exists(pickleFileName):
                logger.debug('jsonFileName=%s', jsonFileName)
                with open(jsonFileName, 'r') as fh:
                    try:
                        detail = simplejson.load(fh)
                        if isinstance(detail, dict) and detail.get('updated', None) == partialNote.updated:
                            logger.debug('Already up to date for note=%s' % (partialNote.title,))
                            continue
                    except simplejson.errors.JSONDecodeError:
                        logger.exception('Found malformed or corrupted JSON file: %s (will auto-rename)', jsonFileName)
                        stamp = datetime.datetime.now().strftime('%Y-%m-%dT%H_%M_%S')
                        os.rename(jsonFileName, 'corrupted--%s.%s' % (jsonFileName, stamp))

            note = self.getNote(partialNote.guid)
            tags = self.getNoteTags(note)

            #logger.debug('b64Content: %s' % (type(note.content)))
            data = {
                'title': bs4.BeautifulSoup(note.title, 'html.parser').string,
                #'b64Title': base64.b64encode(note.title),
                'guid': note.guid,
                'created': note.created,
                'updated': note.updated,
                'deleted': note.deleted,
                'b64Content': base64.b64encode(note.content.encode('utf-8')),
                'b64ContentHash': base64.b64encode(note.contentHash),
                'contentLength': note.contentLength,
                'tags': tags,
                'tagNames': note.tagNames,
                'tagGuids': note.tagGuids,
            }

            with open(pickleFileName, 'wb') as fh:
                pickle.dump(note, fh)

            with open(jsonFileName, 'w') as fh:
                simplejson.dump(data, fh)

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
            # print type(note.contentHash), note.contentHash
            # print dir(note)
            # print note.tagNames

            #print dir(note)
            #print str(note.attributes

            numUpdated += 1

        return numUpdated

    def defaultSearchFilter(self, notebook):
        # `order = 1' -> order by created
        # `order = 2' -> order by updated
        # @see NoteStoreOrder at https://dev.evernote.com/doc/reference/Types.html
        searchFilter = evernote.edam.notestore.ttypes.NoteFilter(order=2, ascending=False, notebookGuid=notebook.guid)
        return searchFilter

    def localCountsMatchRemote(self, notebook):
        localJsonCount = len(glob.glob('{0}/[0-9]*.json'.format(settings.DATA_PATH)))
        localPickleCount = len(glob.glob('{0}/[0-9]*.pickle'.format(settings.DATA_PATH)))
        if localJsonCount != localPickleCount:
            logger.debug('local-json-len=%s local-pikl-len=%s', localJsonCount, localPickleCount)
            return False
        if self.remoteNoteCounts is None:
            self.remoteNoteCounts = self.noteStore.findNoteCounts(settings.developerToken, self.defaultSearchFilter(notebook), False)
        remoteCount = self.remoteNoteCounts.notebookCounts[notebook.guid]
        logger.debug('local-json-len=%s local-pikl-len=%s remote-book-len=%s', localJsonCount, localPickleCount, remoteCount)
        if localPickleCount != remoteCount and localPickleCount != remoteCount-1: # There seems to be a counting bug on Evernotes side.
            return False
        return True

    def loadTagCache(self):
        """Try to load tag cache from disk."""
        logger.info('loading tag cache..')

        try:
            with open(TAG_CACHE_FILENAME, 'rb') as fh:
                self.tagCache = pickle.loads(fh.read(), encoding='latin1')
            logger.info('tag cache successfully loadded')

        except Exception:
            logger.exception('notice: pre-existing tag cache not found or loading failed')

    def __del__(self):
        """Persist tag cache to disk."""
        if not hasattr(self, 'tagCache') or len(self.tagCache) == 0:
           return

        logger.info('shutdown: saving tag cache to disk...')
        with open(TAG_CACHE_FILENAME, 'wb') as fh:
            fh.write(pickle.dumps(self.tagCache))

    def getNote(self, guid):
        """Given a note guid, retrieves and returns the full note."""
        return self.noteStore.getNote(settings.developerToken, guid, True, True, True, True)

    def getNoteTags(self, note):
        """Given a note, retrieves associated tag records and converts them to dicts."""
        logger.info('guids=%s for note=%s' % (note.tagGuids, note.title))
        return list(map(self.tagToDict, list(map(self.resolveGuidToTag, note.tagGuids or []))))

    def resolveGuidToTag(self, guid):
        """Given a tag guid, will look in cache and return cached item, otherwise will pull the tag from the Evernote API."""
        if guid in self.tagCache:
           # Read from cache.
           return self.tagCache[guid]

        # Otherwise, retrieve a fresh list of all tags on the account.
        logger.info('fetching full tag list for the account')
        tags = self.noteStore.listTags(settings.developerToken)
        for tag in tags:
            # Add to cache.
            self.tagCache[tag.guid] = tag

        if guid in self.tagCache:
            # Return cached
            return self.tagCache[guid]

        # Otherwise, this is unexpected.  Attempt a direct lookup.
        logger.warn('requested tag guid not found in full listing, will attempt a direct lookup')
        tag = self.noteStore.getTag(settings.developerToken, guid)
        # Add to cache.
        self.tagCache[tag.guid] = tag
        return tag

    @staticmethod
    def tagToDict(tag):
        """Convert a Tag object to a dict representation."""
        return dict([(key, getattr(tag, key)) for key in ('updateSequenceNum', 'guid', 'name', 'parentGuid')])
