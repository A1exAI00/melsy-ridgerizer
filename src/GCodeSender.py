import serial
import serial.tools.list_ports
import time

from dataclasses import dataclass
from typing import Tuple


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
    SET_STEPS_PER_UNIT_GCODE: str = "M92 X1600 Y1600 Z1600"
    SET_CURRENT_LIMIT_GCODE: str = "M906 X700 Y700"
    SET_MAX_FEEDRATE_GCODE: str = "M203 X1 Y1 Z1"
    SET_ACCELERATION_GCODE: str = "M204 T10"
    SET_MICROSTEPPING_GCODE: str = "M350 X8 Y8 Z32"
    HOME_GCODE: str = "G28"
    HOME_X_GCODE: str = "G28 X"
    HOME_Y_GCODE: str = "G28 Y"
    HOME_Z_GCODE: str = "G28 Z"


class GCodeSenter:
    def __init__(self, config: DeviceConfig, verbose: int = 1) -> None:
        self.config = config
        self.verbose = verbose
        self.serial = None
        self.position = {"X": 0, "Y": 0, "Z": 0}
        return

    def _log(self, message: str, level: int = 1) -> None:
        if self.verbose >= level:
            print(message)
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
            self._log(f"Connected to port {port}", level=1)
            return True
        except Exception as e:
            self._log(f"Connection error: {e}", level=0)
            raise
        return

    def close(self) -> None:
        if self.serial and self.serial.is_open:
            self.serial.close()
            self._log("Connection closed", level=2)
        return

    def moveto(
        self,
        X: float = None,
        Y: float = None,
        Z: float = None,
        need_to_await=True,
        speed: float = 3000,
    ) -> None:
        if X is not None and not (self.config.x_min <= X <= self.config.x_max):
            raise ValueError(
                f"X={X} out of borders [{self.config.x_min}, {self.config.x_max}]"
            )
        if Y is not None and not (self.config.y_min <= Y <= self.config.y_max):
            raise ValueError(
                f"Y={Y} out of borders [{self.config.y_min}, {self.config.y_max}]"
            )
        if Z is not None and not (self.config.z_min <= Z <= self.config.z_max):
            raise ValueError(
                f"Z={Z} out of borders [{self.config.z_min}, {self.config.z_max}]"
            )

        gcode = "G1"
        if X is not None:
            gcode += f" X{X}"
        if Y is not None:
            gcode += f" Y{Y}"
        if Z is not None:
            gcode += f" Z{Z}"
        gcode += f" F{speed}"

        self.send_command(gcode, need_to_await)
        self._log(f"Go to: X={X}, Y={Y}, Z={Z}", level=2)
        return

    def getpos(self) -> Tuple[float, float, float]:
        """Получить текущую позицию (парсинг из M114)."""
        response = self.send_command("M114", need_to_await=True)
        # Парсим ответ вида "X:123.00 Y:456.00 Z:78.00"
        for line in response.split("\n"):
            if line.startswith("X:"):
                parts = line.split()
                self.position["X"] = float(parts[0][2:])
                self.position["Y"] = float(parts[1][2:])
                self.position["Z"] = float(parts[2][2:])

        return (self.position["X"], self.position["Y"], self.position["Z"])

    def home(
        self,
        home_x: bool = True,
        home_y: bool = True,
        home_z: bool = True,
        need_to_await=True,
    ) -> None:
        """Калибровка осей (G28)."""
        if all((home_x, home_y, home_z)):
            self.send_command("G28", need_to_await=need_to_await)
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
        """Отправить G-код и дождаться ответа (если wait=True)."""
        if not self.serial or not self.serial.is_open:
            raise Exception("Device is not connected")

        if need_to_await:
            self.clear_buffer()
            time.sleep(0.01)

        self.serial.write(f"{command}\n".encode())
        if not need_to_await:
            return ""

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

    def clear_buffer(self) -> None:
        line = self.serial.readline().decode()
        while line:
            line = self.serial.readline().decode()
        return

    def print_buffer(self) -> None:
        line = self.serial.readline().decode()
        while line:
            print(line)
            line = self.serial.readline().decode()
        return

    def _wait_for_ok(self, timeout=5) -> None:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.serial.in_waiting:
                line = self.serial.readline().decode().strip()
                if "Marlin" in line or "ok" in line:
                    return True
        raise Exception("Device did not respond")
        return
