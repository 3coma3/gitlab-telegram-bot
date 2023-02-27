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

    def save_config(self):
        try:
            with open(self.configFile, "w") as cf:
                json.dump(self.config, cf, indent=2, sort_keys=False)
                cf.write("\n")
                cf.close()
        except:
            raise Exception("Couldn't write configuration")

    def refresh(self):
        ''' abstract'''
        pass

    def msg_recv(self, m):
        ''' abstract'''
        pass

    def get_updates(self):
        r = self.botq('getUpdates', {'offset': self.state.get('offset', 0)})

        for update in r['result']:
            self.state['offset'] = update['update_id'] + 1

            for u in [p + t for p in ['', 'edited']
                      for t in ['message', 'channel_post']]:
                if u in update:
                    self.msg_recv(update[u])

    def get_chat(self, msg):
        c = msg.get('chat', msg)
        return {
            'id': c['id'],
            'type': c['type'],
            'name': c.get('username', c.get('name', c.get('title')))
        }

    def get_chat_admins(self, c):
        r = self.botq('getChatAdministrators', {'chat_id': c['id']})
        return r['result']

    def reply(self, to, msg):
        if type(to) not in [int, str]:
            to = self.get_chat(to)['id']

        return self.botq('sendMessage',
                         {
                             'chat_id': to,
                             'text': msg,
                             'disable_web_page_preview': True,
                             'parse_mode': 'Markdown'
                         })

    def run(self):
        self.running = True
        while self.running:
            self.get_updates()
            self.refresh()
            time.sleep(1)

    def run_threaded(self):
        t = Thread(target=self.run)
        t.start()

    def stop(self):
        self.running = False


if __name__ == '__main__':
    bot = Bot()
    bot.run()
