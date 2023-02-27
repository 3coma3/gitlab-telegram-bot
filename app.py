#!/usr/bin/env python3

import atexit
import signal

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

    def text_recv(self, txt, chatid):
        ''' registering chats '''
        txt = txt.strip()
        if txt.startswith('/'):
            txt = txt[1:]

        print(txt)

        if txt == self.authmsg:
            if str(chatid) in self.chats:
                self.reply(chatid, "\U0001F913 you were already authorized, but thanks!")
            else:
                self.reply(chatid, "\U0001F60E ok, authorized!")
                self.chats[chatid] = True
                open('chats', 'w').write(json.dumps(self.chats))

        elif txt == 'shutup':
            self.reply(chatid, "Going quiet now. \U0001F634")
            del self.chats[chatid]
            open('chats', 'w').write(json.dumps(self.chats))

        else:
            self.reply(chatid, "\U0001F612 go away.")



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
