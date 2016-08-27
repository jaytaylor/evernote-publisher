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

# CSS scrubber expressions.
_evernoteBrokenCssFragments = (
    r'position:(?:absolute|fixed);(?:top:-10000px;)?(?:height|width):[01]px;(?:width|height):[01]px',
    r'overflow:hidden|position:fixed;top:0px;left:0px', # GitHub.
    r'opacity:0',                                       # GitHub.
    r'box-sizing:border-box;float:right',               # GitHub.
    r'position:static;visibility:visible;width:61px;height:20px;', # GitHub/Twitter tweet button.
    r'display:none !important',
    r'(?:left|top):0px;(?:left|top):0px;width:100%;height:0px', # StackOverflow.
    r'position:fixed;margin:0px;border:0px;padding:0px',        # StackOverflow.
    r'rgb\(255, 255, 255\);position:fixed;left:0px;width:100%',                                                      # Quora.
    r'float:left;height:16px;width:14px;',                                                                           # Quora.
    r'display:table;width:100%;padding-left:88px;box-sizing:border-box',                                             # Quora.
    r'z-index:800(?:[^"]*(?:background|color): *rgb\(255, *255, *255\))+',                                           # Quora.
    r'filter:url\(http:\/\/gigaom.com\/wp-content\/themes\/vip\/gigaom5\/css\/img\/post-page-blur.svg#blur\);margin:0px;bottom:0px;-webkit-filter:blur\(5px\)',          # Gigaom.
    r'left:0px;position:absolute;right:0px;background:rgb\(255, 255, 255\)',                                                                                             # Gigaom.
    r'bottom:0px;left:0px;position:absolute;right:0px;top:0px;background:rgba\(0, 0, 0, 0.498039\)',                                                                     # Gigaom.
    r'overflow-x:auto',   # Never good.
    r'overflow-y:scroll', # Never good.
    r'''height:12px;width:12px;background-image:url\(['"]?[^\)]*facebook\.com\/rsrc\.php[^\)]*\)''', # Facebook.
    r'background:transparent;box-sizing:border-box;width:100%;left:0px;top:0px;height:75px;position:fixed;z-index:10101;display:block;vertical-align:baseline;', # LifeHacker.
#:    r'color:rgb\(255, 255, 255\);position:fixed;left:0px;width:100%;min-height:53px;box-sizing:border-box;z-index:800;font-size:14px;top:0px',  # Quora.
)
evernoteStyleCleanerExpr = re.compile(r'([ \t\r\n]style[ \t\r\n]*=[ \t\r\n]*"[^"]*)(?:%s)([^"]*")' % r'|'.join(_evernoteBrokenCssFragments), re.I)

jsonFilenameToPickleExpr = re.compile(r'^(.*)\.json$', re.I)
jsonFilenameToPickle = lambda filename: jsonFilenameToPickleExpr.subn(r'\1.pickle', filename, 1)[0]

class Note(object):
    def __init__(self, id, data, obj):
        self.id = id
        self.data = data
        self.obj = obj
        self.createdTs = datetime.datetime.fromtimestamp(self.data['created']/1000.0)

        self.content = base64.b64decode(self.data['b64Content']).decode('utf-8').replace('evernote', 'note')

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
        """Pass-through from self to `data` keys and then `object' attributes."""
        if attr in self.__dict__:
            return getattr(self, attr)

        if attr in self.data:
            return self.data[attr]

        if hasattr(self.obj, attr):
            return getattr(self.obj, attr)

        if hasattr(self.obj.attributes, attr):
            return getattr(self.obj.attributes, attr)

        raise AttributeError("'Note' object has no attribute '{0}'".format(attr))

    @property
    def sourceUrl(self):
        sourceUrl = self.sourceURL
        if not sourceUrl:
            return ''
        return sourceUrl

    @property
    def sourceDomain(self):
        if not self.sourceUrl:
            return ''
        domain = re.sub(r'^(?:(?:http:)?//)?([^/]+).*$', r'\1', self.sourceUrl, re.I)
        return domain

    @property
    def sourceDomainUrl(self):
        if not self.sourceUrl:
            return ''
        protocol = 'http%s' % ('s' if self.sourceUrl.lower().startswith('https') else '')
        domainUrl = '%s://%s/' % (protocol, self.sourceDomain)
        return domainUrl

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
                relPath = '%s/%s' % (self.assetsRelPubPath, filename)
                filenameLower = filename.lower()
                if filenameLower.endswith('.pdf'):
                    replacementMarkup = '<a href="%s">View PDF: %s </a> (Asset %s/%s)' % (relPath, filename, i, numAssets)
                elif filenameLower.endswith('.octet-stream') and resource.data.body[0:3].lower().startswith('<svg'):
                    replacementMarkup = resource.data.body
                else:
                    replacementMarkup = '<a href="%s"><img src="%s" alt="Image (Asset %s/%s) alt="Image (Asset %s/%s)" /></a>' % (relPath, relPath, i, numAssets, i, numAssets)
                content = re.subn(r'<en-media(?:[^\/]|\/[^>])+/>', replacementMarkup, content, 1)[0]
                # TODO: investigate "recognition" later.  Looks like it is image OCR, pretty cool!.
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

        # environment-variable based override for development/testing purposes.
        onlyNodeId = os.environ.get('ONLY_NODE_ID')
        for path in dataFiles:
            if onlyNodeId and onlyNodeId not in path:
                continue
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

