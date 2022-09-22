#!/usr/bin/env python3

import json
import re
import atexit
import signal

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


def exit():
    bot.send_to_all("I'm going away for a while. Laters! \U0001F596")


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
    elif event == 'group_create':
        msg = formatGroupMsg(data)
    elif event == 'group_rename':
        msg = formatGroupMsg(data)
    elif event == 'group_destroy':
        msg = formatGroupMsg(data)
    elif event == 'user_create':
        msg = formatUserMsg(data)
    elif event == 'user_rename':
        msg = formatUserMsg(data)
    elif event == 'user_destroy':
        msg = formatUserMsg(data)
    elif event == 'user_add_to_group':
        msg = formatUserMsg(data)
    elif event == 'user_update_for_group':
        msg = formatUserMsg(data)
    elif event == 'user_remove_from_group':
        msg = formatUserMsg(data)
    elif event == 'key_create':
        msg = formatKeyMsg(data)
    elif event == 'key_destroy':
        msg = formatKeyMsg(data)
    elif event == 'project_create':
        msg = formatProjectMsg(data)
    elif event == 'project_update':
        msg = formatProjectMsg(data)
    elif event == 'project_rename':
        msg = formatProjectMsg(data)
    elif event == 'project_transfer':
        msg = formatProjectMsg(data)
    elif event == 'project_destroy':
        msg = formatProjectMsg(data)
    else:
        msg = 'New event "*{0}*" without formmater, write one for me!\n```\n{1}```\n'\
            .format(event, json.dumps(data, indent=2))

    bot.send_to_all(msg)
    return jsonify({'status': 'ok'})


# this generic event is called from the webooks set by admins (info seems to lack)
def formatRepoUpdateMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    msg = msg + '*{0}* {1}'\
            .format(data['user_name'],
                    'issued multiple changes\n\n' if len(data['changes']) > 1 else '')

    for change in data['changes']:
        if 'ref' in change:
            refType = re.search(r'/([^/]+)/[^/]+$', change['ref']).group(1)
            refName = re.search(r'/([^/]+)$', change['ref']).group(1)

            if refType == 'tags' and len(data['changes']) > 1:
                if not int('0x' + change['before'], 0):
                    msg = msg + 'tagged object [{0}]({1}/-/commit/{0}) with tag *"{2}"*\n'\
                                .format(change['after'],
                                        data['project']['web_url'].replace("_", "\_"),
                                        refName)
                else:
                    msg = msg + 'removed tag *"{0}"* from object [{1}]({2}/-/commit/{1})\n'\
                                .format(refName,
                                        change['after'],
                                        data['project']['web_url']).replace("_", "\_")

            elif refType == 'heads':
                if not int('0x' + change['before'], 0):
                    msg = msg + 'created branch [{0}]({1}/-/tree/{0})\n'\
                                .format(refName,
                                        data['project']['web_url']).replace("_", "\_")

                elif not int('0x' + change['after'], 0):
                    msg = msg + 'removed branch *"{0}"*\n'.format(refName)

                # can't tell appart commit pushes and other branch
                # modifications, so ignore
                else:
                    pass

            else:
                msg = msg + 'update with unknown ref type\n'

    return msg


def formatPushMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    msg = msg + '*{0}* pushed *{1}* new commits to the *{2}* branch\n'\
                .format(data['user_name'],
                        data['total_commits_count'],
                        re.search(r'/([^/]+)$', data['ref']).group(1))

    for commit in data['commits']:
        part = commit['message'].rstrip().partition('\n')
        msg = msg + '\n[{0}]({1})\n{2}\n'\
                    .format(part[0],
                            commit['url'].replace("_", "\_"),
                            part[2])

    return msg


def formatTagPushMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    refName = re.search(r'/([^/]+)$', data['ref']).group(1)

    if not int('0x' + data['before'], 0):
        msg = msg + '*{0}* tagged object [{1}]({2}) with tag *"{3}"*\n\n'\
                    .format(data['user_name'],
                            data['checkout_sha'],
                            data['commits'][0]['url'].replace("_", "\_"),
                            refName)

    else:
        msg = msg + '*{0}* removed tag *"{1}"* from object [{2}]({3}/-/commit/{2})\n'\
                    .format(data['user_name'],
                            refName,
                            data['before'],
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
                            attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']
                                                   else attrs['target']['path_with_namespace'],
                            attrs['target_branch'])

    elif action == 'reopen':
        msg = msg + '*{0}* reopened the merge request *{1}* from *{2}* into *{3}*\n'\
                    .format(data['user']['name'],
                            attrs['id'],
                            attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']
                                                   else attrs['target']['path_with_namespace'],
                            attrs['target_branch'])

    elif action == 'update':
        msg = msg + '*{0}* updated the merge request *{1}* from *{2}* into *{3}*\n'\
                    .format(data['user']['name'],
                            attrs['id'],
                            attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']
                                                   else attrs['target']['path_with_namespace'],
                            attrs['target_branch'])

        if 'assignees' in data['changes']:
            msg = msg + 'Assignees were changed\n'

        if 'labels' in data['changes']:
            msg = msg + 'Labels were changed\n'

        if 'discussion_locked' in data['changes']:
            msg = msg + 'The discussion was locked \n'

    elif action == 'close':
        msg = msg + '*{0}* closed the merge request *{1}* from *{2}* into *{3}*\n'\
                    .format(data['user']['name'],
                            attrs['id'],
                            attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']
                                                   else attrs['target']['path_with_namespace'],
                            attrs['target_branch'])

    msg = msg + '\n[{0}]({1})\n{2}\n'\
                .format(attrs['title'],
                        attrs['url'].replace("_", "\_"),
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
                    .format(data['user']['name'],
                            attrs['id'])

    msg = msg + '\n[{0}]({1})\n{2}\n\n'\
                .format(attrs['title'],
                        attrs['url'].replace("_", "\_"),
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
                  .format(data['user']['name'],
                          attrs['url'].replace("_", "\_"),
                          data['commit']['id'],
                          data['commit']['url'].replace("_", "\_"),
                          attrs['note'])

    elif nType == 'MergeRequest':
        msg = msg + '{0} [commented]({1}) on Merge Request [{2}]({3})\n\n{4}'\
                  .format(data['user']['name'],
                          attrs['url'].replace("_", "\_"),
                          data['merge_request']['id'],
                          data['merge_request']['url'].replace("_", "\_"),
                          attrs['note'])

    elif nType == 'Issue':
        msg = msg + '{0} [commented]({1}) on issue [{2}]({3})\n\n{4}'\
                  .format(data['user']['name'],
                          attrs['url'].replace("_", "\_"),
                          data['issue']['iid'],
                          data['issue']['url'].replace("_", "\_"),
                          attrs['note'])

    elif nType == 'Snippet':
        msg = msg + '{0} [commented]({1}) on code snippet [{2}]({3})\n\n{4}'\
                  .format(data['user']['name'],
                          attrs['url'].replace("_", "\_"),
                          data['snippet']['id'],
                          re.search(r'^(.*)#[^#]+$', attrs['url']).group(1).replace("_", "\_"),
                          attrs['note'])

    return msg


def formatWikiMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    attrs = data['object_attributes']
    action = attrs.get('action', 'create')

    msg = msg + '*{0}* {1}d a Wiki entry\n\n'\
                .format(data['user']['name'],
                        action)

    msg = msg + '{0}[{1}]({2})'\
                .format('(was) ' if action == 'delete' else '',
                        attrs['title'],
                        attrs['url'].replace("_", "\_"))

    return msg


def formatGroupMsg(data):
    action = data['event_name']

    if action == 'group_create':
        msg = 'Group *"{0}"* has been created'.format(data['full_path'])

    elif action == 'group_rename':
        msg = 'Group slug *"{0}"* has been renamed to *"{1}"*'.format(data['old_full_path'], data['full_path'])

    elif action == 'group_destroy':
        msg = 'Group *"{0}"* has been deleted'.format(data['full_path'])

    return msg


def formatUserMsg(data):
    action = data['event_name']

    if action == 'user_create':
        msg = 'User *{0}* has been created\n\nFull name: {1}\nEmail: {2}'\
                .format(data['username'], data['name'], data['email'])

    elif action == 'user_rename':
        msg = 'User *{0}* has been renamed to *{1}*'.format(data['old_username'], data['username'])

    elif action == 'user_destroy':
        msg = 'User *{0}* has been deleted'.format(data['username'])

    elif action == 'user_add_to_group':
        msg = 'User *{0}* has been added to group *{1}* with {2} access'\
                .format(data['user_name'],
                        data['group_path'],
                        data['group_access'])

    elif action == 'user_remove_from_group':
        msg = 'User *{0}* has been removed from group *{1}* - access was {2}'\
                .format(data['user_name'],
                        data['group_path'],
                        data['group_access'])

    elif action == 'user_update_for_group':
        msg = 'User *{0}* has been updated for group *{1}* - access is {2}'\
                .format(data['user_name'],
                        data['group_path'],
                        data['group_access'])

    else:
        msg = action

    return msg


def formatKeyMsg(data):
    action = data['event_name']

    if action == 'key_create':
        msg = '*{0}* created an SSH key with type {1}'\
                .format(data['username'],
                        re.search(r'^ssh-([^ ]+) ', data['key']).group(1))

    if action == 'key_destroy':
        msg = '*{0}* removed an SSH key' .format(data['username'])

    return msg


def formatProjectMsg(data):
    msg = '*{0}*\n\n'.format(re.search(r'^([^/]+)/.*$', data['path_with_namespace']).group(1))

    action = data['event_name']

    if action in ['project_create', 'project_update']:
        msg = msg + 'Project *{0}* has been {1}d\n\npath: {2}\nvisibility: {3}\nowners: {4}'\
                    .format(data['name'],
                            re.search(r'^.*_([^_]+)$', action).group(1),
                            data['path_with_namespace'],
                            data['project_visibility'],
                            ", ".join([owner['name'] for owner in data.get('owners', [])]))

        for owner in data.get('owners', []):
            msg = msg + owner['name'] + ' ' + (owner['email'] if owner['email'] else '') + '\n'

    if action == 'project_rename':
        msg = msg + 'Project *{0}* path *{1}* has been renamed to *{2}*\n'\
                    .format(data['name'],
                            re.search(r'^.*/([^/]+)$', data['old_path_with_namespace']).group(1),
                            data['path'])

    if action == 'project_transfer':
        msg = msg + 'Project *{0}* has been transferred from *{1}*\n\nold path: {2}\nnew path: {3}'\
                    .format(data['name'],
                            re.search(r'^([^/]+)/.*$', data['old_path_with_namespace']).group(1),
                            data['old_path_with_namespace'],
                            data['path_with_namespace'])

    if action == 'project_destroy':
        msg = msg + 'Project *{0}* has been removed\n\npath was: {1}\n'\
                    .format(data['name'],
                            data['path_with_namespace'])

    return msg


if __name__ == "__main__":
    atexit.register(exit)
    signal.signal(signal.SIGTERM, exit)
    signal.signal(signal.SIGINT, exit)

    bot.run_threaded()
    app.run(host='0.0.0.0', port=10111)
