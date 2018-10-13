#!/usr/bin/python3
from datetime import datetime

def log(text, *args):
    output = str(text)
    for arg in args:
        output += ' ' + str(arg)
    print('[{:%Y-%m-%d %H:%M:%S}]: {}'.format(datetime.now(), text))