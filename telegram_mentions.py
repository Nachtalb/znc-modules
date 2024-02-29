# Description: A ZNC module to send Telegram notifications on mentions.
# Usage: Load the module with the following semicolon-separated arguments:
#        bot_token= your Telegram bot token
#        chat_id= your chat id
#        mentions= optional, a comma-separated list of words to look for in messages
#        thread_message_id= optional, the message id of the thread to reply to
#
#        Example: /msg *status loadmod telegram_mentions bot_token=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11;chat_id=123456;mentions=hello,world;thread_message_id=123456
#
#        You can obtain a bot token and chat id by creating a new bot using the
#        BotFather bot and sending a message to the bot. The chat id can be obtained
#        by sending a message to the bot and then visiting the following URL:
#        https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
# Author: Nachtalb <na@nachtalb.io>
# License: LGPL-3.0 - https://www.gnu.org/licenses/lgpl-3.0.html

__version__ = "1.0.0"
__description__ = "A ZNC module to send Telegram notifications on mentions."
__author__ = "Nachtalb <na@nachtalb.io>"
__license__ = "LGPL-3.0"

from urllib import request, parse

import znc

### Configuration ###

# The Telegram message template used when receiving a message from a channel. Empty to disable channel mentions.
CHANNEL_TEMPLATE = "{sender} @ {network_name}/{channel_name}: {message}"
# The Telegram message template used when receiving a private message. Empty to disable private mentions.
PRIVATE_TEMPLATE = "{sender} @ {network_name}: {message}"
# Whether to treat mentions as case-sensitive.
CASE_SENSITIVE = False


### Module ###


class telegram_mentions(znc.Module):
    module_types = [znc.CModInfo.NetworkModule]
    description = "Send Telegram notifications on mentions. Expected args: bot_token=TOKEN;chat_id=ID;mentions=mention1,mention2;thread_message_id=ID"
    wiki_page = "telegram_mentions"
    has_args = True
    args_help_text = "Expected args: bot_token=TOKEN;chat_id=ID;mentions=mention1,mention2;thread_message_id=ID"

    def OnLoad(self, args, message):
        if not CASE_SENSITIVE:
            args = args.lower()

        args_dict = dict(arg.split("=") for arg in args.split(";") if "=" in arg)
        self.bot_token = args_dict.get("bot_token")
        self.chat_id = args_dict.get("chat_id")
        self.mentions = list(filter(None, args_dict.get("mentions", "").split(",")))
        self.thread_message_id = args_dict.get("thread_message_id")

        if not self.mentions:
            self.mentions = [self.GetNetwork().GetUser().GetNick()]
            self.PutModule(f"No mentions specified, using '{self.mentions[0]}'")

        if not self._check_args():
            return False

        return True

    def _check_args(self):
        if not self.bot_token or not self.chat_id:
            self.PutModule(
                "Error: bot_token and chat_id not set. Please load the module with the correct arguments."
            )
            return False
        return True

    def OnChanMsg(self, nick, channel, message):
        if not CHANNEL_TEMPLATE:
            return znc.CONTINUE

        if not self._check_args():
            return znc.CONTINUE

        msg_text = message.s if CASE_SENSITIVE else message.s.lower()

        for mention in self.mentions:
            if mention in msg_text:
                self.send_telegram_message(nick, channel, message)
                break
        return znc.CONTINUE

    def OnPrivMsg(self, nick, message):
        if not PRIVATE_TEMPLATE:
            return znc.CONTINUE

        if not self._check_args():
            return znc.CONTINUE

        msg_text = message.s if CASE_SENSITIVE else message.s.lower()

        for mention in msg_text:
            if mention in message.s:
                self.send_telegram_message(nick, None, message)
                break
        return znc.CONTINUE

    def send_telegram_message(self, nick, channel, message):
        network_name = self.GetNetwork().GetName()
        sender = nick.GetNick()
        if channel:
            channel_name = channel.GetName()
            text = CHANNEL_TEMPLATE.format(
                sender=sender,
                network_name=network_name,
                channel_name=channel_name,
                message=message.s,
            )
        else:
            text = PRIVATE_TEMPLATE.format(
                sender=sender, network_name=network_name, message=message.s
            )

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {"chat_id": self.chat_id, "text": text}
        if self.thread_message_id:
            data["thread_message_id"] = self.thread_message_id
        data = parse.urlencode(data).encode()

        req = request.Request(url, data=data)

        try:
            with request.urlopen(req) as response:
                response.read()
        except Exception as e:
            self.PutModule(f"Error sending Telegram message: {e}")
