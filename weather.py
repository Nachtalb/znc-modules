# Description: A ZNC module that fetches current weather information
#              using OpenWeatherMap API.
# Usage: Load the module and set the API key using the 'setkey' command.
#        Then use the 'weather' command to fetch the weather for a specific location.
#        Example: /msg *status loadmod weather
#                 /msg *weather setkey 1234567890abcdef
#                 /msg *weather weather Berlin
# Author: Nachtalb <na@nachtalb.io>
# License: LGPL-3.0 - https://www.gnu.org/licenses/lgpl-3.0.html

__version__ = "1.1.0"
__description__ = (
    "A ZNC module that fetches current weather information using OpenWeatherMap API."
)
__author__ = "Nachtalb <na@nachtalb.io>"
__license__ = "LGPL-3.0"


from urllib import parse
from urllib.request import urlopen
from urllib.error import HTTPError
from http.client import InvalidURL
import json

import znc


### Configuration ###

DEBUG = False


### Module ###


def exception_handler(func):
    def wrapper(self, *args, **kwargs):
        if isinstance(self, znc.Command):
            self.log = self.GetModule().Log

        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            self.log(f"An error occurred: {type(e)} = {e}", force=True)

    return wrapper


class SetAPIKeyCmd(znc.Command):
    command = "setkey"
    args = "<APIKEY>"
    description = "Sets the API key for the weather service."

    @exception_handler
    def __call__(self, line):
        api_key = next(filter(None, line.strip().split()[1:]), None)
        module = self.GetModule()

        if not api_key and module.HasNV("apikey"):
            module.DelNV("apikey")
            module.PutModule("API key removed.")
        elif not api_key:
            module.PutModule("Usage: setkey <APIKEY>")
        else:
            module.SetNV("apikey", api_key)
            module.PutModule("API key set successfully.")


class GetWeatherCmd(znc.Command):
    command = "weather"
    args = "<LOCATION>"
    description = "Fetches weather for a specified location."

    @exception_handler
    def __call__(self, line):
        module = self.GetModule()
        module.Log(f"Received command: {line}")
        location = " ".join(line.strip().split()[1:])
        if not location:
            module.PutModule("Usage: weather <LOCATION>")
            return
        module.get_weather(location)


class DebugCmd(znc.Command):
    command = "debug"
    description = "Prints debug information."

    @exception_handler
    def __call__(self, line):
        module = self.GetModule()
        module.PutModule("Debug information")
        module.PutModule(f"API key: {module.GetNV('apikey')}")


class weather(znc.Module):
    description = (
        "Fetches current weather information using an API key set by the user."
    )
    module_types = [znc.CModInfo.UserModule, znc.CModInfo.NetworkModule]

    @exception_handler
    def OnLoad(self, args, message):
        self.AddHelpCommand()
        self.AddCommand(SetAPIKeyCmd)
        self.AddCommand(GetWeatherCmd)
        if DEBUG:
            self.AddCommand(DebugCmd)

        self.Log(f"Loaded module {self.GetModName()} v{__version__}")
        return True

    @exception_handler
    def OnChanMsg(self, nick, channel, message):
        channel_name = channel.GetName()
        if message.s.startswith("!weather"):
            self.Log(f"Received command in channel {channel_name}: {message.s}")
            location = " ".join(message.s.split()[1:])
            if not location:
                self.Action(
                    "Usage: !weather <LOCATION>", channel=channel_name, keep_local=True
                )
                return znc.HALT
            self.get_weather(location, channel_name)
        return znc.CONTINUE

    @exception_handler
    def OnPrivMsg(self, nick, message):
        nick_name = nick.GetNick()
        if message.s.startswith("!weather"):
            self.Log(f"Received command from {nick_name}: {message.s}")
            location = " ".join(message.s.split()[1:])
            if not location:
                self.Action("Usage: !weather <LOCATION>", nick_name)
                return znc.CONTINUE
            self.get_weather(location, nick_name)
        return znc.CONTINUE

    @exception_handler
    def OnUserMsg(self, target, message):
        if message.s.startswith("!weather"):
            self.Log(f"Received command from self: {str(target)} {message.s}")
            location = " ".join(message.s.split()[1:])
            if not location:
                self.Action("Usage: !weather <LOCATION>", str(target), broadcast=False)
                return znc.HALT
            self.Put(message, target=str(target), mirror=True)
            self.get_weather(location, str(target))
            return znc.HALT

    def Log(self, message, force=False):
        if DEBUG:
            self.PutModule(message)

    def Put(self, message, target=None, action=False, broadcast=True, mirror=True):
        if not target:
            self.Log(f"PutModule: {message}")
            self.PutModule(message)
            return

        try:
            self_user = self.GetNetwork().GetUser().GetNick()

            if action:
                message = f"\x01ACTION {message}\x01"

            msg = f":{self_user} PRIVMSG {target} :{message}"

            self.Log(f"Put: {msg}")
            if broadcast:
                self.PutIRC(msg)
            if mirror:
                self.PutUser(msg)
        except Exception as e:
            self.Log(f"An error occurred: {type(e)} = {e}")

    def Action(self, message, target=None, broadcast=True, mirror=True):
        self.Put(message, target, action=True, broadcast=broadcast, mirror=mirror)

    def get_weather(self, location, target=None):
        api_key = parse.quote(self.GetNV("apikey"))

        if not api_key:
            if target:
                self.Action("!weather is not set up.", target)
            self.PutModule(
                "API key is not set. Use 'setkey' command to set it. You can get an API key from https://openweathermap.org/."
            )
            return

        location = parse.quote(location)
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"

        self.Log(f"Fetching weather: {url=}")

        try:
            response = urlopen(url)
            data = json.loads(response.read().decode())
            weather = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            country = data["sys"]["country"]
            location = data["name"]
            self.Put(f"Weather in {location}, {country}: {weather}, {temp}°C", target)
        except InvalidURL:
            self.Put("Invalid Location.", target)
        except Exception as e:
            if isinstance(e, HTTPError) and e.code == 404:
                self.Action("Location not found.", target)
            else:
                self.Put("Could not fetch weather data", target)

            self.Log(f"An error occurred: {type(e)} = {e}")
