#!/bin/bash

# Kill detatched screen sessions
/bin/screen -ls | /bin/grep Detached | cut -d. -f1 | awk '{print $1}' | xargs kill
# Restart the Telegram daemon
screen -dmS telegram /bin/python3 /home/administrator/frc-elo-cruncher/telegram-interface.py
