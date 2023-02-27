#!/usr/bin/env python3

import atexit
import signal

from flask import Flask, request, jsonify

from bot import Bot
from formatters import eventFormatters as fmt
from util import digest, dumpjson, new_secret, strange, tdif, timestamp as ts


class GitlabBot(Bot):
    def __init__(self):
        self.configFile = 'config.json'
        super(GitlabBot, self).__init__()

        self.send_to_all("I'm online \U0001F44B")
        self.owners = self.state.get('owners', [])
        self.chats = self.state.get('chats', [])
        self.otp = self.state.get('otp', [])
        self.state['owners'] = self.owners
        self.state['chats'] = self.chats
        self.state['otp'] = self.otp

        self.challenges = []

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

    def send_to_all(self, msg):
        if msg:
            for c in self.chats:
                self.reply(c, msg)


bot = GitlabBot()
app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
def webhook():
    data = request.json

    print('DEBUG =================\n' + json.dumps(data, indent=2))

    event = '(could not detect event type)'
    for e in ['object_kind', 'event_type', 'event_name']:
        if e in data:
            event = data[e]
            break

    def nofmt():
        return 'New event "*{0}*" without formmater, write one for me!\n```\n{1}```\n'\
               .format(event, json.dumps(data, indent=2))

    bot.send_to_all(fmt.get(event, lambda _: nofmt())(data))

    return jsonify({'status': 'ok'})


def exit():
    bot.send_to_all("I'm going away for a while. Laters! \U0001F596")


if __name__ == "__main__":
    atexit.register(exit)
    signal.signal(signal.SIGTERM, exit)
    signal.signal(signal.SIGINT, exit)

    bot.run_threaded()
    app.run(host='0.0.0.0', port=10111)
