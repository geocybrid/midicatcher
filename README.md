# midicatcher
Simple python script to watch midi keyboard and record when activity is detected. Intended for use with Raspberry Pi Zero 2 W, which is configured appropriately (more on that below).

**WARNING:** Extremely early WIP. Everything is hardcoded in the main.py constants.

## Basic features

* Looks for midi input device and opens once discovered.
* Waits for the first note, then starts the queue and records midi events.
* After certain inactivity timeout saves the midi file to an archive folder.
* Archive is organized by date and time. It is expected to be on a NFS share that is mounted over wifi.
* Watchdog "friendly" for stability. Keeps updating pid file in /run/user/1000 so that watchdog service can monitor health.
* Tries to handle disconnection and reconnection of midi devices gracefully, so that script doesn't crash.

## Some of the issues
* Currently doesn't try to detect tempo - uses high fixed value. Hence on some players this messes up recording badly.
* Watchdog triggers sometimes without reason - need more investigation (watchdog config will be added later)
* Some of the events are not yet supported, e.g. control changes, which are needed for pedals and any other expression.
* Some keyboards send sense messages, which this script ignores, however this causes the keyboard to not auto-power-off after inactivity period. Needs more testing.
* There are some crashes (especially watchdog reset) that lead to the loss of a recording in memory.

