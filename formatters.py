#!/usr/bin/env python3

import re


# generic event called from webooks set by admins (info seems to lack)
def formatRepoUpdateMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    msg += '*{0}* {1}'\
           .format(data['user_name'],
                   'issued multiple changes\n\n' if len(data['changes']) > 1 else '')

    for change in data['changes']:
        if 'ref' in change:
            refType = re.search(r'/([^/]+)/[^/]+$', change['ref']).group(1)
            refName = re.search(r'/([^/]+)$', change['ref']).group(1)

            if refType == 'tags' and len(data['changes']) > 1:
                if not int('0x' + change['before'], 0):
                    msg += 'tagged object [{0}]({1}/-/commit/{0}) with tag *"{2}"*\n'\
                           .format(change['after'],
                                   data['project']['web_url'].replace("_", "\_"),
                                   refName)
                else:
                    msg += 'removed tag *"{0}"* from object [{1}]({2}/-/commit/{1})\n'\
                           .format(refName,
                                   change['after'],
                                   data['project']['web_url']).replace("_", "\_")

            elif refType == 'heads':
                if not int('0x' + change['before'], 0):
                    msg += 'created branch [{0}]({1}/-/tree/{0})\n'\
                           .format(refName,
                                   data['project']['web_url']).replace("_", "\_")

                elif not int('0x' + change['after'], 0):
                    msg += 'removed branch *"{0}"*\n'.format(refName)

                # can't tell apart other branch modifications, so ignore
                else:
                    pass

            else:
                msg += 'update with unknown ref type "{0}"\n'.format(refType)

    return msg


def formatPushMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    msg += '*{0}* pushed *{1}* new commits to the *{2}* branch\n'\
           .format(data['user_name'],
                   data['total_commits_count'],
                   re.search(r'/([^/]+)$', data['ref']).group(1))

    for commit in data['commits']:
        part = commit['message'].rstrip().partition('\n')
        msg += '\n[{0}]({1})\n{2}\n'\
                .format(part[0],
                        commit['url'].replace("_", "\_"),
                        part[2])

    return msg


def formatTagPushMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    refName = re.search(r'/([^/]+)$', data['ref']).group(1)

    if not int('0x' + data['before'], 0):
        msg += '*{0}* tagged object [{1}]({2}) with tag *"{3}"*\n\n'\
               .format(data['user_name'],
                       data['checkout_sha'],
                       data['commits'][0]['url'].replace("_", "\_"),
                       refName)

    else:
        msg += '*{0}* removed tag *"{1}"* from object [{2}]({3}/-/commit/{2})\n'\
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
        msg += '*{0}* requested to merge from *{1}* into *{2}*\n'\
               .format(data['user']['name'],
                       attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']
                                               else attrs['target']['path_with_namespace'],
                       attrs['target_branch'])

    elif action == 'reopen':
        msg += '*{0}* reopened the merge request *{1}* from *{2}* into *{3}*\n'\
               .format(data['user']['name'],
                       attrs['id'],
                       attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']
                                               else attrs['target']['path_with_namespace'],
                       attrs['target_branch'])

    elif action == 'update':
        msg += '*{0}* updated the merge request *{1}* from *{2}* into *{3}*\n'\
               .format(data['user']['name'],
                       attrs['id'],
                       attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']
                                               else attrs['target']['path_with_namespace'],
                       attrs['target_branch'])

        if 'assignees' in data['changes']:
            msg += '• Assignees were changed\n'

        if 'labels' in data['changes']:
            msg += '• Labels were changed\n'

        if 'discussion_locked' in data['changes']:
            msg += '• The discussion was locked \n'

    elif action == 'close':
        msg += '*{0}* closed the merge request *{1}* from *{2}* into *{3}*\n'\
               .format(data['user']['name'],
                       attrs['id'],
                       attrs['source_branch'] if attrs['source_project_id'] == attrs['target_project_id']
                                               else attrs['target']['path_with_namespace'],
                       attrs['target_branch'])

    msg += '\n[{0}]({1})\n{2}\n'\
           .format(attrs['title'],
                   attrs['url'].replace("_", "\_"),
                   attrs['description'])

    if action != 'close':
        msg += '*labels:* ' + ", ".join([label['title'] for label in data.get('labels', [])]) + '\n'
        msg += '*asignees:* ' + ", ".join([asignee['name'] for asignee in data.get('assignees', [])]) + '\n'

    return msg


