from typing import Dict, Tuple
from dataclasses import dataclass, asdict

import yaml


@dataclass
class ZondCalibrationConfigData:
    x_pixels: float
    y_pixels: float
    x_mm: float
    y_mm: float


class ZondCalibrationConfig:
    def __init__(self, path: str):
        self.path = path
        self.data: ZondCalibrationConfigData = self.open_same_path()
        return

    @staticmethod
    def save(config_path: str, config_data: Dict) -> None:
        with open(config_path, "w") as file:
            yaml.safe_dump(config_data, file)
        return

    @staticmethod
    def open(path: str) -> Dict:
        with open(path, "r") as file:
            return yaml.safe_load(file)

    def save_same_path(self, data: ZondCalibrationConfigData) -> None:
        self.save(self.path, asdict(data))
        return

    def open_same_path(self) -> None:
        data = self.open_and_parse(self.path)
        return data

    @staticmethod
    def open_and_parse(path: str) -> ZondCalibrationConfigData:
        with open(path, "r") as file:
            data = yaml.safe_load(file)

        data = ZondCalibrationConfigData(
            data["x_pixels"],
            data["y_pixels"],
            data["x_mm"],
            data["y_mm"],
        )

        return data

    @property
    def x_pixels(self) -> float:
        return self.data.x_pixels

    @property
    def y_pixels(self) -> float:
        return self.data.y_pixels

    @property
    def x_mm(self) -> float:
        return self.data.x_mm

    @property
    def y_mm(self) -> float:
        return self.data.y_mm

    def calc_current_zond_pixels_position(
        self, y_mm: float, pixels_per_mm: float
    ) -> Tuple[float, float]:

        # Calculate x_pixels from x_pixels_calibrated (nothing to calculate, they are equal)
        x_pixels_calibrated = self.x_pixels
        x_pixels = x_pixels_calibrated

        # Calculate y_pixels from y_pixels_calibrated, y_mm_calibrated and y_mm (linear relation)
        y_pixels_calibrated = self.y_pixels
        y_mm_calibrated = self.y_mm
        y_pixels = -(y_mm - y_mm_calibrated) * pixels_per_mm + y_pixels_calibrated

        return (x_pixels, y_pixels)
