# Telegram RPG Dungeon Bot

## Introduction

The following project aims to replicate the idea of a dungeon RPG game via a Telegram bot. At the moment it could be said that the game is not complete, given the lack of some features that these games can present. However, it can be considered as a beta and starting base for adding new features. The project is written in Python and primarily uses the `python-telegram-bot` library. Regarding saving the actions done by users, two databases were chosen:

- `dungeon.db`: where various user data is stored.
- `asset.db`: where information about classes, objects (of any category), and monsters is kept in storage.

## Requirements
- Python 3.8+
- Libraries listed in `requirements.txt`

## Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/Spiedoz/Portfolio/tree/main/Projects/Bot%20Telegram
    cd telegram-bot
    ```
2. Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1. Create a Telegram bot via [t.me/BotFather](https://t.me/BotFather) and get the token.
2. Enter the token in the `init_bot()` function found in the `core.py` file.
3. Add your `user_id` to the admin list also in the `core.py` file.

## Structure

The bot follows a structure that divides the various features according to topic:
- **actions**: main actions the user can do such as fighting and exploring.
- **admin**: management of the bot's admin powers.
- **asset**: link to the second database to get information about classes, items, and monsters.
- **bot**: bot construction with handlers added.
- **events**: managing randomness of certain events and extractions of rarity (monsters, items) and rewards (healing, money, exp, or stats).
- **users**: managing inventory, guild, profile, registration, and possible upgrades.
- **utils**: general functions such as guide and top, plus useful functions to control whether certain commands can be used.

## Features

The bot allows the user to perform the following actions:
- **Register**: `/start` - the bot will initiate a light conversation to take the user's nickname and provide directions on how to navigate the game.
- **Change region and dungeon**: `/travel` - as the user levels up, more options become available.
- **Exploration**: `/explore` - the ability to trigger events such as monster encounters, item finds, or nothing.
- **Fighting**: `/battle` - start a fight against a monster.
- **Class choice**: `/office` - choose a favored class upon reaching level 10 and later at level 35.
- **Profile check**: `/profile` - view various data including level, money, and combat-related statistics.
- **Statistics improvement**: `/stats` - use stat points gained by leveling up.
- **Inventory management**: `/inventory`, `/info [id]`, `/sell [id] [qt]`, `/equip [id]`, `/unequip [id]`, `/equipment`.
- **Use objects**: `/use [id] [qt]`.
- **Crafting**: `/craft` - limited to two classes.
- **Buy weapons and shields**: `/armory`.
- **Cure**: `/tavern`.
- **Guild management**: `/found [guild name]`, `/invite`, `/promote`, `/members`, `/degrade`, `/guild`, `/expel`, `/leave`, `/rename`.
- **Exchanges**: `/trade` - exchange items and gold with other users.
- **Rankings and guidance**: `/top`, `/guide`.
- **Account deletion**: `/reset`.

The bot handles autonomously:
- User or monster death.
- User level up.
- Monster or object rarity extraction.
- Statistics extraction of the monster encountered.
- Bonus extraction given by Heal, Mystery, Potion_ objects.
- Final evolution of the chosen class.
- Bonus stats entry of classes when user changes.
- Timer jobs (trade and duels).
- Various controls.

## Screenshots

Below are some pictures to make the idea of the bot even clearer:

![Example of welcome message]()
![Example of help command](images/)

## Extra Information

- The balance of monsters, classes, and weapons may not be optimal.
- Images of monsters were quickly made by AI and can easily be replaced by more elaborate images.
- The two databases with all the tables already created are included in the project.
- There is an absence of many comments and the presence of really short descriptions within the code.
- There might be some errors/bugs not found when manually done the test.
- There is no guide.
