import random

import serial
import time
import os
import sys
import signal
import subprocess
from datetime import datetime


COM_PORT = "COM2"
APP_VERSION = "1.0.5"
INTERVAL = 0.001
running = True
running_loop = False

def clear_console():
    subprocess.call('clear' if os.name == 'posix' else 'cls', shell=True)
    print(f"Port: {COM_PORT}\t\tBaudrate: 9600\t\tInterwał wiadomości: {INTERVAL}s\n")

def init_serial_port():
    global COM_PORT
    while True:
        try:
            COM_PORT = input(f"Podaj numer portu COM (domyslnie {COM_PORT}): ") or COM_PORT
            ser = serial.Serial(
                port=COM_PORT,
                baudrate=9600,
                timeout=1
            )
            return ser
        except serial.serialutil.SerialException:
            print(f"\033[41mPort {COM_PORT} jest zajęty, wybierz inny\033[0m")
        except EOFError:
            return None

def print_stat(nr_sent, all_to_send, elapsed_time, color, finished=False):
    nr_sent += 1
    if elapsed_time != 0:
        msg_to_s = nr_sent / elapsed_time
    else:
        msg_to_s = 0
    sys.stdout.write("\r\033[K")
    sys.stdout.write(f"\r{color}{nr_sent}/{all_to_send}\t\t{nr_sent * 100 / all_to_send:.3f}%\t\t{elapsed_time:.3f}s\t\t{msg_to_s:.1f} message/s")
    if not finished:
        sys.stdout.write("\t\tCTRL-C - ends the loop")
    sys.stdout.write("\033[0m")

def send_messages(serial_port, messages):
    global running_loop
    length = len(messages)
    start_time = time.time()
    running_loop = True
    for i, message in enumerate(messages):
        serial_port.write(message)
        elapsed_time = time.time() - start_time
        if not running or not running_loop:
            print_stat(i, length, elapsed_time, "\033[31m", True)
            break
        if i == length-1:
            print_stat(i, length, elapsed_time, "\033[32m", True)
            break
        else:
            print_stat(i, length, elapsed_time, "\033[33m")
        sys.stdout.flush()
        time.sleep(INTERVAL)
    running_loop = False
    print("\n")