# TODO: can be made more informative
def formatIssueMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    attrs = data['object_attributes']
    action = attrs.get('action', 'open')

    if action == 'open':
        msg += '*{0}* opened issue *{1}*\n'.format(data['user']['name'], attrs['id'])

    elif action == 'reopen':
        msg += '*{0}* reopened issue *{1}*\n'.format(data['user']['name'], attrs['id'])

    elif action == 'update':
        msg += '*{0}* updated issue *{1}*\n'.format(data['user']['name'], attrs['id'])
        if 'assignees' in data['changes']:
            msg += '• Assignees were changed\n'

        if 'labels' in data['changes']:
            msg += '• Labels were changed\n'

        if 'discussion_locked' in data['changes']:
            msg += '• The discussion was locked \n'

    elif action == 'close':
        msg += '*{0}* closed issue *{1}*\n'\
               .format(data['user']['name'],
                       attrs['id'])

    msg += '\n[{0}]({1})\n{2}\n\n'\
           .format(attrs['title'],
                   attrs['url'].replace("_", "\_"),
                   attrs['description'])

    if action != 'close':
        msg += '*labels:* ' + ", ".join([label['title'] for label in data.get('labels', [])]) + '\n'
        msg += '*asignees:* ' + ", ".join([asignee['name'] for asignee in data.get('assignees', [])]) + '\n'

    return msg


def formatNoteMsg(data):
    msg = '*{0}*\n\n'.format(data['project']['path_with_namespace'])

    attrs = data['object_attributes']
    nType = attrs['noteable_type']

    if nType == 'Commit':
        msg += '{0} [commented]({1}) on commit [{2}]({3})\n\n{4}'\
               .format(data['user']['name'],
                       attrs['url'].replace("_", "\_"),
                       data['commit']['id'],
                       data['commit']['url'].replace("_", "\_"),
                       attrs['note'])

    elif nType == 'MergeRequest':
        msg += '{0} [commented]({1}) on Merge Request [{2}]({3})\n\n{4}'\
               .format(data['user']['name'],
                       attrs['url'].replace("_", "\_"),
                       data['merge_request']['id'],
                       data['merge_request']['url'].replace("_", "\_"),
                       attrs['note'])

    elif nType == 'Issue':
        msg += '{0} [commented]({1}) on issue [{2}]({3})\n\n{4}'\
               .format(data['user']['name'],
                       attrs['url'].replace("_", "\_"),
                       data['issue']['iid'],
                       data['issue']['url'].replace("_", "\_"),
                       attrs['note'])

    elif nType == 'Snippet':
        msg += '{0} [commented]({1}) on code snippet [{2}]({3})\n\n{4}'\
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

    msg += '*{0}* {1}d a Wiki entry\n\n'\
           .format(data['user']['name'],
                   action)

    msg += '{0}[{1}]({2})'\
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
        msg += 'Project *{0}* has been {1}d\n\npath: {2}\nvisibility: {3}\nowners: {4}'\
               .format(data['name'],
                       re.search(r'^.*_([^_]+)$', action).group(1),
                       data['path_with_namespace'],
                       data['project_visibility'],
                       ", ".join([owner['name'] for owner in data.get('owners', [])]))

        for owner in data.get('owners', []):
            msg += '{0}{1}\n'\
                   .format(owner['name'],
                           (' ' + owner['email']) if owner['email'] else '')

    if action == 'project_rename':
        msg += 'Project *{0}* path *{1}* has been renamed to *{2}*\n'\
               .format(data['name'],
                       re.search(r'^.*/([^/]+)$', data['old_path_with_namespace']).group(1),
                       data['path'])

    if action == 'project_transfer':
        msg += 'Project *{0}* has been transferred from *{1}*\n\nold path: {2}\nnew path: {3}'\
               .format(data['name'],
                       re.search(r'^([^/]+)/.*$', data['old_path_with_namespace']).group(1),
                       data['old_path_with_namespace'],
                       data['path_with_namespace'])

    if action == 'project_destroy':
        msg += 'Project *{0}* has been removed\n\npath was: {1}\n'\
               .format(data['name'],
                       data['path_with_namespace'])

    return msg


eventFormatters = {
    'repository_update': formatRepoUpdateMsg,
    'push': formatPushMsg,
    'tag_push': formatTagPushMsg,
    'merge_request': formatMergeRequestMsg,
    'issue': formatIssueMsg,
    'note': formatNoteMsg,
    'wiki_page': formatWikiMsg,
    'group_create': formatGroupMsg,
    'group_rename': formatGroupMsg,
    'group_destroy': formatGroupMsg,
    'user_create': formatUserMsg,
    'user_rename': formatUserMsg,
    'user_destroy': formatUserMsg,
    'user_add_to_group': formatUserMsg,
    'user_update_for_group': formatUserMsg,
    'user_remove_from_group': formatUserMsg,
    'key_create': formatKeyMsg,
    'key_destroy': formatKeyMsg,
    'project_create': formatProjectMsg,
    'project_update': formatProjectMsg,
    'project_rename': formatProjectMsg,
    'project_transfer': formatProjectMsg,
    'project_destroy': formatProjectMsg
}
