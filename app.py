#!/usr/bin/env python3

import json
import re

from flask import Flask
from flask import request
from flask import jsonify
from bot import Bot
app = Flask(__name__)

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

        self.send_to_all('Hi!')

    def text_recv(self, txt, chatid):
        ''' registering chats '''
        txt = txt.strip()
        if txt.startswith('/'):
            txt = txt[1:]

        print(txt)

        if txt == self.authmsg:
            if str(chatid) in self.chats:
                self.reply(chatid, "\U0001F60E  boy, you already got the power.")
            else:
                self.reply(chatid, "\U0001F60E  Ok boy, you got the power !")
                self.chats[chatid] = True
                open('chats', 'w').write(json.dumps(self.chats))

        elif txt == 'shutupbot':
            del self.chats[chatid]
            self.reply(chatid, "\U0001F63F Ok, take it easy\nbye.")
            open('chats', 'w').write(json.dumps(self.chats))

        else:
            self.reply(chatid, "\U0001F612 I won't talk to you.")

    def send_to_all(self, msg):
        for c in self.chats:
            self.reply(c, msg)

b = GitlabBot()

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

    if event == 'repository_update':
        msg = formatRepoUpdateMsg(data)
    elif event == 'push':
        msg = formatPushMsg(data)
    else:
        msg = 'New event "' + event + '" without formatter, write one for me!\n```\n' + json.dumps(data, indent=2) + '```'

    b.send_to_all(msg)
    return jsonify({'status': 'ok'})

# this generic event is called from the webooks set by admins (info seems to lack)
def formatRepoUpdateMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    msg = msg + '*{0}* {1}'\
            .format(data['user_name'],\
                    'issued multiple changes\n\n' if len(data['changes']) > 1 else '')

    for change in data['changes']:
        if 'ref' in change:
            refType = re.search(r'/([^/]+)/[^/]+$', change['ref']).group(1)
            refName = re.search(r'/([^/]+)$', change['ref']).group(1)

            if refType == 'tags' and len(data['changes']) > 1:
                if not int('0x' + change['before'], 0):
                    msg = msg + 'tagged object [{0}]({1}/-/commit/{0}) with tag *"{2}"*\n'\
                                .format(change['after'],\
                                        data['project']['web_url'].replace("_", "\_"),\
                                        refName)
                else:
                    msg = msg + 'removed tag *"{0}"* from object [{1}]({2}/-/commit/{1})\n'\
                                .format(refName,\
                                        change['after'],\
                                        data['project']['web_url']).replace("_", "\_")

            elif refType == 'heads':
                if not int('0x' + change['before'], 0):
                    msg = msg + 'created branch [{0}]({1}/-/tree/{0})\n'\
                                .format(refName,\
                                        data['project']['web_url']).replace("_", "\_")

                elif not int('0x' + change['after'], 0):
                    msg = msg + 'removed branch *"{0}"*\n'.format(refName)

                else:
                    msg = msg + 'changed branch *"{0}"*\n'.format(refName)

            else:
                msg = msg + 'update with unknown ref type\n'

    return msg

def formatPushMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    msg = msg + '*{0}* pushed *{1}* new commits to the *{2}* branch\n'\
                .format(data['user_name'],\
                        data['total_commits_count'],\
                        re.search(r'/([^/]+)$', data['ref']).group(1))

    for commit in data['commits']:
        part = commit['message'].rstrip().partition('\n')
        msg = msg + '\n[{0}]({1})\n{2}\n'\
                    .format(part[0],\
                            commit['url'].replace("_", "\_"),\
                            part[2])

    return msg


def generateIssueMsg(data):
    action = data['object_attributes']['action']
    if action == 'open':
        assignees = ''
        for assignee in data.get('assignees', []):
            assignees += assignee['name'] + ' '
        msg = '*{0}* new issue for *{1}*:\n'\
            .format(data['project']['name'], assignees)
    elif action == 'reopen':
        assignees = ''
        for assignee in data.get('assignees', []):
            assignees += assignee['name'] + ' '
        msg = '*{0}* issue re-opened for *{1}*:\n'\
            .format(data['project']['name'], assignees)
    elif action == 'close':
        msg = '*{0}* issue closed by *{1}*:\n'\
            .format(data['project']['name'], data['user']['name'])
    elif action == 'update':
        assignees = ''
        for assignee in data.get('assignees', []):
            assignees += assignee['name'] + ' '
        msg = '*{0}* issue assigned to *{1}*:\n'\
            .format(data['project']['name'], assignees)

    msg = msg + '[{0}]({1})'\
        .format(data['object_attributes']['title'], data['object_attributes']['url'])
    return msg


def generateCommentMsg(data):
    ntype = data['object_attributes']['noteable_type']
    if ntype == 'Commit':
        msg = 'note to commit'
    elif ntype == 'MergeRequest':
        msg = 'note to MergeRequest'
    elif ntype == 'Issue':
        msg = 'note to Issue'
    elif ntype == 'Snippet':
        msg = 'note on code snippet'
    return msg


def generateMergeRequestMsg(data):
    return 'new MergeRequest'


def generateWikiMsg(data):
    return 'new wiki stuff'


def generatePipelineMsg(data):
    return 'new pipeline stuff'


def generateBuildMsg(data):
    return 'new build stuff'


if __name__ == "__main__":
    b.run_threaded()
    app.run(host='0.0.0.0', port=10111)
