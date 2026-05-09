import argparse
import csv
import datetime as dt
import math
import sys
import time
from pathlib import Path

try:
    import can
    import cantools
except ImportError as err:
    print("Missing dependency:", err)
    print("Run: pip install -r requirements.txt")
    sys.exit(1)


dbc_file = Path("vehicle_fd.dbc")
csv_log = Path("can_fd_decoded_log.csv")
raw_log = Path("can_fd_raw_log.txt")

bus_name = "lucidprep_vcan"
msg_name = "VehStatFd"
rx_timeout = 1.0


def get_db(dbc_path):
    # this failed once when I ran from the wrong folder, so keep the check
    if not dbc_path.exists():
        raise FileNotFoundError(f"DBC file not found: {dbc_path}")

    db = cantools.database.load_file(str(dbc_path))
    return db


def calc_speed(step_num):
    # rough little drive pattern, not meant to be physically perfect
    if step_num < 5:
        return step_num * 8

    speed = 35 + (math.sin(step_num / 4) * 18)

    if speed < 0:
        speed = 0

    return speed


def calc_gear(speed):
    if speed > 55:
        gear = 4
    elif speed > 35:
        gear = 3
    elif speed > 15:
        gear = 2
    else:
        gear = 1

    return gear


def make_sig_vals(step_num):
    speed = calc_speed(step_num)

    rpm = 900 + (speed * 42)
    if rpm > 4200:
        rpm = 4200

    brake = 0
    if step_num > 0 and step_num % 9 == 0:
        brake = 1

    gear = calc_gear(speed)

    sig_vals = {
        "VehSpeed": round(speed, 2),
        "EngRpm": round(rpm, 2),
        "BrkPressed": brake,
        "Gear": gear,
    }
    return sig_vals


def pack_frame(db, sig_vals):
    msg_def = db.get_message_by_name(msg_name)
    payload = db.encode_message(msg_def.frame_id, sig_vals)

    frame = can.Message(
        arbitration_id=msg_def.frame_id,
        data=payload,
        is_extended_id=False,
        is_fd=True,
        bitrate_switch=True,
        error_state_indicator=False,
    )
    return frame


def unpack_frame(db, frame):
    decoded = db.decode_message(frame.arbitration_id, frame.data)
    return decoded


def make_buses():
    # python-can virtual backend needs separate handles here so it feels like tx/rx nodes
    bus_tx = can.Bus(interface="virtual", channel=bus_name, receive_own_messages=False)
    bus_rx = can.Bus(interface="virtual", channel=bus_name, receive_own_messages=False)
    return bus_tx, bus_rx


def write_headers(csv_writer, raw_file):
    cols = []
    cols.append("time")
    cols.append("can_id")
    cols.append("is_fd")
    cols.append("brs")
    cols.append("dlc_bytes")
    cols.append("VehSpeed_kph")
    cols.append("EngRpm")
    cols.append("BrkPressed")
    cols.append("Gear")

    csv_writer.writerow(cols)
    raw_file.write("# raw CAN FD log from python-can virtual channel\n")


def log_one(csv_writer, raw_file, frame, decoded):
    now_txt = dt.datetime.now().isoformat(timespec="milliseconds")
    can_id_txt = f"0x{frame.arbitration_id:X}"

    row = []
    row.append(now_txt)
    row.append(can_id_txt)
    row.append(frame.is_fd)
    row.append(frame.bitrate_switch)
    row.append(len(frame.data))
    row.append(decoded["VehSpeed"])
    row.append(decoded["EngRpm"])
    row.append(decoded["BrkPressed"])
    row.append(decoded["Gear"])

    csv_writer.writerow(row)

    data_txt = ""
    for byte in frame.data:
        if data_txt == "":
            data_txt = f"{byte:02X}"
        else:
            data_txt = data_txt + " " + f"{byte:02X}"

    raw_file.write(
        f"{now_txt} {can_id_txt} FD={frame.is_fd} BRS={frame.bitrate_switch} "
        f"DATA=[{data_txt}] DECODED={decoded}\n"
    )


def run_sim(cycles, delay_sec, dbc_path):
    db = get_db(dbc_path)
    bus_tx, bus_rx = make_buses()

    sent_count = 0
    got_count = 0

    with csv_log.open("w", newline="") as log_csv, raw_log.open("w") as raw_file:
        csv_writer = csv.writer(log_csv)
        write_headers(csv_writer, raw_file)

        for i in range(cycles):
            sig_vals = make_sig_vals(i)
            frame = pack_frame(db, sig_vals)

            bus_tx.send(frame)
            sent_count += 1

            rx_frame = bus_rx.recv(timeout=rx_timeout)
            if rx_frame is None:
                # if this happens on virtual bus, I probably broke the channel name
                print("No CAN frame received on cycle", i)
                continue

            decoded = unpack_frame(db, rx_frame)
            log_one(csv_writer, raw_file, rx_frame, decoded)
            got_count += 1

            print(
                f"{i:02d} sent id=0x{rx_frame.arbitration_id:X} "
                f"speed={decoded['VehSpeed']:.2f} km/h "
                f"rpm={decoded['EngRpm']:.0f} fd={rx_frame.is_fd} brs={rx_frame.bitrate_switch}"
            )

            time.sleep(delay_sec)

    bus_tx.shutdown()
    bus_rx.shutdown()

    print()
    print(f"Done. Sent {sent_count} frames and decoded {got_count}.")
    print(f"Decoded CSV log: {csv_log}")
    print(f"Raw text log: {raw_log}")


def parse_args():
    parser = argparse.ArgumentParser(description="Quick virtual CAN FD logger demo")
    parser.add_argument("--cycles", type=int, default=20, help="how many fake frames to send")
    parser.add_argument("--delay", type=float, default=0.15, help="delay between frames")
    parser.add_argument("--dbc", type=Path, default=dbc_file, help="DBC file to load")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_sim(args.cycles, args.delay, args.dbc)
