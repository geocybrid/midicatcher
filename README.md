# midicatcher
Simple python script to watch midi keyboard and record when activity is detected. Intended for use with Raspberry Pi Zero 2 W, which is configured appropriately (more on that below).

**WARNING:** Extremely early WIP. Everything is hardcoded in the main.py constants.

## Basic features

* Looks for midi input device and opens once discovered.
* Waits for the first note, then starts the queue and records midi events.
* After certain inactivity timeout saves the midi file to an archive folder.
* Archive is organized by date and time. It is expected to be on a NFS share that is mounted over wifi.
* Watchdog "friendly" for stability. Keeps updating pid file in `/run/user/1000` so that watchdog service can monitor health.
* Tries to handle disconnection and reconnection of midi devices gracefully, so that script doesn't crash.

## Some of the issues

* Currently doesn't try to detect tempo - uses high fixed value. Hence, on some players this messes up recording badly.
* Watchdog triggers sometimes without reason - need more investigation (watchdog config will be added later)
* Some of the events are not yet supported, e.g. control changes, which are needed for pedals and any other expression.
* Some keyboards send sense messages, which this script ignores, however this causes the keyboard to not auto-power-off after inactivity period. Needs more testing.
* There are some crashes (especially watchdog reset) that lead to the loss of a recording in memory.

## Raspberry Pi setup

This script was developped on a 64-bit Raspberry Pi OS Legacy Lite (bullseye) for Pi Zero 2 W.

### Config.txt settings and raspi-config
GPU VRAM was set to 16M (which is minimum allowed) using `sudo raspi-config`
Most of the features were disabled/tweaked in `/boot/config.txt`:
```
   dtoverlay=disable-bt
   dtparam=audio=off
   camera_auto_detect=0
   display_auto_detect=0
   dtparam=watchdog=on
```
**Note 1:** the watchdog is enabled by default. Adding this explicit param is actually to help you disable it quickly by changing `on` to `off`, should the device be caught in a reboot loop.
**Note 2:** the watchdog is required to successfully reboot the pi. So if you disable it and then use `sudo reboot` it will essentially result in a halt with no way to recover remotely.

### OS and python packages
```
  sudo apt-get install libasound2-dev
  sudo apt-get install python3-pip
  sudo apt-get install nfs-common
  sudo apt-get install watchdog

  pip install -r requirements.txt
```
**Note:** This doesn't actually set up watchdog correctly. Configuring it correctly is not trivial and probably better done using dedicated manuals.


### Logging setup
Since this device is supposed to be left running all the time, SD card wear is a concern. To this end, it makes sense to redirect logs to an external server and disable local logging.

Disable journalctl logging to disk:
`/etc/systemd/journald.conf` should contain
    [Journal]
    Storage=volatile
    RuntimeMaxUse=64M

`/etc/rsyslog.conf` can be changed to comment out all local destinations and only add remote, for example:
    *.* @192.168.1.3
(obviously, 192.168.1.3 must have syslog receiving configured)

### Service setup
Make a symlink from the service file in this repo to `/lib/systemd/system/midicatcher.service`, then use the following commands to activate:
```
   sudo systemctl daemon-reload
   sudo systemctl enable midicatcher.service
   sudo systemctl start midicatcher.service
```
### NFS setup
Once the server (in this case - `/volume1/drop` on `192.168.1.3`) share is configured, test connectivity using the commands:
```
   sudo mkdir /mnt/nas_drop
   sudo mount 192.168.1.3:/volume1/drop /mnt/nas_drop
```
Afterwards, add row to /etc/fstab:
```
   192.168.1.3:/volume1/drop       /mnt/nas_drop   nfs auto,nofail,noatime,nolock,intr,tcp,actimeo=1800    0       0
```
Then it can be immediately mounted using: `sudo mount /mnt/nas_drop`
