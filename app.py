#!/usr/bin/env python3

import atexit
import re
import signal
import time

from flask import Flask, request, jsonify

from bot import Bot
from formatters import eventFormatters as fmt
from util import digest, dumpjson, new_secret, strange, tdif, timestamp as ts


# formatted string from a dictionary
def msg(*args):
    return {
        'online': "I'm online \U0001F44B",
        'offline': "I'm going away for a while. Laters! \U0001F596",
        'help': "Available commands:",
        'ok': "Allright! \U0001F60E",
        'cmd_unknown': "What? \U0001F633",
        'cmd_private': "This is a PM-only command \U0001F610",
        'sorry_owner': "I'm sorry Dave, I'm afraid I can't do that \U0001F916",
        'arg_few': "I need more info \U0001F914",
        'arg_extra': "I didn't understand this \"{0}\" \U0001F914",
        'otp_list': "Here's the list of tokens:\n```\n{0}```\n",
        'otp_new': "Ok! New token: {0}\n\ntype {1}\nexpires in {2}",
        'otp_remove': "Ok! Deleted {0} token{1}",
        'otp_flush': "Done! We have 0 tokens pending",
        'otp_bad_type': "Can't use that token here",
        'otp_bad_lifetime': "Wrong lifetime, must be between {0} and {1}",
        'chg_list': "Here's the list of challenges:\n```\n{0}```\n",
        'chg_new': "You have {0} to complete the challenge \U0001FE0F",
        'chgp_remove': "Ok! Deleted {0} challenge{1}",
        'chg_flush': "Done! We have 0 challenges pending",
        'chg_unknown': "Hmm maybe forgot to /start? \U0001F9D0",
        'chat_list': "Here's the list of chats:\n```\n{0}```\n",
        'chat_auth': "\U0001F60E Ok, authorized!",
        'chat_aauth': "\U0001F913 already authorized!",
        'chat_deauth': "\U0001F60E Ok, deauthorized!",
        'chat_leave': "I'll leave in {0} minutes if I'm not requested before.",
        'chat_unauth': "\U0001F612 go away.",
        'chat_quiet': "Going quiet now \U0001F910",
        'chat_unknown': "I don't know that chat \U0001F914",
        'owner_list': "Here's the list of bot owners:\n```\n{0}```\n",
        'owner_remove': "Ok! {0} owner{1} gone",
        'bot_auth': "\U0001F60E You're the boss!",
        'bot_aauth': "Hi again boss \U0001F913"
    }.get(args[0], args[0]).format(*args[1:])


