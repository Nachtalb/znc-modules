# ZNC Modules by Nachtalb

This repository contains a collection of ZNC modules developed by Nachtalb,
aimed at enhancing the functionality and user experience of ZNC, an IRC bouncer.
Each module is designed with a specific purpose, from notification services to
utility enhancements for IRC users.

## How to Use

To use any of the modules in this collection:

1. Clone this repository or download the specific module you want to use.
2. Place the module file(s) in your ZNC modules directory.
3. Load the module according to the instructions provided in the module file.

   To load a module, use the `/msg *status loadmod <module_name> <args>` command
   in your IRC client or through the ZNC web interface.

## Available Modules

- `telegram_mentions.py`: Sends Telegram notifications on mentions. Detailed
  usage instructions are available at the top of the module file.
- `telegram_first_pm.py`: Sends Telegram notifications on the first private
  message from a user since activation of the module. Detailed usage
  instructions are available at the top of the module file.

## License

Each module may have its own licensing. Please refer to the individual module
files for license information.
