# Description: A ZNC module that fetches current weather information
#              using OpenWeatherMap API.
# Usage: Load the module and set the API key using the 'setkey' command.
#        Then use the 'weather' command to fetch the weather for a specific location.
#        Example: /msg *status loadmod weather
#                 /msg *weather setkey 1234567890abcdef
#                 /msg *weather weather Berlin
# Author: Nachtalb <na@nachtalb.io>
# License: LGPL-3.0 - https://www.gnu.org/licenses/lgpl-3.0.html

__version__ = "1.0.0"
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


class SetAPIKeyCmd(znc.Command):
    command = "setkey"
    args = "<APIKEY>"
    description = "Sets the API key for the weather service."

    def __call__(self, line):
        api_key = line.strip().split()[1]
        if not api_key:
            self.GetModule().PutModule("Usage: setkey <APIKEY>")
            return
        self.GetModule().SetNV("apikey", api_key)
        self.GetModule().PutModule("API key set successfully.")


class GetWeatherCmd(znc.Command):
    command = "weather"
    args = "<LOCATION>"
    description = "Fetches weather for a specified location."

    def __call__(self, line):
        location = " ".join(line.strip().split()[1:])
        if not location:
            self.GetModule().PutModule("Usage: weather <LOCATION>")
            return
        self.GetModule().get_weather(location)


class DebugCmd(znc.Command):
    command = "debug"
    description = "Prints debug information."

    def __call__(self, line):
        module = self.GetModule()
        module.PutModule("Debug information")
        module.PutModule(f"API key: {module.GetNV('apikey')}")


class weather(znc.Module):
    description = (
        "Fetches current weather information using an API key set by the user."
    )
    module_types = [znc.CModInfo.UserModule, znc.CModInfo.NetworkModule]

    def OnLoad(self, args, message):
        self.AddHelpCommand()
        self.AddCommand(SetAPIKeyCmd)
        self.AddCommand(GetWeatherCmd)
        if DEBUG:
            self.AddCommand(DebugCmd)
        return True

    def OnChanMsg(self, nick, channel, message):
        channel_name = channel.GetName()
        if message.s.startswith("!weather"):
            location = " ".join(message.s.split()[1:])
            if not location:
                self.Put("Usage: !weather <LOCATION>", channel=channel_name)
                return znc.CONTINUE
            self.get_weather(location, channel=channel_name)

    def OnPrivMsg(self, nick, message):
        nick_name = nick.GetNick()
        if message.s.startswith("!weather"):
            location = " ".join(message.s.split()[1:])
            if not location:
                self.Put("Usage: !weather <LOCATION>", nick=nick_name)
                return znc.CONTINUE
            self.get_weather(location, nick=nick_name)

    def Put(self, message, channel=None, nick=None):
        if channel:
            self.PutIRC(f"PRIVMSG {channel} :{message}")
        elif nick:
            self.PutIRC(f"PRIVMSG {nick} :{message}")
        else:
            self.PutModule(message)

    def get_weather(self, location, channel=None, nick=None):
        api_key = parse.quote(self.GetNV("apikey"))

        if not api_key:
            if channel:
                self.Put("Not currently set up.", channel, nick)
            self.PutModule(
                "API key is not set. Use 'setkey' command to set it. You can get an API key from https://openweathermap.org/."
            )
            return

        location = parse.quote(location)
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"

        if DEBUG:
            self.PutModule(f"Fetching weather: {url=}")

        try:
            response = urlopen(url)
            data = json.loads(response.read().decode())
            weather = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            country = data["sys"]["country"]
            location = data["name"]
            self.Put(
                f"Weather in {location}, {country}: {weather}, {temp}°C", channel, nick
            )
        except InvalidURL:
            self.Put("Invalid Location.", channel, nick)
        except Exception as e:
            if isinstance(e, HTTPError) and e.code == 404:
                self.Put("Location not found.", channel, nick)
            else:
                self.Put("Could not fetch weather data", channel, nick)

            if DEBUG:
                self.PutModule(f"An error occurred: {type(e)} = {e}")
