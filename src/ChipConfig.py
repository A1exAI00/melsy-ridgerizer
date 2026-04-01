from typing import Dict
from dataclasses import dataclass

import yaml


@dataclass
class ChipConfigData:
    ridge_period: float
    ridge_width: float
    ridge_length: float
    number_of_ridges_max: int
    eutectic_apply_length: float
    safe_z_height_above_ridge: float


class ChipConfig:
    def __init__(self, path: str) -> None:
        self.path = path
        self.data: ChipConfigData = self.open_same_path()
        return

    @staticmethod
    def open(path: str) -> Dict:
        with open(path, "r") as file:
            return yaml.safe_load(file)

    @staticmethod
    def save(path: str, config_data: Dict) -> None:
        with open(path, "w") as file:
            yaml.safe_dump(config_data, file)
        return

    @staticmethod
    def open_and_parse(path: str) -> ChipConfigData:
        with open(path, "r") as file:
            data = yaml.safe_load(file)

        data = ChipConfigData(
            data["ridge_period"],
            data["ridge_width"],
            data["ridge_length"],
            data["number_of_ridges_max"],
            data["eutectic_apply_length"],
            data["safe_z_height_above_ridge"],
        )

        return data

    def open_same_path(self) -> None:
        data = self.open_and_parse(self.path)
        return data

    @property
    def ridge_period(self) -> float:
        return self.data.ridge_period
    
    @property
    def ridge_width(self) -> float:
        return self.data.ridge_width
    
    @property
    def ridge_length(self) -> float:
        return self.data.ridge_length
    
    @property
    def number_of_ridges_max(self) -> int:
        return self.data.number_of_ridges_max
    
    @property
    def eutectic_apply_length(self) -> float:
        return self.data.eutectic_apply_length
    
    @property
    def safe_z_height_above_ridge(self) -> float:
        return self.data.safe_z_height_above_ridge
    
    @property
    def ridge_length_to_period_ratio(self) -> float:
        return self.ridge_length / self.ridge_period
    
    @property
    def ridges_max_sum_length(self) -> float:
        return self.ridge_period * self.number_of_ridges_max