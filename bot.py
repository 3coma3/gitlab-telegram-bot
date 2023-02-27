#!/usr/bin/env python

import json
import requests
import time

from threading import Thread


class Bot:
    def __init__(self):
        try:
            with open(self.configFile, "r") as cf:
                self.config = json.load(cf)
                print("Successfully read configuration")
        except:
            raise Exception("Couldn't read configuration")

        self.api = 'https://api.telegram.org/bot{0}/'\
                   .format(self.config.get('api_token'))
        self.defaults = self.config.get('defaults', {})
        self.state = self.config.get('state', {})
        self.config['state'] = self.state
        self.me = self.botq('getMe')['result']
        self.running = False

    def botq(self, method, params=None):
        url = self.api + method
        params = params if params else {}
        return requests.post(url, params).json()

    def msg_recv(self, msg):
        ''' method to override '''
        pass
    def save_config(self):
        try:
            with open(self.configFile, "w") as cf:
                json.dump(self.config, cf, indent=2, sort_keys=False)
                cf.write("\n")
                cf.close()
        except:
            raise Exception("Couldn't write configuration")

    def text_recv(self, txt, chatid):
        ''' method to override '''
        pass

    def updates(self):
        r = self.botq('getUpdates', {'offset': self.offset})

        for up in r['result']:
            self.offset = up['update_id'] + 1

            if 'message' in up:
                self.msg_recv(up['message'])
            elif 'edited_message' in up:
                self.msg_recv(up['edited_message'])
            else:
                # not a valid message
                break

            try:
                txt = up['message']['text']
                self.text_recv(txt, self.get_to_from_msg(up['message']))

            except:
                pass

        open('offset', 'w').write('%s' % self.offset)

    def get_to_from_msg(self, msg):
        to = ''
        try:
            to = msg['chat']['id']
        except:
            to = ''
        return to

    def reply(self, to, msg):
        if type(to) not in [int, str]:
            to = self.get_to_from_msg(to)

        resp = self.botq('sendMessage', {'chat_id': to, 'text': msg, 'disable_web_page_preview': True, 'parse_mode': 'Markdown'})
        return resp

    def run(self):
        self.running = True
        while self.running:
            self.updates()
            time.sleep(1)

    def run_threaded(self):
        t = Thread(target=self.run)
        t.start()

    def stop(self):
        self.running = False


if __name__ == '__main__':
    bot = Bot()
    bot.run()