def get_template_files(folder="templates"):
    if not os.path.exists(folder):
        return []
    return [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

def send_msg(serial_port, body_msg):
    checksum = get_check_sum(body_msg)
    msg = body_msg + checksum + b"\r"
    serial_port.write(msg)
    return msg

def generate_new_throw(lane_state):
    throw_int = int(lane_state["throw"], 16) + 1
    if throw_int > lane_state["throw_limit"]:
        last_mode = lane_state["mode"]
        lane_state["mode"] = 0
        return last_mode
    throw_result = random.randint(0, 9)
    lane_sum_int = int(lane_state["lane_sum"], 16) + throw_result
    total_sum_int = int(lane_state["total_sum"], 16) + throw_result
    empty_throw_int = int(lane_state["lane_sum"], 16) + (1 if throw_result == 0 else 0)
    time_int = int(lane_state["time"], 16)
    if time_int > 0:
        time_int -= 1
    lane_state["throw"] = bytes(format(throw_int, '03X'), 'utf-8')
    lane_state["throw_result"] = bytes(format(throw_result, '03X'), 'utf-8')
    lane_state["lane_sum"] = bytes(format(lane_sum_int, '03X'), 'utf-8')
    lane_state["total_sum"] = bytes(format(total_sum_int, '03X'), 'utf-8')
    lane_state["empty_throw"] = bytes(format(empty_throw_int, '03X'), 'utf-8')
    lane_state["time"] = bytes(format(time_int, '03X'), 'utf-8')
    return 0

def interactive_mode(serial_port):
    global running_loop
    running_loop = True
    lane_state = []
    number_of_lane = 6
    for i in range(number_of_lane):
        lane_state.append({
            "throw_limit": 0,
            "time": b"285",
            "mode": 0, #0 - no mode, 1 - probe, 2 - normal game
            "throw": b"000",
            "throw_result": b"000",
            "lane_sum": b"000",
            "total_sum": b"000",
            "empty_throw": b"000"
        })
    while True:
        if not running or not running_loop:
            break
        number_of_waiting_bytes = serial_port.in_waiting
        if number_of_waiting_bytes == 0:
            continue
        msgs = serial_port.read(number_of_waiting_bytes)
        for msg in msgs.split(b"\r"):
            if msg == b"":
                continue
            head = msg[2:4] + msg[0:2]
            lane_number = int(msg[1:2])
            body = b""
            if msg[4:5] == b"S":
                body = b"s100000FF"
            elif len(msg) == 6:
                l = lane_state[lane_number]
                lane_time = l["time"]
                if l["mode"] == 0:
                    body = lane_time
                else:
                    mode_end = generate_new_throw(l)
                    if mode_end > 0:
                        if mode_end == 1:
                            body = b"p0"
                        else:
                            body = b"i0"
                    else:
                        throw = l["throw"]
                        throw_result = l["throw_result"]
                        lane_sum = l["lane_sum"]
                        total_sum = l["total_sum"]
                        empty_throw = l["empty_throw"]
                        body = b"w" + throw + throw_result + lane_sum + total_sum + b"000" + empty_throw + lane_time + b"000000"
            elif msg[4:6] == b"IG":
                lane_state[lane_number] = {
                    "throw_limit": int(msg[6:9], 16) + int(msg[9:12], 16),
                    "time": msg[12:15],
                    "mode": 2,
                    "throw": b"000",
                    "throw_result": b"000",
                    "lane_sum": b"000",
                    "total_sum": msg[15:18],
                    "empty_throw": msg[18:21]
                }
                body = b"i1"
            elif msg[4:5] == b"P":
                lane_state[lane_number] = {
                    "throw_limit": int(msg[5:8], 16),
                    "time": msg[8:11],
                    "mode": 1,
                    "throw": b"000",
                    "throw_result": b"000",
                    "lane_sum": b"000",
                    "total_sum": b"000",
                    "empty_throw": b"000"
                }
                body = b"p1"
            elif msg[4:5] == b"M":
                body = lane_state[lane_number]["time"]
            elif msg[4:5] == b"E":
                body = lane_state[lane_number]["time"]
            elif msg[4:5] == b"U":
                body = lane_state[lane_number]["time"]
            elif msg[4:5] == b"T":
                body = lane_state[lane_number]["time"]
            else:
                print(f"{datetime.now().strftime("%H:%M:%S %f")[:-3]} | \t[????????????????????????????????????????????]: {msg}")
                continue
            msg_sent = send_msg(serial_port, head + body)
            print(f"{datetime.now().strftime("%H:%M:%S %f")[:-3]} | \t<-- {msg} \t | --> {msg_sent}")

def get_check_sum(message: bytes) -> bytes:
    sum_ascii = 0
    for x in message:
        sum_ascii += x
    return bytes(hex(sum_ascii).split("x")[-1].upper()[-2:], 'utf-8')

def choose_options(list_options):
    global INTERVAL
    print(f"\033[36m[0]\tZmiana interwału wiadomości")
    print(f"\033[36m[1]\tInteraktwny tryb [Odpowiadanie serwerowi]")
    for i, option in enumerate(list_options):
        print(f"\033[34m[{i+2}]\t{option}")
    a = input("\033[0mWybierz numer szablonu: ")
    print("\n")
    try:
        a_int = int(a)
        if a_int == 0:
            i = input(f"Podaj nowy interwał (domyślnie {INTERVAL}): ") or str(INTERVAL)
            i_int = float(i)
            INTERVAL = i_int
            clear_console()
            return None
        if a_int == 1:
            return 1
        name = list_options[a_int-2]
        clear_console()
        print(f"Wybrano szablon: \033[42m{name}\033[0m")
        return name
    except EOFError:
        raise EOFError
    except Exception:
        print("\033[41mWystąpił błąd\033[0m")
        return None

def load_messages(file_name):
    messages = []
    with open(file_name, 'rb') as file:
        for line in file:
            l = line.split(b"\t")
            if b"COM_SEND" in l[3]:
                m = l[5][2:-3].replace(b'\\r', b"\r")
                m = m.replace(b'\\xb3', b"\xb3")
                messages.append(m)
    return messages

def exit_handler(signal_received, frame):
    global running, running_loop
    if running_loop:
        running_loop = False
    else:
        print("\n\033[43mKończenie programu...\033[0m")
        running = False

def main():
    subprocess.call('clear' if os.name == 'posix' else 'cls', shell=True)
    signal.signal(signal.SIGINT, exit_handler)
    serial_port = init_serial_port()
    if serial_port is None:
        return
    list_templates = get_template_files()
    clear_console()
    while running:
        try:
            chosen_option = choose_options(list_templates)
        except EOFError:
            continue
        if chosen_option is None:
            continue
        if isinstance(chosen_option, str):
            messages = load_messages("templates/"+chosen_option)
            send_messages(serial_port, messages)
        if chosen_option == 1:
            interactive_mode(serial_port)

if __name__ == '__main__':
    main()