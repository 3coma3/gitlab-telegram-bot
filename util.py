#!/usr/bin/env python

from hashlib import sha256
import secrets
import string
import time

from flask import json


def digest(string):
    return sha256(string.encode()).hexdigest()


# shortcut to json.dumps with friendlier formatting for lists and timestamps
def dumpjson(o):
    def fmt(o):
        return {k: (v if k != 'refresh' else 'in ' + tdif(v))
                for k, v in o.items()}

    if type(o) is list:
        return ('(no entries)' if not o
                else '\n'.join([str(i) + ': ' + json.dumps(fmt(x), indent=2)
                                for i, x in enumerate(o)]))

    return json.dumps(o, indent=2)


# generate a secret
def new_secret(length):
    charset = string.ascii_letters + string.digits
    while True:
        s = ''.join(secrets.choice(charset) for _ in range(length))
        if (any(char.islower() for char in s)
                and any(char.isupper() for char in s)
                and sum(char.isdecimal() for char in s) >= 3):
            return s


# string to range
def strange(s):
    r = []
    try:
        for x in s.split(','):
            *xs, = x.split('-')
            xs = list(sorted(map(int, xs)))
            r.extend(list(range(xs[0], xs[-1] + 1, 1)))
    except:
        return None

    return sorted(list(set(r)))


# human-friendly timestamp difference
def tdif(t1, t2=None):
    [t1, t2] = sorted(map(int, [t1, t2 or time.time()]))
    d, h = divmod(t2 - t1, 86400)
    h, m = divmod(h, 3600)
    m, s = divmod(m, 60)
    s, _ = divmod(s, 1)

    t = [[k, v] for k, v
         in zip(['day', 'hour', 'minute', 'second'], [d, h, m, s])
         if v]

    def cont(i):
        if not i:
            return ''
        return ', ' if i < len(t) - 1 else ' and '

    r = ''
    for i, [k, v] in enumerate(t):
        r += '{0}{1} {2}{3}'.format(cont(i), v, k, '' if v == 1 else 's')
    return r


def timestamp(lifetime):
    return int(time.time()) + lifetime * 60
