import time
import pathlib
import os
import asyncio

from alsa_midi import AsyncSequencerClient, PortType, NoteOnEvent, NoteOffEvent, ActiveSensingEvent
from mido import MidiFile, MidiTrack, Message, MetaMessage, bpm2tempo

DEFAULT_TEMPO_BPM = 500
DEFAULT_TEMPO = int(bpm2tempo(DEFAULT_TEMPO_BPM))
DEFAULT_TICKS_PER_BEAT = 480

DEVICE_CHECK_INTERVAL_SEC = 5.0
MIDI_FILE_TIMEOUT_SEC = 5.0

RECORDING_PATH = '/mnt/nas_drop/midicatcher'

PID_FILE_PATH = "/run/user/1000"
PID_FILE_NAME = os.path.join(PID_FILE_PATH, "midicatcher.pid")
PID_WRITE_INTERVAL_SEC = 5.0

last_pid_write_time = 0.0

def maybe_write_pid():
    global last_pid_write_time
    if time.time()-last_pid_write_time>PID_WRITE_INTERVAL_SEC:
        with open(PID_FILE_NAME, "wt") as f:
            f.write(str(os.getpid()))
        last_pid_write_time = time.time()

def init_midi():
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage('set_tempo', tempo=DEFAULT_TEMPO))
    return mid, track
    track.append(Message('note_off', note=60, velocity=64, time=64))

def add_alsa_event(track, prev_tick, alsa_event):
    event_time = alsa_event.tick - prev_tick
    if isinstance(alsa_event, NoteOnEvent):
        if alsa_event.velocity > 0:
            track.append(Message('note_on', note=alsa_event.note, velocity=alsa_event.velocity, time=event_time))
        else:
            track.append(Message('note_off', note=alsa_event.note, velocity=alsa_event.velocity, time=event_time))
    elif isinstance(alsa_event, NoteOffEvent):
        track.append(Message('note_off', note=alsa_event.note, velocity=alsa_event.velocity, time=event_time))
    else:
        print(f"Ignoring unsupported MIDI event type: {alsa_event}")

def save_midi(mid, start_timestamp):
    local_time = time.localtime(start_timestamp)
    record_path = os.path.join(RECORDING_PATH, time.strftime('%Y-%m-%d', local_time))
    if not os.path.exists(record_path):
        os.mkdir(record_path)
    filename = f"piano_{time.strftime('%Y-%m-%d_%H:%M:%S', local_time)}.mid"
    filepath = os.path.join(record_path, filename)
    mid.save(filepath)
    print(f"Saved midi to {filepath}")

async def start_listening(client, source_port):
    queue = client.create_queue("capture_queue")
    try:
        queue.set_tempo(DEFAULT_TEMPO, DEFAULT_TICKS_PER_BEAT)
        queue.start()
        try:
            in_port = client.create_port("input", timestamping=True, timestamp_real=False, timestamp_queue=queue)
            in_port.connect_from(source_port)
            try:
                last_note_tick = None
                last_note_time = None
                song_start_time = None 
                midi_file = None
                midi_track = None
                try:
                    while last_note_time is None or time.time()-last_note_time < MIDI_FILE_TIMEOUT_SEC:
                        try:
                            event = await asyncio.wait_for(client.event_input(), timeout=1.0)
                            if isinstance(event, ActiveSensingEvent):
                                # We do not want to trigger on this event
                                continue
                            if last_note_tick is None: 
                                await client.drain_output()
                                last_note_tick = 0
                                song_start_time = time.time()
                                midi_file, midi_track = init_midi()

                            #print("Time:", event.tick-last_note_tick, "Event:", repr(event))
                            add_alsa_event(midi_track, last_note_tick, event)
                            last_note_tick = event.tick
                            last_note_time = time.time()
                        except asyncio.TimeoutError:
                            pass
                        maybe_write_pid()
                finally:
                    if midi_file is not None:
                        save_midi(midi_file, song_start_time)

            finally:
                try:
                    in_port.disconnect_from(source_port)
                except:
                    pass
        finally:
            try:
                queue.stop()
                await client.drain_output()
            except:
                pass
    finally:
        try:
            queue.close()
        except:
            pass

async def main():
    print (f"Midicatcher starting @ {time.time()}")
    while not os.path.exists(PID_FILE_PATH):
        print(f"Waiting 1 sec for {PID_FILE_PATH} to be mounted")
        time.sleep(1)
    print(f"Starting to listen...")

    client = AsyncSequencerClient("midicatcher")
    try:
        while True:
            in_ports = client.list_ports(input=True, type=PortType.MIDI_GENERIC | PortType.HARDWARE)

            #print(f"Found {len(in_ports)} MIDI input ports:")
            for i,port in enumerate(in_ports):
                print(f"{i+1}. {port}")

            if len(in_ports) == 0:
                #print(f"No midi input ports found. waiting {DEVICE_CHECK_INTERVAL_SEC} seconds.")
                time.sleep(DEVICE_CHECK_INTERVAL_SEC)
                maybe_write_pid()
            else:
                print(f"Listening on port {in_ports[0]}")
                await start_listening(client, in_ports[0])
                print(f"Restarting...")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())