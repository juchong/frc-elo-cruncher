#!/bin/bash

LOCKDIR=/tmp/CRUNCHING

#Remove the lock directory
function cleanup {
    if rmdir $LOCKDIR; then
        echo "Finished"
    else
        echo "Failed to remove lock directory '$LOCKDIR'"
        exit 1
    fi
}

if mkdir $LOCKDIR; then
    #Ensure that if we "grabbed a lock", we release it
    #Works for SIGTERM and SIGINT(Ctrl-C)
    trap "cleanup" EXIT

    echo "Acquired lock, running"

    /bin/python3 /home/administrator/frc-elo-cruncher/tbapull2020.py --run
else
    echo "Could not create lock directory '$LOCKDIR'"
    exit 1
fi
