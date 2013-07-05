# -*- coding: utf-8 -*-

"""
EverNote WebClipper publisher.

@author Jay Taylor [@jtaylor]
@date 2013-06-30
"""

def fileGetContents(fileName, flags='r'):
    with open(fileName, flags) as fh:
        return fh.read()

