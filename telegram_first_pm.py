# Description: A ZNC module to send Telegram notifications on the first private
#              message received from a user since activation of the module.
# Usage: Load the module with the following semicolon-separated arguments:
#        bot_token= your Telegram bot token
#        chat_id= your chat id
#        thread_message_id= optional, the message id of the thread to reply to
#
#        Example: /msg *status loadmod telegram_first_pm bot_token=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11;chat_id=123456;thread_message_id=123456
#
#        You can obtain a bot token and chat id by creating a new bot using the
#        BotFather bot and sending a message to the bot. The chat id can be obtained
#        by sending a message to the bot and then visiting the following URL:
#        https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
# Author: Nachtalb <na@nachtalb.io>
# License: LGPL-3.0 - https://www.gnu.org/licenses/lgpl-3.0.html

__version__ = "1.0.0"
__description__ = "Send Telegram notifications on the first private message received from a user since activation of the module."
__author__ = "Nachtalb <na@nachtalb.io>"
__license__ = "LGPL-3.0"

from urllib import request, parse

import znc

### Configuration ###

# The message template to use when sending a message to Telegram.
TEMPLATE = "{sender} @ {network_name}: {message}"


### Module ###


class telegram_first_pm(znc.Module):
    module_types = [znc.CModInfo.NetworkModule]
    description = "Send Telegram notifications on the first private message received from a user since activation of the module. Expected args: bot_token=TOKEN;chat_id=ID;thread_message_id=ID"
    wiki_page = "telegram_first_pm"
    has_args = True
    args_help_text = "Expected args: bot_token=TOKEN;chat_id=ID;thread_message_id=ID"

    _seen_users = set()

    def OnLoad(self, args, message):
        args_dict = dict(arg.split("=") for arg in args.split(";") if "=" in arg)
        self.bot_token = args_dict.get("bot_token")
        self.chat_id = args_dict.get("chat_id")
        self.thread_message_id = args_dict.get("thread_message_id")

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

    def OnPrivMsg(self, nick, message):
        if not self._check_args():
            return znc.CONTINUE

        sender = nick.GetNick()

        if sender in self._seen_users:
            return znc.CONTINUE

        self._seen_users.add(sender)
        self.send_telegram_message(nick, message)

        return znc.CONTINUE

    def send_telegram_message(self, nick, message):
        network_name = self.GetNetwork().GetName()
        sender = nick.GetNick()
        text = TEMPLATE.format(
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
