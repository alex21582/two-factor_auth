import serial
import serial.tools.list_ports
import time
import re
from pathlib import Path


class MacObj:
    def __init__(self, rssi, mac):
        self.rssi = rssi
        self.mac = mac

    def __eq__(self, other):
        return self.mac == other.mac

    def __hash__(self):
        return hash(self.mac)


def find_init_file(file_name: Path) -> bool:
    path_obj = Path(file_name)
    file_found = path_obj.exists()
    return file_found


def read_init_file(file_name: Path) -> set:
    with open(file_name, 'r') as f:
        macs_list = f.readlines()
    return set([string.strip() for string in macs_list])


def read_macs(serial_port: serial) -> (re.Match, re.Match):
    raw_string = serial_port.readline()
    string = raw_string.decode('ISO 8859-1').strip()
    raw_rssi, raw_mac = string.rsplit(sep=",", maxsplit=2)
    mac = re.match(r"(?<!:)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b(?!:)", raw_mac)
    rssi = re.match(r"-\d\d", raw_rssi)
    return rssi, mac


def create_init_macs_set(period: int, serial_port: serial) -> set:
    init_macs_set = set()
    start_time = int(time.time())
    current_time = int(time.time()) - start_time
    while current_time < period:
        _, mac_obj = read_macs(serial_port)
        if mac_obj is not None:
            init_macs_set.add(mac_obj.string)
        else:
            current_time = int(time.time()) - start_time
    serial_port.close()
    return init_macs_set


def write_init_file(init_macs_set: set, file_name: Path) -> None:
    with open(file_name, 'w+', encoding='UTF8', newline='') as f:
        if "ff:ff:ff:ff:ff:ff" not in init_macs_set:
            f.write("ff:ff:ff:ff:ff:ff\n")
        for init_mac in init_macs_set:
            f.write(f"{init_mac}\n")


def get_serial_port() -> serial:
    ports = serial.tools.list_ports.comports()
    for serial_port, desc, _ in ports:
        if desc in ['CH340', 'USB Serial']:
            try:
                s = serial.Serial(serial_port, 115200)
                if s.read():
                    s.close()
                    return serial_port
            except (OSError, serial.SerialException) as ex:
                logger.warning(f"Open serial port error - {type(ex)}: {ex.args}.")
                raise serial.SerialException("Port is unavailable")
