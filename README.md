# GitLab webhook-based telegram notifications bot

Simple bot that listens to gitlab webhooks and sends each event to authenticated chats

## Important note

Although for now the fork is mergeable with upstream, I plan to work freely on it so expect to see divergence eventually. This README is being updated as the usage changes.

## Requirements 

Python 3.9+

## How to use

1. Create a new bot https://core.telegram.org/bots#create-a-new-bot and copy the token to the token file
2. Change the authmsg file with some secret keyword
3. Run app.py in your server or [run it in docker](https://github.com/3coma3/gitlab-telegram-bot/blob/main/README.md#q-how-can-i-run-the-bot-in-docker)
4. At GitLab, create webhooks pointing to **http://\<bot address\>:10111**
5. Talk to your bot and write only the keyword

You will receive notifications for all events for which a webhook notification was configured at GitLab. You can enable notifications at two places: site wide (using an administrator account), and per project, if you have enough rights.

Some webhooks overlap between site wide and per project, so you might want to disable at either place as you see fit to avoid having extra notifications.

If the webhook doesn't have a formatting function implemented, the bot will inform of that and just print the json data it received from the webhook so you can write one and send a patch :). Most events do have a formatter implemented, though.



## FAQ

### Q. How can I stop receiving messages
A. Write "shutup" in your conversation and the bot won't talk to you anymore

### Q. How can I enable the bot in group chats
A. Write /keyword instead of keyword

### Q. How can I run the bot in Docker?
A. First build the image with

```shell
$ docker build -t bot .
```
then run it:

```shell
$ docker run -d -p 10111:10111 --name bot -e AUTHMSG="$(cat secret)" -e TOKEN="$(cat token)" bot
```
