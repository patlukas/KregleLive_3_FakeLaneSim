import serial
import time
import os
import sys
import signal
import subprocess

COM_PORT = "COM2"
APP_VERSION = "1.0.4"
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

def choose_options(list_options):
    global INTERVAL
    print(f"\033[36m[0]\tZmiana interwału wiadomości")
    for i, option in enumerate(list_options):
        print(f"\033[34m[{i+1}]\t{option}")
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
        name = list_options[a_int-1]
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
        messages = load_messages("templates/"+chosen_option)
        send_messages(serial_port, messages)

if __name__ == '__main__':
    main()