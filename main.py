import serial
import time
import os
import sys
import signal

APP_VERSION = "1.0.0"
INTERVAL = 0.001
running = True
running_loop = False

def init_serial_port():
    port = input("Podaj numer portu COM (domyślnie COM2): ") or "COM2"
    ser = serial.Serial(
        port=port,
        baudrate=9600,
        timeout=1
    )
    return ser

def send_messages(serial_port, messages):
    global running_loop
    length = len(messages)
    start_time = time.time()
    running_loop = True
    for i, message in enumerate(messages):
        if not running:
            return
        if not running_loop:
            return
        serial_port.write(message)
        elapsed_time = time.time() - start_time
        if elapsed_time != 0:
            msg_to_s = i / elapsed_time
        else:
            msg_to_s = 0
        sys.stdout.write(f"\r                                                                                                 ")
        sys.stdout.write(f"\r{i}/{length}\t|\t{i * 100 / length:.3f}%\t|\t{elapsed_time:.3f}s\t|\t{msg_to_s:.1f} message/s\t CTRL-C - ends the loop")  # Nadpisanie linii
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
    print(f"[0]\tZmiena interwału wiadomości, aktualnie jest {INTERVAL}")
    for i, option in enumerate(list_options):
        print(f"[{i+1}]\t{option}")
    a = input("Wybierz numer szablonu: ")
    print("\n")
    try:
        a_int = int(a)
        if a_int == 0:
            i = input(f"Podaj nowy interwał (domyślnie {INTERVAL}): ") or str(INTERVAL)
            i_int = float(i)
            INTERVAL = i_int
            return None
        name = list_options[a_int-1]
        print("Wybrano szablon: ", name)
        return name
    except EOFError:
        raise EOFError
    except Exception:
        print("Wystąpił błąd")
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
    print("\n⛔ Otrzymano Ctrl + C")
    if running_loop:
        print("Przerywanie pętli...")
        running_loop = False
    else:
        print("Kończenie programu...")
        running = False

def main():
    signal.signal(signal.SIGINT, exit_handler)
    serial_port = init_serial_port()
    list_templates = get_template_files()
    while running:
        try:
            chosen_option = choose_options(list_templates)
        except EOFError:
            continue
        if chosen_option is None:
            continue
        messages = load_messages("templates/"+chosen_option)
        send_messages(serial_port, messages)

main()