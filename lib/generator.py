# -*- coding: utf-8 -*-

"""Note renderer."""

import simplejson as json, glob, settings, shutil, unicodedata
from .util import fileGetContents

try:
    import cPickle as pickle
except ImportError:
    import pickle


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


def generate():
    """Read and render Note data."""
    listing = []
    dataFiles = glob.iglob('{0}/*.json'.format(settings.DATA_PATH))
    for path in dataFiles:
        jsonFileName = path[path.rindex('/')+1:]
        destination = '{0}/api/{1}'.format(settings.OUTPUT_PATH, jsonFileName)
        shutil.copyfile(path, destination)

        with open(path, 'r') as fh:
            data = json.load(fh)
        listing.append({'id': jsonFileName[0:jsonFileName.index('.')], 'data': data})

    makeIndex(listing)
    
    #serializedDataFiles = glob.iglob('{0}/*.pickle'.format(settings.DATA_PATH))
    #for fileName in serializedDataFiles:
    #    renderNote(fileName)

def makeIndex(listingData):
    """Create static index."""
    out = u'<html>\n<head>\n<title>Jays evernotes</title>\n</head>\n<body>\n'

    out += u'<div class="content">\n<ul>'
    for entry in listingData:
        #title = unicodedata.normalize('NFKD', unicode(entry['data']['title']))
        b = entry['data']['title']#.decode('unicode-escape')
        print b
        a = u'{0}'.format(b)
        title = a #a.encode('utf-8')
        print type(a),'->',type(title), title
        out += u'<li><a href="view.php?id={0}">{1}</a></li>\n'.format(entry['id'], title)
    out += u'</ul></div>\n'

    out += u'<div class="footer">Powered by <a href="https://github.com/jaytaylor/evernote-publisher">Evernote Publisher</a></div>\n'
    out += u'</body>\n</html>'

    with open('{0}/index.html'.format(settings.OUTPUT_PATH), 'w') as fh:
        fh.write(out.encode('utf-8'))


