#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic inline bot example. Applies different text transformations.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import decimal
import logging
import re
import creds
import mysql.connector
from uuid import uuid4

from telegram import InlineQueryResultArticle, ParseMode, InputTextMessageContent, Update
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, CallbackContext
from telegram.utils.helpers import escape_markdown

# Configure SQL Connector
scoutingdb = mysql.connector.connect(
	host=creds.HOST,
	user=creds.USER,
	passwd=creds.PASS,
	database=creds.DB
)

dbcursor = scoutingdb.cursor()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Set up global defines
fieldlist = [
    '2022carv',
    '2022gal',
    '2022hop',
    '2022new',
    '2022roe',
    '2022tur',
    '2022pncmp'
]

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def teamelo(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /teamelo is issued."""
    chat_id = update.message.chat_id
    try:
        tnum = int(context.args[0])
        if tnum < 0:
            update.message.reply_text('Invalid team number! Please try again.')
            return
        
        if tnum > 9999:
            update.message.reply_text('Invalid team number! Please try again.')
            return

        dbcursor.execute("SELECT `slowelo` FROM `teamEloList` WHERE `teamnumber` = {}".format(tnum))
        telo = dbcursor.fetchall()
        telofin = decimal.Decimal(telo[0][0])
        update.message.reply_text('Team {} ELO: {}'.format(tnum, round(telofin,2)))

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /teamelo <team number>')
    


def fieldelo(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /fieldelo is issued."""
    chat_id = update.message.chat_id
    try:
        ecode = context.args[0]
        print(ecode)
        if (ecode not in fieldlist):
            update.message.reply_text('Invalid event code! Valid codes: 2022carv, 2022gal, 2022hop, 2022new, 2022roe, 2022tur')
            return

        dbcursor.execute("SELECT `teamnumber`, `currentelo` from teamEloList as tel join ( \
        SELECT DISTINCT team from (SELECT DISTINCT red1 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}' UNION \
        SELECT DISTINCT red2 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}' UNION \
        SELECT DISTINCT red3 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}' UNION \
        SELECT DISTINCT blue1 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}' UNION \
        SELECT DISTINCT blue2 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}' UNION \
        SELECT DISTINCT blue3 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}') as team) as t on tel.teamnumber = t.team \
        ORDER BY `tel`.`currentelo` DESC".format(ecode))
        felo = dbcursor.fetchall()
        #print(felo)
        felofin = ""
        for x in range(0,len(felo),1):
            felofin = felofin + str(felo[x][0]) + ' - ' + str(round(felo[x][1],2)) + '\n'
        print(felofin)
        update.message.reply_text('{} ELO:'.format(ecode) + '\n' + felofin)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /fieldelo <TBA event code>')

def matchelo(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /matchelo is issued."""
    update.message.reply_text('Match ELO:')

def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(creds.TELEGRAM_KEY)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("teamelo", teamelo))
    dispatcher.add_handler(CommandHandler("fieldelo", fieldelo))
    dispatcher.add_handler(CommandHandler("matchelo", matchelo))

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()