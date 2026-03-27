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
    SET_BACKLASH_CORRECTION_GCODE: str = "M425 F1 S0 X0.3 Y0.1 Z0.0"
    HOME_GCODE: str = "G28"
    HOME_X_GCODE: str = "G28 X"
    HOME_Y_GCODE: str = "G28 Y"
    HOME_Z_GCODE: str = "G28 Z"


class GCodeSender:
    def __init__(self, config: DeviceConfig) -> None:
        """Constructor for GCodeSender class.

        :param config: Config for device to connect to.
        :type config: DeviceConfig

        :returns:
        :rtype: None
        """
        self.config = config
        self.serial = None
        return

    def _find_printer_port(self) -> str | None:
        for port in serial.tools.list_ports.comports():
            if (
                self.config.vid
                and self.config.pid
                and port.vid == self.config.vid
                and port.pid == self.config.pid
            ):
                return port.device
        return

    def connect(self) -> None:
        """Establishe the connection with device.

        :returns:
        :rtype: None
        """
        if self.serial and self.serial.is_open:
            self.close()

        port = self._find_printer_port()
        if not port:
            raise Exception("Device not found")

        self.serial = serial.Serial(
            port, self.config.baudrate, timeout=self.config.response_timeout
        )
        return

    def close(self) -> None:
        """Close the connection with the device.

        :returns:
        :rtype: None
        """
        if self.serial and self.serial.is_open:
            self.serial.close()
        return

    def go_to(
        self,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
        need_to_await: bool = False,
        speed: float = 3000,
    ) -> None:
        """Ask device to move to coordinates (x, y, z). Sends "G1" gcode command to the device.

        :param x: Horizontal coordinate along the chip.
        :type x: float | None = None
        :param y: Horizontal coordinate of the zond perpendicular to the chip.
        :type y: float | None = None
        :param z: Vertical coordinate of the zond above the chip.
        :type z: float | None = None
        :param need_to_await: Flag to block further commands execution until this command is finished.
        :type need_to_await: bool = False
        :param speed: Speed of the travel.
        :type speed: float = 3000

        :returns:
        :rtype: None
        """
        if x is not None and not (self.config.x_min <= x <= self.config.x_max):
            raise ValueError(f"X={x} ∉ [{self.config.x_min}, {self.config.x_max}]")
        if y is not None and not (self.config.y_min <= y <= self.config.y_max):
            raise ValueError(f"Y={y} ∉ [{self.config.y_min}, {self.config.y_max}]")
        if z is not None and not (self.config.z_min <= z <= self.config.z_max):
            raise ValueError(f"Z={z} ∉ [{self.config.z_min}, {self.config.z_max}]")

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
        """Ask device what is the position.
        Sends "M114" gcode command to the device, parses the responce like
        `X:123.00 Y:456.00 Z:78.00` and returns (x, y, z) coordinates.

        :returns: Coordinates.
        :rtype: Tuple[float, float, float]
        """
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

    def home(self, need_to_await: bool = True) -> None:
        """Ask device to perform homing operation.
        Sends "G28 Z", "G28 X" and "G28 Y" gcode command to the device.

        :param need_to_await: Flag to block further commands execution until this command is finished.
        :type need_to_await: bool = True

        :returns:
        :rtype: None
        """
        self.send_command("G28 Z", need_to_await=need_to_await)
        self.send_command("G28 X", need_to_await=need_to_await)
        self.send_command("G28 Y", need_to_await=need_to_await)
        return

    def send_command(self, command: str, need_to_await: bool = True) -> str:
        """Send generic command.

        :param command: Command to send.
        :type command: str
        :param need_to_await: Flag to block further commands execution until this command is finished.
        :type need_to_await: bool = True

        :returns: Responce from the device. Responce is empty if `need_to_await = False`
        :rtype: str
        """
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
        """Clear input and output COM port buffers. Sleep for 0.1s after that.

        :returns:
        :rtype: None
        """
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        sleep(0.1)
        return