class GitlabBot(Bot):
    def __init__(self):
        self.configFile = 'config.json'
        super(GitlabBot, self).__init__()

        self.owners = self.state.get('owners', [])
        self.chats = self.state.get('chats', [])
        self.otp = self.state.get('otp', [])
        self.state['owners'] = self.owners
        self.state['chats'] = self.chats
        self.state['otp'] = self.otp

        self.challenges = []

        self.broadcast(msg('online'))

    def broadcast(self, m):
        if m:
            for c in self.chats:
                if c['authorized'] and not c['quiet']:
                    self.reply(c['id'], m)

    def user_entry(self, u):
        return {'id': u['id'],
                'name': u.get('username', u.get('name', u.get('title', '')))}

    def update_chat(self, c):
        c['admins'] = []

        if c['type'] == 'private':
            c['owner'] = self.user_entry(c)
            return

        for a in self.get_chat_admins(c):
            if (a['status'] == 'administrator' and a['can_promote_members']):
                c['admins'].append = self.user_entry(a['user'])

            elif a['status'] == 'creator':
                c['owner'] = self.user_entry(a['user'])

    def refresh(self):
        save_config = False

        def iter(f, xs):
            for i, x in enumerate(xs):
                if f(x):
                    del xs[i]
                    nonlocal save_config
                    save_config = True

        def expired(o):
            return int(time.time()) > o['refresh']

        def chat(c):
            if (not c['authorized']) and expired(c):
                self.botq('leaveChat', {'chat_id': c['id']})
                return True

            if (not c['authorized']) or expired(c):
                self.update_chat(c)
                if c['authorized']:
                    c['refresh'] = ts(self.defaults.get('chat_lifetime', 1))
                nonlocal save_config
                save_config = True

        iter(expired, self.challenges)
        iter(expired, self.otp)
        iter(chat, self.chats)

        if save_config:
            self.save_config()

    def cache_chat(self, c):
        cached = next((cc for cc in self.chats if cc['id'] == c['id']), None)
        if cached:
            return cached

        c['refresh'] = ts(self.defaults.get('chat_lifetime', 1))
        c['authorized'] = False
        c['quiet'] = True
        self.chats.append(c)
        self.update_chat(c)
        return c

    def msg_recv(self, m):
        chat = self.get_chat(m)

        if 'text' in m:
            self.txt_recv(m['text'], chat, m.get('from', m.get('sender_chat', '')))
            self.save_config()

        elif 'new_chat_participant' in m\
             and m['new_chat_participant']['username'] == self.me['username']:
            self.cache_chat(chat)

    def txt_recv(self, txt, chat, from_):
        args = (txt[1:] if txt.startswith('/') else txt).strip().split()
        cmd = re.sub(r'[^@]\([@][^ ]+\)$', '', args.pop(0))

        def target_chat(cid=None):
            if not cid:
                return self.cache_chat(chat)

            if type(cid) is list:
                cid = cid[0]

            key = 'id'
            if type(cid) is str:
                if cid[1:].isdecimal():
                    cid = int(cid)
                else:
                    key = 'name'

            return next((c for c in self.chats if c[key] == cid), None)

        def bot_owner():
            return any(owner['id'] == from_['id'] for owner in self.owners)

        def chat_owner(chat):
            return self.cache_chat(chat)['owner']['id'] == from_['id']

        def chat_admin(chat):
            return any(admin['id'] == from_['id']
                       for admin in self.cache_chat(chat)['admins'])

        def is_privileged(chat):
            return bot_owner() or chat_owner(chat) or chat_admin(chat)

        def check_args(min=0, max=0):
            if len(args) < min:
                self.reply(chat, msg('arg_few'))
            elif len(args) > max:
                self.reply(chat, msg('arg_extra', ' '.join(args)))
            else:
                return True

        def check_owner_cmd(min=0, max=0):
            if not bot_owner():
                self.reply(chat, msg('chat_unauth'))

            elif chat['type'] != 'private':
                self.reply(chat, msg('cmd_private'))

            else:
                return check_args(min, max)

        if cmd == 'lsotp':
            if check_owner_cmd():
                self.reply(chat, msg('otp_list', dumpjson(self.otp)))

        elif cmd == 'getotp':
            if not check_owner_cmd(max=2):
                return

            type_ = lifetime = None
            for arg in args:
                if not type_ and arg in ['owner', 'private', 'group', 'channel']:
                    type_ = arg

                elif not lifetime and arg.isdecimal():
                    if (1 <= int(arg) <= 1440):
                        lifetime = int(arg)
                        continue
                    return self.reply(chat, msg('otp_bad_lifetime', 1, 1440))

                else:
                    return self.reply(chat, msg('arg_extra', arg))

            secret = new_secret(8)
            otp = {
                'secret': digest(secret),
                'type': type_ or self.defaults.get('otp_type', 'private'),
                'refresh': ts(lifetime or self.defaults.get('otp_lifetime', 1))
            }
            self.otp.append(otp)
            self.reply(chat, msg('otp_new', secret, otp['type'],
                                 tdif(otp['refresh'])))

        elif cmd == 'delotp':
            if not check_owner_cmd(min=1, max=1):
                return

            r = strange(args[0])
            if not r:
                return self.reply(chat, msg('arg_extra', args[0]))

            n = 0
            for i in sorted(r, reverse=True):
                if i < len(self.otp):
                    n += 1
                    del self.otp[i]
            self.reply(chat, msg('otp_remove', n, '' if n == 1 else 's'))

        elif cmd == 'flushotp':
            if check_owner_cmd():
                self.otp.clear()
                self.reply(chat, msg('otp_flush'))

        elif cmd == 'lschg':
            if check_owner_cmd():
                self.reply(chat, msg('chg_list', dumpjson(self.challenges)))

        elif cmd == 'delchg':
            if not check_owner_cmd(min=1, max=1):
                return

            r = strange(args[0])
            if not r:
                return self.reply(chat, msg('arg_extra', args[0]))

            n = 0
            for i in sorted(r, reverse=True):
                if i < len(self.challenges):
                    n += 1
                    del self.challenges[i]
            self.reply(chat, msg('chg_remove', n, '' if n == 1 else 's'))

        elif cmd == 'flushchg':
            if check_owner_cmd():
                self.challenges.clear()
                self.reply(chat, msg('chg_flush'))

        elif cmd == 'lsowner':
            if check_owner_cmd():
                self.reply(chat,
                           msg('owner_list', dumpjson(self.owners)))

        elif cmd == 'delowner':
            if not check_owner_cmd(min=1, max=1):
                return

            r = strange(args[0])
            if not r:
                return self.reply(chat, msg('arg_extra', args[0]))

            n = 0
            for i in sorted(r, reverse=True):
                if i < len(self.owners):
                    n += 1
                    del self.owners[i]
            self.reply(chat, msg('owner_remove', n, '' if n == 1 else 's'))

        elif cmd == 'start':
            if not check_args(max=1):
                return

            tc = target_chat(args)
            if not tc:
                return self.reply(chat, msg('chat_unknown'))

            if not is_privileged(tc):
                return self.reply(chat, msg('chat_unauth'))

            if (tc['authorized']):
                return self.reply(chat, msg('chat_aauth'))

            if bot_owner():
                tc['authorized'] = True
                tc['quiet'] = False
                return self.reply(chat, msg('chat_auth'))

            chg = next((c for c in self.challenges
                        if c['cid'] == tc['id'] and c['uid'] == from_['id']),
                       None)
            if not chg:
                chg = {
                    'cid': tc['id'],
                    'uid': from_['id'],
                    'refresh': ts(self.defaults.get('challenge_lifetime', 1))
                }
                self.challenges.append(chg)

            self.reply(chat, msg('chg_new', tdif(chg['refresh'])))

        elif cmd == 'auth':
            if not check_args(min=1, max=2):
                return

            cid = secret = None
            for arg in args:
                if arg.isdecimal() and not cid:
                    cid = arg
                    continue

                elif not secret:
                    secret = digest(arg)
                    continue

                else:
                    return self.reply(chat, msg('arg_extra', arg))

            tc = target_chat(cid)
            if not tc:
                return self.reply(chat, msg('chat_unknown'))

            otp = next((t for t in self.otp
                        if t['secret'] == secret and t['type'] == 'owner'),
                       None)

            chg = next((c for c in self.challenges
                        if c['cid'] == tc['id'] and c['uid'] == from_['id']),
                       None)

            if (tc['id'] == chat['id'] and (otp or secret == digest(self.config['api_token']))):
                if bot_owner():
                    return self.reply(chat, msg('bot_aauth'))
                if otp:
                    otp['refresh'] = 0
                if chg:
                    chg['refresh'] = 0
                if tc['type'] != 'private':
                    tc['authorized'] = True
                self.owners.append(self.user_entry(from_))
                return self.reply(chat, msg('bot_auth'))

            if tc['authorized']:
                return self.reply(chat, msg('chat_aauth'))

            if not chg:
                return self.reply(chat, msg('chg_unknown'))

            otp = next((t for t in self.otp
                        if t['secret'] == secret and t['type'] == tc['type']),
                       None)
            if not otp:
                return self.reply(chat, msg('otp_bad_type'))

            tc['authorized'] = True
            tc['quiet'] = False
            otp['refresh'] = 0
            chg['refresh'] = 0
            return self.reply(chat, msg('chat_auth'))

        elif cmd == 'stop':
            if not check_args(max=1):
                return

            tc = target_chat(args)
            if not tc:
                return self.reply(chat, msg('chat_unknown'))

            if tc['authorized'] and is_privileged(tc):
                tc['authorized'] = False
                tc['quiet'] = True
                tc['refresh'] = ts(10)
                self.reply(chat, msg('chat_deauth'))
                if tc['type'] != 'private':
                    self.reply(chat, msg('chat_leave', tdif(tc['refresh'])))
            elif bot_owner():
                self.reply(chat, msg('sorry_owner'))
            else:
                self.reply(chat, msg('chat_unauth'))

        elif cmd == 'lschat':
            if chat['type'] != 'private':
                return self.reply(chat, msg('cmd_private'))

            if not check_args():
                return

            chats = self.chats if bot_owner() else\
                [c for c in self.chats if chat_owner(c) or chat_admin(c)]

            self.reply(chat, msg('chat_list', dumpjson(chats)))

        elif cmd == 'quiet':
            if not check_args(max=1):
                return

            tc = target_chat(args)
            if not tc:
                return self.reply(chat, msg('chat_unknown'))

            if not (tc['authorized'] and is_privileged(tc)):
                if bot_owner():
                    self.reply(chat, msg('sorry_owner'))
                else:
                    self.reply(chat, msg('chat_unauth'))
            else:
                tc['quiet'] = True
                self.reply(chat, msg('chat_quiet'))

        elif cmd == 'speak':
            if not check_args(max=1):
                return

            tc = target_chat(args)
            if not tc:
                return self.reply(chat, msg('chat_unknown'))

            if not (tc['authorized'] and is_privileged(tc)):
                if bot_owner():
                    self.reply(chat, msg('sorry_owner'))
                else:
                    self.reply(chat, msg('chat_unauth'))
            else:
                tc['quiet'] = False
                self.reply(chat, msg('ok'))

        else:
            if is_privileged(chat):
                return self.reply(chat, msg('cmd_unknown'))

            else:
                return self.reply(chat, msg('chat_unauth'))


bot = GitlabBot()
app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
def webhook():

    if (request.headers.get('X-Gitlab-Token', None) != bot.config.get('svc_token', None)):
        return jsonify({'status': 'unauthorized'}), 401

    data = request.json

    # print('DEBUG =================\n' + dumpjson(data))

    event = '(could not detect event type)'
    for e in ['object_kind', 'event_type', 'event_name']:
        if e in data:
            event = data[e]
            break

    # TODO: move string to msg
    def nofmt():
        return 'New event "*{0}*" without formmater, write one for me!\n```\n{1}```\n'\
               .format(event, dumpjson(data))

    bot.broadcast(fmt.get(event, lambda _: nofmt())(data))

    return jsonify({'status': 'ok'})


def exit():
    bot.broadcast(msg('offline'))


if __name__ == "__main__":
    atexit.register(exit)
    signal.signal(signal.SIGTERM, exit)
    signal.signal(signal.SIGINT, exit)

    bot.run_threaded()
    [host, port] = bot.config.get('listen', '0.0.0.0:10111').split(':')
    app.run(host=host, port=port)
