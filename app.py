#!/usr/bin/env python3

import atexit
import signal

from flask import Flask, request, json, jsonify

from bot import Bot
from formatters import eventFormatters as fmt


class GitlabBot(Bot):
    def __init__(self):
        try:
            self.authmsg = open('authmsg').read().strip()
        except:
            raise Exception("The authorization messsage file is invalid")

        super(GitlabBot, self).__init__()
        self.chats = {}
        try:
            chats = open('chats', 'r').read()
            self.chats = json.loads(chats)
        except:
            open('chats', 'w').write(json.dumps(self.chats))

        self.send_to_all("I'm online \U0001F44B")

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
        for c in self.chats:
            self.reply(c, msg)


bot = GitlabBot()
app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
def webhook():
    data = request.json

    print('DEBUG =================\n' + json.dumps(data, indent=2))

    if 'object_kind' in data:
        event = data['object_kind']
    elif 'event_type' in data:
        event = data['event_type']
    elif 'event_name' in data:
        event = data['event_name']
    else:
        event = '(could not detect the type)'

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
