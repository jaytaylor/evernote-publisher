# -*- coding: utf-8 -*-

"""Note renderer."""

import base64, datetime, simplejson as json, glob, os, re, settings, shutil, unicodedata, urllib
from bs4 import BeautifulSoup
import jinja2
from unidecode import unidecode
from .util import fileGetContents, safeUnicode

try:
    import cPickle as pickle
except ImportError:
    import pickle

_evernoteBrokenCssFragments = (
    r'position:(?:absolute|fixed);(?:top:-10000px;)?(?:height|width):[01]px;(?:width|height):[01]px',
    r'overflow:hidden|position:fixed;top:0px;left:0px',
    r'opacity:0',
    r'display:none !important',
)
evernoteStyleCleanerExpr = re.compile(r'([ \t\r\n]style[ \t\r\n]*=[ \t\r\n]*"[^"]*)(?:%s)([^"]*")' % '|'.join(_evernoteBrokenCssFragments), re.I)
jsonFilenameToPickleExpr = re.compile(r'^(.*)\.json$', re.I)
jsonFilenameToPickle = lambda filename: jsonFilenameToPickleExpr.subn(r'\1.pickle', filename, 1)[0]

class Note(object):
    def __init__(self, id, data, obj):
        self.id = id
        self.data = data
        self.obj = obj
        self.createdTs = datetime.datetime.fromtimestamp(self.data['created']/1000.0)

        self.content = base64.b64decode(self.data['b64Content']).decode('utf-8')

        # Cleanup Evernote's poor clipping CSS butchery.
        last = ''
        while last != self.content:
            last = self.content
            self.content = evernoteStyleCleanerExpr.sub(r'\1\2', self.content)

        # print self.data.keys() #dir(self.data)
        # print self.data['tagNames']

        self.data['title'] = BeautifulSoup(self.data['title'], 'html.parser', from_encoding='iso8859-15').string
        tagStrings = map(lambda tag: tag['name'].encode('utf-8'), self.data.get('tags', []))
        self.data['urlencoded_query'] = urllib.quote_plus('%s %s' % (self.data['title'].encode('utf-8'), ' '.join(tagStrings)))

    def __getattr__(self, attr):
        """Pass-through to `data` keys when requrested attribute is not available."""
        if attr in self.__dict__:
            return getattr(self, attr)

        if attr in self.data:
            return self.data[attr]

        if hasattr(self.obj, attr):
            return getattr(self.obj, attr)

        raise AttributeError("'Note' object has no attribute '{0}'".format(attr))

    def resourceFilenameTuples(self):
        out = []
        if not self.resources:
            return out
        for i, resource in enumerate(self.resources):
            ext = resource.mime[resource.mime.index('/') + 1:] if resource.mime and '/' in resource.mime else 'dat'
            filename = '%s-%s.%s' % (self.guid, i, ext)
            out.append((resource, filename))
        return out

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
        self.assetsRelPubPath = '../assets'

        def contentWithTranslatedAssets(note):
            content = note.content
            # Replace media objects in content with ones that actually exist :)
            resourcesAndFilenames = list(note.resourceFilenameTuples())
            i = 1
            numAssets = len(resourcesAndFilenames)
            for resource, filename in resourcesAndFilenames:
                if filename.lower().endswith('.pdf'):
                    replacementMarkup = '<a href="%s/%s">View PDF: %s </a> (Asset %s/%s)' % (self.assetsRelPubPath, filename, filename, i, numAssets)
                else:
                    replacementMarkup = '<a href="%s/%s"><img src="%s/%s" alt="Image (Asset %s/%s) alt="Image (Asset %s/%s)" /></a>' % (self.assetsRelPubPath, filename, self.assetsRelPubPath, filename, i, numAssets, i, numAssets)
                content = re.subn(r'<en-media(?:[^\/]|\/[^>])+/>', replacementMarkup, content, 1)[0]
                # TODO: investigate "recognition" later.  Looks like it is iamge OCR.
                #if resource.recognition:
                #    content += resource.recognition.body
                i += 1
            return content
        jinja2.filters.FILTERS['contentWithTranslatedAssets'] = contentWithTranslatedAssets

        self.env = jinja2.environment.Environment()
        self.templates = dict((name[10:], open(name, 'rb').read()) for name in glob.glob('templates/*.html'))
        self.env.loader = jinja2.DictLoader(self.templates)

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
            #if '1467328549000' not in path:
            #    continue
            jsonFileName = path[path.rindex('/') + 1:]
            destination = '{0}/api/{1}'.format(settings.OUTPUT_PATH, jsonFileName)
            shutil.copyfile(path, destination)

            with open(path, 'r') as fh:
                data = json.load(fh)

            with open(jsonFilenameToPickle(path), 'r') as fh:
                obj = pickle.load(fh)

            noteId = jsonFileName[0:jsonFileName.index('.')]
            note = Note(noteId, data, obj)
            listing.append(note)

        notes = sorted(
            filter(
                lambda note: note.deleted is not True,
                listing,
            ),
            key=lambda note: note.createdTs,
            reverse=True,
        )

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
                    tag['name'] = unidecode(safeUnicode(tag['name'].lower()))
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
        """Render a template and dump corresponding assets."""
        t = self.env.get_template(template)
        if 'note' in kw:
            self.dumpAssets(kw['note'])
        rendered = t.render(**kw)
        with open('{0}/{1}'.format(settings.OUTPUT_PATH, targetFile), 'w') as fh:
            fh.write(rendered.encode('utf-8'))

    def dumpAssets(self, note):
        assetsPath = settings.OUTPUT_PATH + '/assets'
        if not os.path.exists(assetsPath):
            os.makedirs(assetsPath)
        for resource, filename in note.resourceFilenameTuples():
            with open('%s/%s' % (assetsPath, filename), 'wb') as fh:
                fh.write(resource.data.body)

