#!/usr/bin/env python
# -*- coding: utf-8 -*-

import BaseHTTPServer
import SimpleHTTPServer
import sys

def run(handlerClass=SimpleHTTPServer.SimpleHTTPRequestHandler, protocol='HTTP/1.0'):
    if sys.argv[1:]:
        port = int(sys.argv[1])
    else:
        port = 8000
    server_address = ('', port)

    handlerClass.protocol_version = protocol
    httpd = BaseHTTPServer.HTTPServer(server_address, handlerClass)

    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()


if __name__ == '__main__':
    run()

