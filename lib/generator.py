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
        
        #serializedDataFiles = glob.iglob('{0}/*.pickle'.format(settings.DATA_PATH))
        #for fileName in serializedDataFiles:
        #    renderNote(fileName)

    def makeNote(self, note):
        """Render and write out note."""
        #with open('templates/node.html', 'r') as fh:
        t = self.env.get_template('node.html')#Template(fh.read())
        rendered = t.render(note=note)

        with open('{0}/node/{1}.html'.format(settings.OUTPUT_PATH, note.id), 'w') as fh:
            fh.write(rendered.encode('utf-8'))

    def makeIndex(self, notes):
        """Create and write out static index."""
        #with open('templates/index.html', 'r') as fh:
        t = self.env.get_template('index.html') #Template(fh.read())
        rendered = t.render(notes=notes)

        with open('{0}/index.html'.format(settings.OUTPUT_PATH), 'w') as fh:
            fh.write(rendered.encode('utf-8'))

