from typing import List, Tuple, Dict

import torch
import numpy as np
from ultralytics import YOLO


class RidgeDetection:
    def __init__(self, model_path: str) -> None:
        """Constructor for RidgeDetection class.

        :param model_path: Reletive path to pretrained NN model for ridge detection.
        :type model_path: str

        :returns:
        :rtype: None
        """
        self.model_path: str = model_path
        self.model = YOLO(self.model_path)
        return

    @staticmethod
    def conv_box_to_xyxyxyxy(box: torch.Tensor) -> List[int]:
        """Convert torch.Tensor OBB object to a list of vertices.

        :param box: OBB object in image coordinates.
        :type box: torch.Tensor

        :returns: List of vertices in image coordinates in `x1, y1, x2, y2, x3, y3, x4, y4` format.
        :rtype: List[int]
        """
        return torch.flatten(box).tolist()

    @staticmethod
    def conv_xyxyxyxy_to_box(
        x1: int, y1: int, x2: int, y2: int, x3: int, y3: int, x4: int, y4: int
    ) -> torch.Tensor:
        """Convert a list of vertices from `x1, y1, x2, y2, x3, y3, x4, y4` format to torch.Tensor OBB object.

        :param x1: X coordinate if the first vortex.
        :type x1: int
        :param y1: Y coordinate if the first vortex.
        :type y1: int
        :param x2: X coordinate if the second vortex.
        :type x2: int
        :param y2: Y coordinate if the second vortex.
        :type y2: int
        :param x3: X coordinate if the third vortex.
        :type x3: int
        :param y3: Y coordinate if the third vortex.
        :type y3: int
        :param x4: X coordinate if the forth vortex.
        :type x4: int
        :param y4: Y coordinate if the forth vortex.
        :type y4: int

        :returns: OBB object in image coordinates.
        :rtype: torch.Tensor
        """
        return torch.tensor(np.array([x1, y1, x2, y2, x3, y3, x4, y4]).reshape((4, 2)))

    @staticmethod
    def get_box_long_side_points(box: torch.Tensor) -> Tuple[int, int, int, int]:
        """Get a list of coordinates of such two vertices that form a long side of the torch.Tensor OBB object.

        :param box: OBB object in image coordinates.
        :type box: torch.Tensor

        :returns: Tuple of coordinates in `(x1, y1, x2, y2)` format.
        :rtype: Tuple[int, int, int, int]
        """
        x1, y1, x2, y2, x3, y3, x4, y4 = RidgeDetection.conv_box_to_xyxyxyxy(box)
        distances: Dict[Tuple[int, int, int, int], float] = {}
        distances[(x1, y1, x2, y2)] = np.hypot(x2 - x1, y2 - y1)
        distances[(x2, y2, x3, y3)] = np.hypot(x3 - x2, y3 - y2)
        return max(distances, key=distances.get)

    @staticmethod
    def get_box_short_side_points(box: torch.Tensor) -> Tuple[int, int, int, int]:
        """Get a list of coordinates of such two vertices that form a short side of the torch.Tensor OBB object.

        :param box: OBB object in image coordinates.
        :type box: torch.Tensor

        :returns: Tuple of coordinates in `(x1, y1, x2, y2)` format.
        :rtype: Tuple[int, int, int, int]
        """
        x1, y1, x2, y2, x3, y3, x4, y4 = RidgeDetection.conv_box_to_xyxyxyxy(box)
        distances: Dict[Tuple[int, int, int, int], float] = {}
        distances[(x1, y1, x2, y2)] = np.hypot(x2 - x1, y2 - y1)
        distances[(x2, y2, x3, y3)] = np.hypot(x3 - x2, y3 - y2)
        return min(distances, key=distances.get)

    @staticmethod
    def get_box_angle(box: torch.Tensor) -> float:
        """Get an orientation of the torch.Tensor OBB object.
        Value `alpha = 0` correcponds to the long side of the torch.Tensor OBB object oriented vertically on the image.

        :param box: OBB object in image coordinates.
        :type box: torch.Tensor

        :returns: Angle of the OBB object in radians.
        :rtype: float
        """
        x1, y1, x2, y2 = RidgeDetection.get_box_long_side_points(box)
        alpha = np.arctan2(x1 - x2, y1 - y2)
        return alpha

    @staticmethod
    def get_box_center(box: torch.Tensor) -> Tuple[float, float]:
        """Get the center of the torch.Tensor OBB object.

        :param box: OBB object in image coordinates.
        :type box: torch.Tensor

        :returns: Coordinates of the center of the OBB object in image coordinates.
        :rtype: Tuple[float, float]
        """
        xs = [box[i][0] for i in range(len(box))]
        ys = [box[i][1] for i in range(len(box))]
        center_x = np.mean(xs)
        center_y = np.mean(ys)
        return (center_x, center_y)

    @staticmethod
    def filter_invalid_by_centers(
        box_i: torch.Tensor,
        conf_i: float,
        box_j: torch.Tensor,
        conf_j: float,
        x_threshold: float,
        y_threshold: float,
    ) -> Tuple[bool, bool]:
        """Filter two torch.Tensor OBB objects by their centers.

        For two provided OBB objects their center coordinates are calculated.
        If the distance between their centers in X direction is less then `x_threshold` or
        if the distance between their centers in Y direction is less then `y_threshold`,
        then the OBB object with lower confidence score is filtered out.

        :param box_i: First OBB object in image coordinates.
        :type box_i: torch.Tensor
        :param conf_i: Confidence of the `box_i`.
        :type conf_i: float
        :param box_j: Second OBB object in image coordinates.
        :type box_j: torch.Tensor
        :param conf_j: Confidence of the `box_j`.
        :type conf_j: float

        :returns: Two boolean flags that correspond to filtering out `box_i` or `box_j` or none of them.
        :rtype: Tuple[bool, bool]
        """
        xs_i = [box_i[i][0] for i in range(len(box_i))]
        ys_i = [box_i[i][1] for i in range(len(box_i))]
        center_x_i = np.mean(xs_i)
        center_y_i = np.mean(ys_i)
        xs_j = [box_j[i][0] for i in range(len(box_j))]
        ys_j = [box_j[i][1] for i in range(len(box_j))]
        center_x_j = np.mean(xs_j)
        center_y_j = np.mean(ys_j)

        if (
            abs(center_x_i - center_x_j) < x_threshold
            or abs(center_y_i - center_y_j) < y_threshold
        ):
            if conf_i > conf_j:
                return (False, True)
            else:
                return (True, False)
        return (False, False)

    @staticmethod
    def rotate_vector(vec: np.ndarray, alpha_rad: float) -> np.ndarray:
        """Rotate a numpy.ndarray vector.

        :param vec: Numpy 2D vector.
        :type vec: np.ndarray
        :param alpha_rad: Angle to rotate by in radians.
        :type alpha_rad: float

        :returns: Rotated numpy 2D vector.
        :rtype: np.ndarray
        """
        rot_matrix = np.array(
            [
                [np.cos(alpha_rad), -np.sin(alpha_rad)],
                [np.sin(alpha_rad), np.cos(alpha_rad)],
            ]
        )
        rotated_vec = np.dot(vec, rot_matrix)
        return rotated_vec

    @staticmethod
    def rotate_tensor(tensor: torch.Tensor, alpha_rad: float) -> torch.Tensor:
        """Rotate a torch.Tensor vector.

        :param tensor: Tensor vector.
        :type tensor: torch.Tensor
        :param alpha_rad: Angle to rotate by in radians.
        :type alpha_rad: float

        :returns: Rotated tensor vector.
        :rtype: torch.Tensor
        """
        return torch.from_numpy(RidgeDetection.rotate_vector(tensor, alpha_rad))

    @staticmethod
    def sort_boxes(
        boxes: List[torch.Tensor], confidences: List[float]
    ) -> Tuple[List[torch.Tensor], List[float]]:
        """Sort a list of torch.Tensor OBB objects in ascending order of their center X coordinate.

        :param boxes: List of torch.Tensor OBB objects to sort.
        :type boxes: List[torch.Tensor]

        :returns: Sorted list of torch.Tensor OBB objects.
        :rtype: List[torch.Tensor]
        """
        boxes_and_confidences_sorted = sorted(
            zip(boxes, confidences),
            key=lambda box_conf: RidgeDetection.get_box_center(box_conf[0])[0],
        )
        boxes_sorted = [box_conf[0] for box_conf in boxes_and_confidences_sorted]
        confidences_sorted = [box_conf[1] for box_conf in boxes_and_confidences_sorted]
        return boxes_sorted, confidences_sorted

    def run_detection(self, image):
        """Detect, filter invalid and sort torch.Tensor OBB objects on an image.

        :param image: Image to detect OBB objects on.
        :type image:

        :returns: Sorted list of torch.Tensor OBB objects and list of their confidences respectively.
        :rtype: Tuple[List[torch.Tensor], List[float]]
        """
        results = self.model.predict(source=image)

        obb_boxes: List[torch.Tensor] = []
        confidences: List[float] = []
        for result in results:
            if result.obb is not None:
                obb_boxes = result.obb.xyxyxyxy
                confidences = result.obb.conf
            else:
                continue

        obb_boxes_invalid_indexes: List[torch.Tensor] = []
        for i, [box_i, conf_i] in enumerate(zip(obb_boxes, confidences)):
            for j in range(i + 1, len(obb_boxes)):
                box_j, conf_j = obb_boxes[j], confidences[j]
                invalid_i, invalid_j = self.filter_invalid_by_centers(
                    box_i, conf_i, box_j, conf_j, 50.0, 0.0
                )
                if invalid_i:
                    obb_boxes_invalid_indexes.append(i)
                if invalid_j:
                    obb_boxes_invalid_indexes.append(j)

        obb_boxes_valid: List[torch.Tensor] = []
        confidences_valid: List[float] = []
        for i, [box, conf] in enumerate(zip(obb_boxes, confidences)):
            if i not in obb_boxes_invalid_indexes:
                obb_boxes_valid.append(box)
                confidences_valid.append(conf)

        sorted_obb_boxes, sorted_confidences = RidgeDetection.sort_boxes(
            obb_boxes_valid, confidences_valid
        )

        return (sorted_obb_boxes, sorted_confidences)
