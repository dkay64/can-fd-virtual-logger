# Virtual CAN FD Logger

Mini Project 1 for my LucidPrep CAN/CAN FD prep.

This is a small Python demo that sends a fake vehicle status message on a virtual CAN bus, then receives and decodes it with a DBC. I used it to practice the full path:

```text
signal values -> DBC encode -> CAN FD frame -> virtual bus -> DBC decode -> logs
```

It is not meant to be a polished library. It is just a working mini project I can explain and run.

## Files

```text
can_fd_sim_logger.py      main script
vehicle_fd.dbc            CAN database for the fake vehicle message
requirements.txt          python-can + cantools
can_fd_decoded_log.csv    decoded signal log, regenerated each run
can_fd_raw_log.txt        raw payload log, regenerated each run
.gitignore                ignores Python cache files
```

## Setup Notes

I made a separate conda env for this:

```bash
conda create -n can_env
conda activate can_env
```

Then from the project folder:

```bash
pip install -r requirements.txt
```

## Run

```bash
python can_fd_sim_logger.py
```

Optional faster/smaller run:

```bash
python can_fd_sim_logger.py --cycles 5 --delay 0
```

The script overwrites these logs every time:

```text
can_fd_decoded_log.csv
can_fd_raw_log.txt
```


```bash
python can_fd_decoded_log.csv
```

That fails in terminal because the CSV is output data, not code. Use `type can_fd_decoded_log.csv` on Windows or just open it in VS Code / Excel.

## What The Script Does

`can_fd_sim_logger.py`:

- loads `vehicle_fd.dbc`
- builds a fake speed/rpm/brake/gear signal set
- encodes those signals into the DBC message
- sends a CAN FD frame on the `python-can` virtual bus
- receives the frame on another virtual bus handle
- decodes the raw bytes back into signal values
- writes a CSV log and a raw text log

The virtual bus channel is:

```text
lucidprep_vcan
```

The CAN FD frame is created with:

```python
is_fd=True
bitrate_switch=True
```

`bitrate_switch=True` is the BRS part. My understanding: arbitration still has to happen at the normal arbitration rate, then the data phase can switch faster for CAN FD.

## DBC Message

The DBC message is:

```text
BO_ 291 VehStatFd: 16 SIM_ECU
```

`291` decimal is `0x123`, which is the CAN ID printed by the script.

Signals:

| Signal | Meaning | Scale |
| --- | --- | --- |
| `VehSpeed` | fake vehicle speed | `0.01 km/h` per bit |
| `EngRpm` | estimated engine RPM | `0.25 rpm` per bit |
| `BrkPressed` | brake flag | `0` or `1` |
| `Gear` | fake gear value | integer |

The names are shortened because I wanted the project to feel closer to quick working code, not a huge generated example.

## Sample Run

```text
00 sent id=0x123 speed=0.00 km/h rpm=900 fd=True brs=True
01 sent id=0x123 speed=8.00 km/h rpm=1236 fd=True brs=True
02 sent id=0x123 speed=16.00 km/h rpm=1572 fd=True brs=True
03 sent id=0x123 speed=24.00 km/h rpm=1908 fd=True brs=True
04 sent id=0x123 speed=32.00 km/h rpm=2244 fd=True brs=True
...
19 sent id=0x123 speed=17.01 km/h rpm=1614 fd=True brs=True

Done. Sent 20 frames and decoded 20.
Decoded CSV log: can_fd_decoded_log.csv
Raw text log: can_fd_raw_log.txt
```

## Decoded Log Example

```csv
time,can_id,is_fd,brs,dlc_bytes,VehSpeed_kph,EngRpm,BrkPressed,Gear
2026-05-09T15:28:30.041,0x123,True,True,16,0.0,900.0,0,1
2026-05-09T15:28:30.191,0x123,True,True,16,8.0,1236.0,0,1
2026-05-09T15:28:30.342,0x123,True,True,16,16.0,1572.0,0,2
```

## Raw Log Example

```text
2026-05-09T15:28:30.041 0x123 FD=True BRS=True DATA=[00 00 10 0E 00 01 00 00 00 00 00 00 00 00 00 00] DECODED={'VehSpeed': 0.0, 'EngRpm': 900.0, 'BrkPressed': 0, 'Gear': 1}
2026-05-09T15:28:30.191 0x123 FD=True BRS=True DATA=[20 03 50 13 00 01 00 00 00 00 00 00 00 00 00 00] DECODED={'VehSpeed': 8.0, 'EngRpm': 1236.0, 'BrkPressed': 0, 'Gear': 1}
2026-05-09T15:28:30.342 0x123 FD=True BRS=True DATA=[40 06 90 18 00 02 00 00 00 00 00 00 00 00 00 00] DECODED={'VehSpeed': 16.0, 'EngRpm': 1572.0, 'BrkPressed': 0, 'Gear': 2}
```

The raw log is the part I care about most. It shows that values are actually being serialized into bytes and decoded back, not just printed from the original Python variables.

## Quick DBC vs ARXML Note

DBC is simpler and common for CAN signal databases. It tells tools how message IDs, payload bytes, signals, scaling, units, and receivers fit together.

ARXML is the AUTOSAR format. It can describe more of the full vehicle software/communication setup, including ECUs, PDUs, frames, signals, and mappings. It is more complete but also heavier to read.
