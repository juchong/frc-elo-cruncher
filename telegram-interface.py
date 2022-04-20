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

from numpy import empty
import creds
import mysql.connector
from uuid import uuid4

from telegram import InlineQueryResultArticle, ParseMode, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown

# Configure SQL Connector
scoutingdb = mysql.connector.connect(
	host=creds.HOST,
	user=creds.USER,
	passwd=creds.PASS,
	database=creds.DB,
    connect_timeout=31536000
)

dbcursor = scoutingdb.cursor()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# /teamelo <team#>
def teamelo(update: Update, context: CallbackContext) -> None:
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
        update.message.reply_text('Team {} Elo: {}'.format(tnum, round(telofin,2)))

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /teamelo <team number>')
    
# /fieldelo 
def fieldelo(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    try:
        ecode = context.args[0]
        print(ecode)
        dbcursor.execute("SELECT `eventkey` FROM `eventlist` WHERE 1")
        vevents = dbcursor.fetchall()
        validevents = []
        for x in range(0,len(vevents),1):
            validevents.append(str(vevents[x][0]))
        #print(validevents)
        if (ecode not in validevents):
            update.message.reply_text('Invalid event code! Try again.')
            return
        update.message.reply_text('{} Elo:'.format(ecode) + '\n' + field_query(ecode))
        
    except (IndexError, ValueError):
        # Show buttons for champs if no event code is provided
        cmp22field = [
            [
                InlineKeyboardButton("Carver", callback_data='2022carv'),
                InlineKeyboardButton("Galileo", callback_data='2022gal'),
                InlineKeyboardButton("Hopper", callback_data='2022hop'),
            ],
            [
                InlineKeyboardButton("Newton", callback_data='2022new'),
                InlineKeyboardButton("Roebling", callback_data='2022roe'),
                InlineKeyboardButton("Turing", callback_data='2022tur'),
            ],
            [InlineKeyboardButton("PNWCMP (DEBUG)", callback_data='2022pncmp')],
        ]
        reply_markup = InlineKeyboardMarkup(cmp22field)
        update.message.reply_text('Please choose a field:', reply_markup=reply_markup)

def matchelo(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id   

    try:
        ecode = context.args[0]
        '''
        dbcursor.execute("SELECT `eventkey` FROM `eventlist` WHERE 1")
        vevents = dbcursor.fetchall()
        validevents = []
        for x in range(0,len(vevents),1):
            validevents.append(str(vevents[x][0]))
        #print(validevents)
        if (ecode not in validevents):
            update.message.reply_text('Invalid event code! Try again.')
            return
        '''
        update.message.reply_text('{} Elo:'.format(ecode) + '\n' + match_query(ecode))

    except (IndexError, ValueError):
        # Show buttons for champs if no event code is provided
        cmp22field = [
            [
                InlineKeyboardButton("Carver", callback_data='2022carv'),
                InlineKeyboardButton("Galileo", callback_data='2022gal'),
                InlineKeyboardButton("Hopper", callback_data='2022hop'),
            ],
            [
                InlineKeyboardButton("Newton", callback_data='2022new'),
                InlineKeyboardButton("Roebling", callback_data='2022roe'),
                InlineKeyboardButton("Turing", callback_data='2022tur'),
            ],
            [InlineKeyboardButton("PNWCMP (DEBUG)", callback_data='2022pncmp')],
        ]
        reply_markup = InlineKeyboardMarkup(cmp22field)
        update.message.reply_text('Please choose a field:', reply_markup=reply_markup)

# /fieldelo button handler
def cmp22field_button(update: Update, context: CallbackContext) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(text=f"{query.data} Elo:" + "\n" + "\n" + field_query(query.data))

# Performs a field Elo query
def field_query(dat: str):
    dbcursor.execute("SELECT `teamnumber`, `currentelo` from teamEloList as tel join ( \
    SELECT DISTINCT team from (SELECT DISTINCT red1 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}' UNION \
    SELECT DISTINCT red2 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}' UNION \
    SELECT DISTINCT red3 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}' UNION \
    SELECT DISTINCT blue1 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}' UNION \
    SELECT DISTINCT blue2 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}' UNION \
    SELECT DISTINCT blue3 as team from mastermatchlist as mml1 where mml1.eventkey = '{0}') as team) as t on tel.teamnumber = t.team \
    ORDER BY `tel`.`currentelo` DESC".format(dat))
    felo = dbcursor.fetchall()
    felofin = ""
    for x in range(0,len(felo),1):
        felofin = felofin + str(felo[x][0]) + ' - ' + str(round(felo[x][1],2)) + '\n'
    #print(felofin)
    return felofin

def match_query(dat: str):
    dbcursor.execute("SELECT mml.red1, mml.red2, mml.red3, mml.blue1, mml.blue2, mml.blue3, \
    telR.currentelo,  telRR.currentelo,  telRRR.currentelo, telB.currentelo,  telBB.currentelo,  telBBB.currentelo, \
    mml.predictedredmargin, mml.actualmargin \
    FROM `mastermatchlist` as mml \
    LEFT JOIN teamEloList as telR on telR.teamnumber = mml.red1 \
    LEFT JOIN teamEloList as telRR on telRR.teamnumber = mml.red2 \
    LEFT JOIN teamEloList as telRRR on telRRR.teamnumber = mml.red3 \
    LEFT JOIN teamEloList as telB on telB.teamnumber = mml.blue1 \
    LEFT JOIN teamEloList as telBB on telBB.teamnumber = mml.blue2 \
    LEFT JOIN teamEloList as telBBB on telBBB.teamnumber = mml.blue3 \
    where mml.matchkey = '{}'".format(dat))
    mraw = dbcursor.fetchall()
    #print(mraw)

    if mraw[0][12] > 0:
        pwinner = "Red Alliance"
    else:
        pwinner = "Blue Alliance"

    if mraw[0][13] > 0:
        awinner = "Red Alliance"
    elif mraw[0][13] < 0:
        awinner = "Blue Alliance"
    elif mraw[0][13] == 0:
        awinner = "???"

    message = ""
    message = message + "Red1: " + str(mraw[0][0]) + " - " + str(round(mraw[0][6],2)) + "\n"
    message = message + "Red2: " + str(mraw[0][1]) + " - " + str(round(mraw[0][7],2)) + "\n"
    message = message + "Red3: " + str(mraw[0][2]) + " - " + str(round(mraw[0][8],2)) + "\n"
    message = message + "Blue1: " + str(mraw[0][3]) + " - " + str(round(mraw[0][9],2)) + "\n"
    message = message + "Blue2: " + str(mraw[0][4]) + " - " + str(round(mraw[0][10],2)) + "\n"
    message = message + "Blue3: " + str(mraw[0][5]) + " - " + str(round(mraw[0][11],2)) + "\n"
    message = message + "\n"
    message = message + "Predicted Winner: " + pwinner + "\n"
    message = message + "Predicted Margin: " + str(abs(round(mraw[0][12],2))) + "\n"
    message = message + "Actual Winner: " + awinner + "\n"
    if mraw[0][13] == 0:
        message = message + "Actual Margin: ???" + "\n"
    else:
        message = message + "Actual Margin: " + str(abs(round(mraw[0][13],2))) + "\n"
    #print(message)
    return message

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
    updater.dispatcher.add_handler(CallbackQueryHandler(cmp22field_button))

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()