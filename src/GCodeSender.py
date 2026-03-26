from time import sleep
from dataclasses import dataclass
from typing import Tuple

import serial
import serial.tools.list_ports


@dataclass
class DeviceConfig:
    name: str
    vid: int
    pid: int
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float
    baudrate: int = 115200
    response_timeout: float = 1


# Конфиги всех принтеров
DEVICES = (
    DeviceConfig(
        name="BTT MSK Mini v3.0",
        vid=0x0483,
        pid=0x5740,
        x_min=0,
        x_max=220,
        y_min=0,
        y_max=240,
        z_min=0,
        z_max=260,
    ),
)


@dataclass
class SomeGCodes:
    SET_STEPS_PER_UNIT_GCODE: str = "M92 X1600 Y3200 Z1600"
    SET_CURRENT_LIMIT_GCODE: str = "M906 X700 Y700"
    SET_MAX_FEEDRATE_GCODE: str = "M203 X2 Y2 Z2"
    SET_ACCELERATION_GCODE: str = "M204 T10"
    SET_MICROSTEPPING_GCODE: str = "M350 X8 Y8 Z32"
    SET_ABSOLUTE_POSITIONING_GCODE: str = "G90"
    SET_RELETIVE_POSITIONING_GCODE: str = "G91"
    SET_BACKLASH_CORRECTION_GCODE: str = "M425 F1 S0 X0.1 Y0.1 Z0.0"
    HOME_GCODE: str = "G28"
    HOME_X_GCODE: str = "G28 X"
    HOME_Y_GCODE: str = "G28 Y"
    HOME_Z_GCODE: str = "G28 Z"


class GCodeSender:
    def __init__(self, config: DeviceConfig) -> None:
        self.config = config
        self.serial = None
        return

    def connect(self) -> None:
        if self.serial and self.serial.is_open:
            self.close()

        port = self._find_printer_port()
        if not port:
            raise Exception("Device not found")

        try:
            self.serial = serial.Serial(
                port, self.config.baudrate, timeout=self.config.response_timeout
            )
            return True
        except Exception as e:
            raise e
        return

    def close(self) -> None:
        if self.serial and self.serial.is_open:
            self.serial.close()
        return

    def go_to(
        self,
        x: float = None,
        y: float = None,
        z: float = None,
        need_to_await=True,
        speed: float = 3000,
    ) -> None:
        if x is not None and not (self.config.x_min <= x <= self.config.x_max):
            raise ValueError(
                f"X={x} out of borders [{self.config.x_min}, {self.config.x_max}]"
            )
        if y is not None and not (self.config.y_min <= y <= self.config.y_max):
            raise ValueError(
                f"Y={y} out of borders [{self.config.y_min}, {self.config.y_max}]"
            )
        if z is not None and not (self.config.z_min <= z <= self.config.z_max):
            raise ValueError(
                f"Z={z} out of borders [{self.config.z_min}, {self.config.z_max}]"
            )

        gcode = "G01"
        if x is not None:
            gcode += f" X{x}"
        if y is not None:
            gcode += f" Y{y}"
        if z is not None:
            gcode += f" Z{z}"
        gcode += f" F{speed}"

        self.send_command(gcode, need_to_await)
        return

    def get_pos(self) -> Tuple[float, float, float]:
        """M114 -> X:123.00 Y:456.00 Z:78.00"""
        if not self.serial or not self.serial.is_open:
            raise Exception("Device is not connected")

        self.serial.write(f"M114\n".encode())
        position = []
        while True:
            line = self.serial.readline().decode()
            if line.startswith("X:"):
                parts = line.split()
                position.append(float(parts[0][2:]))
                position.append(float(parts[1][2:]))
                position.append(float(parts[2][2:]))
                break
            if not line:
                return

        return position

    def home(
        self,
        home_x: bool = True,
        home_y: bool = True,
        home_z: bool = True,
        need_to_await=True,
    ) -> None:
        """Калибровка осей (G28)."""
        if all((home_x, home_y, home_z)):
            self.send_command("G28 Z", need_to_await=need_to_await)
            self.send_command("G28 X", need_to_await=need_to_await)
            self.send_command("G28 Y", need_to_await=need_to_await)
            return

        if home_x:
            self.send_command("G28 X", need_to_await=need_to_await)
        if home_y:
            self.send_command("G28 Y", need_to_await=need_to_await)
        if home_z:
            self.send_command("G28 Z", need_to_await=need_to_await)

        return

    def _find_printer_port(self):
        for port in serial.tools.list_ports.comports():
            if (
                self.config.vid
                and self.config.pid
                and (port.vid == self.config.vid and port.pid == self.config.pid)
            ):
                return port.device
        return None

    def send_command(self, command: str, need_to_await: bool = True) -> str:
        if not self.serial or not self.serial.is_open:
            raise Exception("Device is not connected")

        if need_to_await:
            self.clear_buffers()

        self.serial.write(f"{command}\n".encode())

        if need_to_await:
            self.serial.write("M400\n".encode())
            ok_count = 0
            response = []
            while True:
                line = self.serial.readline().decode()
                if line:
                    response.append(line)
                if "ok" in line:
                    ok_count += 1
                    if ok_count == 2:
                        break
            return "\n".join(response)

        return ""

    def clear_buffers(self) -> None:
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        sleep(0.1)
        return
