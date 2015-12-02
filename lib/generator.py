# -*- coding: utf-8 -*-

"""Note renderer."""

import base64, datetime, simplejson as json, glob, os, settings, shutil, unicodedata
from jinja2 import Template, DictLoader
from jinja2.environment import Environment
from .util import fileGetContents

try:
    import cPickle as pickle
except ImportError:
    import pickle


class Note(object):
    def __init__(self, data):
        self.id = data['id']
        self.data = data['data']
        self.createdTs = datetime.datetime.fromtimestamp(self.data['created']/1000.0)
        self.content = base64.b64decode(self.data['b64Content']).decode('utf-8')
        print self.data.keys() #dir(self.data)
        print self.data['tagNames']

    def __getattr__(self, attr):
        """Pass-through to `data` keys when requrested attribute is not available."""
        if attr in self.__dict__:
            return getattr(self, attr)

        if attr in self.data:
            return self.data[attr]

        raise AttributeError("'Note' object has no attribute '{0}'".format(attr))


#def renderNote(fileName):
#    """Render a single note."""
#    with open(fileName, 'r') as fh:
#        print 'fileName={fileName}'.format(fileName)
#        note = pickle.load(fh)
#        data = {
#            'title': note.title,
#            'guid': note.guid,
#            'created': note.created,
#            'updated': note.updated,
#            'deleted': note.deleted,
#            'b64Content': base64.b64encode(note.content),
#            'b64ContentHash': base64.b64encode(note.contentHash),
#            'contentLength': note.contentLength,
#            'tagNames': note.tagNames,
#            'tagGuids': note.tagGuids,
#        }
#
#    settings.OUTPUT_PATH


class HtmlGenerator(object):
    """Generate and render HTML output."""

    def __init__(self):
        """Prepare jinja2 template environment."""
        self.env = Environment()
        self.templates = dict((name[10:], open(name, 'rb').read()) for name in glob.glob('templates/*.html'))
        self.env.loader = DictLoader(self.templates)

    def generate(self):
        """Read and render Note data."""
        listing = []
        dataFiles = glob.iglob('{0}/*.json'.format(settings.DATA_PATH))

        if not os.path.exists(settings.OUTPUT_PATH + '/api'):
            os.makedirs(settings.OUTPUT_PATH + '/api')
        if not os.path.exists(settings.OUTPUT_PATH + '/node'):
            os.makedirs(settings.OUTPUT_PATH + '/node')
        if not os.path.exists(settings.OUTPUT_PATH + '/tag'):
            os.makedirs(settings.OUTPUT_PATH + '/tag')

        for path in dataFiles:
            jsonFileName = path[path.rindex('/')+1:]
            destination = '{0}/api/{1}'.format(settings.OUTPUT_PATH, jsonFileName)
            shutil.copyfile(path, destination)

            with open(path, 'r') as fh:
                data = json.load(fh)
            listing.append({'id': jsonFileName[0:jsonFileName.index('.')], 'data': data})

        notes = sorted(filter(lambda n: n.deleted is not True, map(lambda d: Note(d), listing)), key=lambda n: n.createdTs, reverse=True)

        self.makeIndex(notes)

        map(self.makeNote, notes)

        self.makeTags(notes)

        #serializedDataFiles = glob.iglob('{0}/*.pickle'.format(settings.DATA_PATH))
        #for fileName in serializedDataFiles:
        #    renderNote(fileName)

    @staticmethod
    def arrangeNotesByTag(notes):
        byTag = {}
        for note in notes:
            if hasattr(note, 'tags'):
                for tag in note.tags:
                    tag['name'] = tag['name'].lower()
                    if tag['name'] not in byTag:
                        byTag[tag['name']] = tag
                        byTag[tag['name']]['notes'] = []
                    byTag[tag['name']]['notes'].append(note)
        for tagName in byTag:
            byTag[tagName]['notes'] = sorted(byTag[tagName]['notes'], key=lambda note: note.createdTs, reverse=True)
        return byTag

    def notesByTag(self, notes, order='asc'):
        """@return list of tags, each tag includes notes."""
        byTag = self.arrangeNotesByTag(notes)
        values = sorted(byTag.values(), key=lambda tag: tag['name'], reverse=order == 'desc')
        return values

    def notesByTagFrequency(self, notes, order='asc'):
        """@return list of tags, each tag includes notes."""
        byTag = self.arrangeNotesByTag(notes)
        values = sorted(byTag.values(), key=lambda tag: tag['name'])
        values = sorted(values, key=lambda tag: len(byTag[tag['name']]['notes']), reverse=order == 'desc')
        return values

    def makeTags(self, notes):
        """Create tags index."""
        tagsAsc = self.notesByTag(notes)
        for tag in tagsAsc:
            self.render('tag.html', 'tag/{0}.html'.format(tag['name']), **{'tag': tag})

        tagIndices = {
            'tag/index.html': tagsAsc,
            'tag/by-tag-desc.html': self.notesByTag(notes, order='desc'),
            'tag/by-frequency-asc.html': self.notesByTagFrequency(notes),
            'tag/by-frequency-desc.html': self.notesByTagFrequency(notes, order='desc'),
        }

        for filePath, tags in tagIndices.items():
            self.render('tagIndex.html', filePath, **{'tags': tags})

    def makeNote(self, note):
        """Render and write out note."""
        self.render('node.html', 'node/{0}.html'.format(note.id), **{'note': note})

    def makeIndex(self, notes):
        """Create and write out static index."""
        self.render('noteIndex.html', 'index.html', **{'notes': notes})

    def render(self, template, targetFile, **kw):
        """Render a template."""
        t = self.env.get_template(template)
        rendered = t.render(**kw)
        with open('{0}/{1}'.format(settings.OUTPUT_PATH, targetFile), 'w') as fh:
            fh.write(rendered.encode('utf-8'))

