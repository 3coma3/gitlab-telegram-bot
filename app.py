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
    elif event == 'tag_push':
        msg = formatTagPushMsg(data)
    elif event == 'merge_request':
        msg = formatMergeRequestMsg(data)
    elif event == 'issue':
        msg = formatIssueMsg(data)
    elif event == 'note':
        msg = formatNoteMsg(data)
    elif event == 'wiki_page':
        msg = formatWikiMsg(data)
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

def formatTagPushMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    refName = re.search(r'/([^/]+)$', data['ref']).group(1)

    if not int('0x' + data['before'], 0):
        msg = msg + '*{0}* tagged object [{1}]({2}) with tag *"{3}"*\n\n'\
                    .format(data['user_name'],\
                            data['checkout_sha'],\
                            data['commits'][0]['url'].replace("_", "\_"),\
                            refName)

    else:
        msg = msg + '*{0}* removed tag *"{1}"* from object [{2}]({3}/-/commit/{2})\n'\
                    .format(data['user_name'],\
                            refName,\
                            data['before'],\
                            data['project']['web_url'].replace("_", "\_"))

    return msg

# TODO: can be made more informative
def formatMergeRequestMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    attrs = data['object_attributes']
    action = attrs.get('action', 'open')

    if action == 'open':
        msg = msg + '*{0}* requested to merge from *{1}* into *{2}*\n'\
                    .format(data['user']['name'],
                            attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']\
                                                   else attrs['target']['path_with_namespace'],\
                            attrs['target_branch'])

    elif action == 'reopen':
        msg = msg + '*{0}* reopened the merge request *{1}* from *{2}* into *{3}*\n'\
                    .format(data['user']['name'],\
                            attrs['id'],\
                            attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']\
                                                   else attrs['target']['path_with_namespace'],\
                            attrs['target_branch'])

    elif action == 'update':
        msg = msg + '*{0}* updated the merge request *{1}* from *{2}* into *{3}*\n'\
                    .format(data['user']['name'],\
                            attrs['id'],
                            attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']\
                                                   else attrs['target']['path_with_namespace'],\
                            attrs['target_branch'])

        if 'assignees' in data['changes']:
            msg = msg + 'Assignees were changed\n'

        if 'labels' in data['changes']:
            msg = msg + 'Labels were changed\n'

        if 'discussion_locked' in data['changes']:
            msg = msg + 'The discussion was locked \n'

    elif action == 'close':
        msg = msg + '*{0}* closed the merge request *{1}* from *{2}* into *{3}*\n'\
                    .format(data['user']['name'],\
                            attrs['id'],\
                            attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']\
                                                   else attrs['target']['path_with_namespace'],\
                            attrs['target_branch'])

    msg = msg + '\n[{0}]({1})\n{2}\n'\
                .format(attrs['title'],\
                attrs['url'].replace("_", "\_"),\
                attrs['description'])

    if action != 'close':
        msg = msg + '*labels:* ' + ", ".join([label['title'] for label in data.get('labels', [])]) + '\n'
        msg = msg + '*asignees:* ' + ", ".join([asignee['name'] for asignee in data.get('assignees', [])]) + '\n'

    return msg

# TODO: can be made more informative
def formatIssueMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    attrs = data['object_attributes']
    action = attrs.get('action', 'open')

    if action == 'open':
        msg = msg + '*{0}* opened issue *{1}*\n'.format(data['user']['name'], attrs['id'])

    elif action == 'reopen':
        msg = msg + '*{0}* reopened issue *{1}*\n'.format(data['user']['name'], attrs['id'])

    elif action == 'update':
        msg = msg + '*{0}* updated issue *{1}*\n'.format(data['user']['name'], attrs['id'])
        if 'assignees' in data['changes']:
            msg = msg + 'Assignees were changed\n'

        if 'labels' in data['changes']:
            msg = msg + 'Labels were changed\n'

        if 'discussion_locked' in data['changes']:
            msg = msg + 'The discussion was locked \n'

    elif action == 'close':
        msg = msg + '*{0}* closed issue *{1}*\n'\
                    .format(data['user']['name'],\
                            attrs['id'])

    msg = msg + '\n[{0}]({1})\n{2}\n\n'\
                .format(attrs['title'],\
                        attrs['url'].replace("_", "\_"),\
                        attrs['description'])

    if action != 'close':
        msg = msg + '*labels:* ' + ", ".join([label['title'] for label in data.get('labels', [])]) + '\n'
        msg = msg + '*asignees:* ' + ", ".join([asignee['name'] for asignee in data.get('assignees', [])]) + '\n'

    return msg

def formatNoteMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    attrs = data['object_attributes']
    nType = attrs['noteable_type']

    if nType == 'Commit':
        msg = msg + '{0} [commented]({1}) on commit [{2}]({3})\n\n{4}'\
                  .format(data['user']['name'],\
                          attrs['url'].replace("_", "\_"),\
                          data['commit']['id'],\
                          data['commit']['url'].replace("_", "\_"),\
                          attrs['note'])

    elif nType == 'MergeRequest':
        msg = msg + '{0} [commented]({1}) on Merge Request [{2}]({3})\n\n{4}'\
                  .format(data['user']['name'],\
                          attrs['url'].replace("_", "\_"),\
                          data['merge_request']['id'],\
                          data['merge_request']['url'].replace("_", "\_"),\
                          attrs['note'])

    elif nType == 'Issue':
        msg = msg + '{0} [commented]({1}) on issue [{2}]({3})\n\n{4}'\
                  .format(data['user']['name'],\
                          attrs['url'].replace("_", "\_"),\
                          data['issue']['iid'],\
                          data['issue']['url'].replace("_", "\_"),\
                          attrs['note'])

    elif nType == 'Snippet':
        msg = msg + '{0} [commented]({1}) on code snippet [{2}]({3})\n\n{4}'\
                  .format(data['user']['name'],\
                          attrs['url'].replace("_", "\_"),\
                          data['snippet']['id'],\
                          re.search(r'^(.*)#[^#]+$', attrs['url']).group(1).replace("_", "\_"),\
                          attrs['note'])

    return msg

def formatWikiMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    attrs = data['object_attributes']
    action = attrs.get('action', 'create')

    msg = msg + '*{0}* {1}d a Wiki entry\n\n'\
                .format(data['user']['name'],\
                        action)

    msg = msg + '{0}[{1}]({2})'\
                .format('(was) ' if action == 'delete' else '',\
                        attrs['title'],\
                        attrs['url'].replace("_", "\_"))

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
