from os import path
import numpy as np
import cv2
from time import sleep

from src.Camera import Camera
from src.GCodeSender import GCodeSender, SomeGCodes, DEVICES
from src.RidgeDetection import RidgeDetection
from src.misc import *


class Apparatus:
    def __init__(self):

        # Chip configuration
        # TODO change hardcoded variables to actual configs
        self.ridge_period = 0.15
        self.ridge_width = 0.1
        self.ridge_length = 2.0
        self.ridge_length_to_period_ratio = self.ridge_length / self.ridge_period
        self.number_of_ridges: int = 62
        self.ridges_sum_length = self.number_of_ridges * self.ridge_period
        self.eutectic_apply_length = 1.0
        self.safe_height_above_ridge = 1.0

        # Connect external devices
        self.gcode_sender = self.connect_gcode_sender()
        self.camera = Camera(4, height=1000)
        self.camera.create_capture()

        self.target_position = self.get_current_position()

        self.image_crop_size = np.array([1000, 1000])
        self.ridge_model_path = path.join(
            "nn-models", "obb-ridge-detection", "best1.pt"
        )
        self.ridge_model = RidgeDetection(self.ridge_model_path)

        self.pixels_per_mm_coeff: float | None = None
        self.first_ridge_center_coordinates_mm: list[float | None] = [None] * 3
        self.last_ridge_center_coordinates_mm: list[float | None] = [None] * 3
        return

    @staticmethod
    def connect_gcode_sender() -> GCodeSender:
        gcode_sender = GCodeSender(DEVICES[0])
        gcode_sender.connect()
        gcode_sender.send_command(
            SomeGCodes.SET_STEPS_PER_UNIT_GCODE, need_to_await=False
        )
        gcode_sender.send_command(
            SomeGCodes.SET_CURRENT_LIMIT_GCODE, need_to_await=False
        )
        gcode_sender.send_command(
            SomeGCodes.SET_MAX_FEEDRATE_GCODE, need_to_await=False
        )
        gcode_sender.send_command(
            SomeGCodes.SET_ACCELERATION_GCODE, need_to_await=False
        )
        gcode_sender.send_command(
            SomeGCodes.SET_MICROSTEPPING_GCODE, need_to_await=False
        )
        gcode_sender.send_command(
            SomeGCodes.SET_BACKLASH_CORRECTION_GCODE, need_to_await=False
        )
        return gcode_sender

    def get_current_position(self) -> tuple[float, float, float]:
        pos = self.gcode_sender.get_pos()
        return pos

    def get_target_position(self) -> list[float]:
        return self.target_position

    def set_target_position(self, values: list[float]) -> None:
        self.target_position = values
        return

    def set_target_position_piecewice(self, coord: str, value: float) -> None:
        if coord.lower() == "x":
            self.target_position[0] = value
        elif coord.lower() == "y":
            self.target_position[1] = value
        elif coord.lower() == "z":
            self.target_position[2] = value
        else:
            raise Exception(f"Unknown coordinate: {coord}")
        return

    def set_terget_reletive_to_current(self, values: list[float | None]) -> None:
        values = [(value if value is not None else 0.0) for value in values]
        new_target_position = [
            self.target_position[i] + values[i]
            for i in range(len(self.target_position))
        ]
        self.set_target_position(new_target_position)
        return

    def move_to_target_position(self, need_to_await=False) -> None:
        if any([aaa is None for aaa in self.target_position]):
            self.set_target_position(self.get_current_position())
        kwargs = dict(zip(["x", "y", "z"], self.target_position))
        self.gcode_sender.go_to(**kwargs, need_to_await=need_to_await)
        return

    def home(self) -> None:
        self.gcode_sender.home()
        self.set_target_position(self.get_current_position())
        return

    def get_camera_frame(self, find_obbs: bool, draw_obbs: bool):
        # Read camera buffer
        ret, frame = self.camera.capture.read()
        if not ret:
            raise Exception("Could not get camera frame.")

        center_x = frame.shape[1] // 2
        center_y = frame.shape[0] // 2

        cropped_frame = frame[
            center_y
            - self.image_crop_size[1] // 2 : center_y
            + self.image_crop_size[1] // 2,
            center_x
            - self.image_crop_size[0] // 2 : center_x
            + self.image_crop_size[0] // 2,
        ]

        # Detect rectangles
        if find_obbs or draw_obbs:
            obbs, confidences = self.ridge_model.run_detection(cropped_frame)
            first_ridge_center, last_ridge_center, ridge_period_in_pixels = (
                self.analyze_obbs(obbs)
            )
        else:
            first_ridge_center, last_ridge_center, ridge_period_in_pixels = (
                None,
                None,
                None,
            )

        if draw_obbs:
            for obb in obbs:
                xs: list[float] = obb[:, 0].tolist()
                ys: list[float] = obb[:, 1].tolist()
                xs.append(xs[0])
                ys.append(ys[0])
                for i in range(len(xs) - 1):
                    cv2.line(
                        img=cropped_frame,
                        pt1=(int(xs[i]), int(ys[i])),
                        pt2=(int(xs[i + 1]), int(ys[i + 1])),
                        color=(255, 0, 0),
                        thickness=2,
                    )

            cv2.line(
                img=cropped_frame,
                pt1=[int(aaa) for aaa in first_ridge_center.tolist()],
                pt2=[int(aaa) for aaa in last_ridge_center.tolist()],
                color=(0, 255, 0),
                thickness=2,
            )

        return (
            cropped_frame,
            first_ridge_center,
            last_ridge_center,
            ridge_period_in_pixels,
        )

    def analyze_obbs(self, obbs) -> tuple[np.ndarray, np.ndarray, float]:
        # Calculate mean rotation angle of each obb
        angles = [RidgeDetection.get_box_angle(obb) for obb in obbs]
        angle_mean = np.mean(angles)

        # Rotate obbs to align with coordinate system
        rotated_obbs = [RidgeDetection.rotate_tensor(obb, -angle_mean) for obb in obbs]

        ridge_short_sides = [
            RidgeDetection.get_box_short_side_points(obb) for obb in rotated_obbs
        ]
        ridge_long_sides = [
            RidgeDetection.get_box_long_side_points(obb) for obb in rotated_obbs
        ]
        ridge_centers_x = [
            RidgeDetection.get_box_center(obb)[0] for obb in rotated_obbs
        ]

        # Calculate distances between ridge centers
        # There can be missing ridges, so there is a chance to see a value equal 2*period or 3*period
        ridge_periods_pixel = [
            abs(ridge_centers_x[i] - ridge_centers_x[i + 1])
            for i in range(len(ridge_centers_x) - 1)
        ]
        ridge_period_mean_pixel = np.median(ridge_periods_pixel)

        ridge_length_pixel = self.ridge_length_to_period_ratio * ridge_period_mean_pixel

        ridge_center_coordinate_mean = np.mean(
            [np.mean([y1, y2]) for x1, y1, x2, y2 in ridge_long_sides]
        )

        first_box = np.array(rotated_obbs[0])
        last_box = np.array(rotated_obbs[-1])

        first_ridge_approx_center = np.mean(first_box, axis=0)
        first_ridge_avg_center = np.array(
            [first_ridge_approx_center[0], ridge_center_coordinate_mean]
        )

        last_ridge_approx_center = np.mean(last_box, axis=0)
        last_ridge_avg_center = np.array(
            [last_ridge_approx_center[0], ridge_center_coordinate_mean]
        )

        # Rotate back to original coordinate system
        first_ridge_avg_center = RidgeDetection.rotate_vector(
            first_ridge_avg_center, angle_mean
        )
        last_ridge_avg_center = RidgeDetection.rotate_vector(
            last_ridge_avg_center, angle_mean
        )

        return first_ridge_avg_center, last_ridge_avg_center, ridge_period_mean_pixel

    def save_first_ridge_center(self) -> None:
        self.first_ridge_center_coordinates_mm = self.get_current_position()
        return

    def save_last_ridge_center(self) -> None:
        self.last_ridge_center_coordinates_mm = self.get_current_position()
        return

    def deduce_last_ridge_position(self) -> None:

        # Save first ridge position right under the zond
        self.save_first_ridge_center()

        # Move to a safe height right above the ridge
        self.set_terget_reletive_to_current([0.0, 0.0, -self.safe_height_above_ridge])
        self.move_to_target_position(need_to_await=True)

        # Move out of the frame
        self.set_terget_reletive_to_current([0.0, -2.0, 0.0])
        self.move_to_target_position(need_to_await=True)

        # Sleep to allow the image to settle
        sleep(2)

        # Get first and last ridges in frame1 coordinates
        _, first_on_frame1, last_on_frame1, period1 = self.get_camera_frame(True, False)
        print(f"{first_on_frame1=}")
        print(f"{last_on_frame1=}")
        print(f"{period1=}")

        # Save pixels per mm if it is not measured
        if self.pixels_per_mm_coeff is None:
            self.pixels_per_mm_coeff = period1 / self.ridge_period

        # Some linear algebra
        vec_fl = last_on_frame1 - first_on_frame1
        n_ridges_in_frame = int(round(np.linalg.norm(vec_fl) / period1))
        vec_one_ridge = vec_fl / n_ridges_in_frame

        # Move to other end
        self.set_terget_reletive_to_current(
            [
                vec_one_ridge[0] * self.number_of_ridges / self.pixels_per_mm_coeff,
                0.0,
                0.0,
            ]
        )
        self.move_to_target_position(need_to_await=True)

        # Sleep to allow the image to settle
        sleep(2)

        # Get last ridge in frame2 coordinates
        _, first_on_frame2, last_on_frame2, period2 = self.get_camera_frame(True, False)
        print(f"{first_on_frame2=}")
        print(f"{last_on_frame2=}")
        print(f"{period2=}")

        # Move back into a frame
        self.set_terget_reletive_to_current([0.0, 2.0, 0.0])
        self.move_to_target_position(need_to_await=True)

        # Calculate correction for zond position (some linear algebra again)
        vec_FL = last_on_frame2 - first_on_frame1

        # # Move with the correction
        self.set_terget_reletive_to_current(
            [
                vec_FL[0] / self.pixels_per_mm_coeff,
                -vec_FL[1] / self.pixels_per_mm_coeff,
                0.0,
            ]
        )
        self.move_to_target_position(need_to_await=True)

        # Move down from the safe height on the ridge
        self.set_terget_reletive_to_current([0.0, 0.0, self.safe_height_above_ridge])
        self.move_to_target_position(need_to_await=True)

        # Save last ridge position right under the zond
        self.save_last_ridge_center()
        return

    def is_ridge_index_valid(self, nth: int) -> bool:
        return not (nth < 1 or nth > self.number_of_ridges)
    
    def get_nth_ridge_center(self, nth: int) -> np.ndarray:
        if not self.is_ridge_index_valid(nth):
            raise Exception(f"Incorrent index: {nth} ∉ [1, {self.number_of_ridges}]")
        
        first = np.array(list(self.first_ridge_center_coordinates_mm))
        last = np.array(list(self.last_ridge_center_coordinates_mm))

        number_of_ridges = int(round(np.linalg.norm(last - first) / self.ridge_period))

        # Ridge in question
        ridge = first + (last - first) * (nth - 1) / number_of_ridges
        return ridge

    def get_perp_unit_vector(self) -> np.ndarray:
        first = np.array(self.first_ridge_center_coordinates_mm)
        last = np.array(self.last_ridge_center_coordinates_mm)
        vec = last - first
        unit_vector = (
            np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
            @ vec
            / np.linalg.norm(vec)
        )
        return unit_vector

    def run(self) -> None:
        if any([X is None for X in self.first_ridge_center_coordinates_mm]):
            raise Exception("First ridge center is not set")
        if any([X is None for X in self.last_ridge_center_coordinates_mm]):
            raise Exception("Last ridge center is not set")

        perp_unit_vector = self.get_perp_unit_vector()

        for i in range(1, 10, 2):
            center = self.get_nth_ridge_center(i)

            # Move to a safe height right above the ridge
            self.set_target_position(center.tolist())
            self.set_terget_reletive_to_current(
                [0.0, 0.0, -self.safe_height_above_ridge]
            )
            self.move_to_target_position(need_to_await=True)

            # Move to the ridge
            self.set_target_position(center.tolist())
            self.move_to_target_position(need_to_await=True)

            # Move along the ridge back and forth to apply eutectic
            self.set_target_position(
                (center + perp_unit_vector * self.eutectic_apply_length / 2).tolist()
            )
            self.move_to_target_position(need_to_await=True)
            self.set_target_position(
                (center - perp_unit_vector * self.eutectic_apply_length / 2).tolist()
            )
            self.move_to_target_position(need_to_await=True)

            # Move back to the center of the ridge
            self.set_target_position(center.tolist())
            self.move_to_target_position(need_to_await=True)

            # Move to a safe height right above the ridge
            self.set_target_position(center.tolist())
            self.set_terget_reletive_to_current(
                [0.0, 0.0, -self.safe_height_above_ridge]
            )
            self.move_to_target_position(need_to_await=True)
        return

    def set_target_to_nth_ridge_center(self, nth: int) -> None:
        if not self.is_ridge_index_valid(nth):
            raise Exception(f"Incorrent index: {nth} ∉ [1, {self.number_of_ridges}]")

        ridge = self.get_nth_ridge_center(nth)
        self.set_target_position(ridge.tolist())
        return

    def go_to_nth_ridge_center(self, nth: int) -> None:
        if not self.is_ridge_index_valid(nth):
            raise Exception(f"Incorrent index: {nth} ∉ [1, {self.number_of_ridges}]")

        # Move to safe height above ridge
        self.set_target_to_nth_ridge_center(nth)
        self.set_terget_reletive_to_current([0.0, 0.0, -self.safe_height_above_ridge])
        self.move_to_target_position()

        # Move on the ridge
        self.set_target_to_nth_ridge_center(nth)
        self.move_to_target_position()
        return

    def measure_basklash(self, nth: int) -> None:
        if not self.is_ridge_index_valid(nth):
            raise Exception(f"Incorrent index: {nth} ∉ [1, {self.number_of_ridges}]")

        N_travels = 50
        N_frame_measurements = 5

        measurements_negative = []
        measurements_positive = []
        for i in range(N_travels):
            # Move from the negative direction
            self.set_target_to_nth_ridge_center(nth)
            self.set_terget_reletive_to_current([-0.2, 0.0, 0.0])
            self.set_terget_reletive_to_current([0.0, -2.0, 0.0])
            self.move_to_target_position(need_to_await=True)
            self.set_target_to_nth_ridge_center(nth)
            self.set_terget_reletive_to_current([0.0, -2.0, 0.0])
            self.move_to_target_position(need_to_await=True)

            # Wait for frame to settle
            sleep(1)

            # Measure
            for j in range(N_frame_measurements):
                try:
                    _, first, last, period = self.get_camera_frame(True, False)
                    measurement = []
                    measurement.append(first.tolist())
                    measurement.append(last.tolist())
                    measurement.append(float(period))
                    measurements_negative.append(measurement)
                except:
                    pass

            # Move from the positive direction
            self.set_target_to_nth_ridge_center(nth)
            self.set_terget_reletive_to_current([0.2, 0.0, 0.0])
            self.set_terget_reletive_to_current([0.0, -2.0, 0.0])
            self.move_to_target_position(need_to_await=True)
            self.set_target_to_nth_ridge_center(nth)
            self.set_terget_reletive_to_current([0.0, -2.0, 0.0])
            self.move_to_target_position(need_to_await=True)

            # Wait for frame to settle
            sleep(1)

            # Measure
            for j in range(N_frame_measurements):
                try:
                    _, first, last, period = self.get_camera_frame(True, False)
                    measurement = []
                    measurement.append(first.tolist())
                    measurement.append(last.tolist())
                    measurement.append(float(period))
                    measurements_positive.append(measurement)
                except:
                    pass

        print(f"{measurements_negative=}")
        print()
        print(f"{measurements_positive=}")

        return (measurements_negative, measurements_positive)

    def close(self) -> None:
        self.gcode_sender.close()
        self.camera.close()
        return
