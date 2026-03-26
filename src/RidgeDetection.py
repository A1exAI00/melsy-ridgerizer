from ultralytics import YOLO
import torch
import numpy as np

class RidgeDetection:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.model = YOLO(self.model_path)
        return

    @staticmethod
    def conv_box_to_xyxyxyxy(box):
        return torch.flatten(box).tolist()

    @staticmethod
    def conv_xyxyxyxy_to_box(x1, y1, x2, y2, x3, y3, x4, y4):
        return torch.tensor(np.array([x1, y1, x2, y2, x3, y3, x4, y4]).reshape((4, 2)))

    @staticmethod
    def get_box_long_side_points(box):
        x1, y1, x2, y2, x3, y3, x4, y4 = RidgeDetection.conv_box_to_xyxyxyxy(box)
        distances = {}
        distances[(x1, y1, x2, y2)] = np.hypot(x2 - x1, y2 - y1)
        distances[(x2, y2, x3, y3)] = np.hypot(x3 - x2, y3 - y2)
        return max(distances, key=distances.get)

    @staticmethod
    def get_box_angle(box):
        x1, y1, x2, y2 = RidgeDetection.get_box_long_side_points(box)
        alpha = np.arctan2(x1 - x2, y1 - y2)
        return alpha

    @staticmethod
    def get_box_center(box):
        xs = [box[i][0] for i in range(len(box))]
        ys = [box[i][1] for i in range(len(box))]
        center_x = np.mean(xs)
        center_y = np.mean(ys)
        return (center_x, center_y)

    @staticmethod
    def get_box_short_side_points(box):
        x1, y1, x2, y2, x3, y3, x4, y4 = RidgeDetection.conv_box_to_xyxyxyxy(box)
        distances = {}
        distances[(x1, y1, x2, y2)] = np.hypot(x2 - x1, y2 - y1)
        distances[(x2, y2, x3, y3)] = np.hypot(x3 - x2, y3 - y2)
        return min(distances, key=distances.get)

    @staticmethod
    def filter_invalid_by_centers(
        box_i, conf_i, box_j, conf_j, x_threshold, y_threshold
    ):
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
    def rotate_vector(vec, alpha_rad):
        rot_matrix = np.array(
            [
                [np.cos(alpha_rad), -np.sin(alpha_rad)],
                [np.sin(alpha_rad), np.cos(alpha_rad)],
            ]
        )
        rotated_vec = np.dot(vec, rot_matrix)
        return rotated_vec

    @staticmethod
    def rotate_tensor(vec, alpha_rad):
        return torch.from_numpy(RidgeDetection.rotate_vector(vec, alpha_rad))

    @staticmethod
    def sort_boxes(boxes, confidences):
        boxes_and_confidences_sorted = sorted(
            zip(boxes, confidences),
            key=lambda box_conf: RidgeDetection.get_box_center(box_conf[0])[0],
        )
        boxes_sorted = [box_conf[0] for box_conf in boxes_and_confidences_sorted]
        confidences_sorted = [box_conf[1] for box_conf in boxes_and_confidences_sorted]
        return boxes_sorted, confidences_sorted

    def run_detection(self, image):
        results = self.model.predict(source=image)

        obb_boxes = []
        confidences = []
        for result in results:
            if result.obb is not None:
                obb_boxes = result.obb.xyxyxyxy
                confidences = result.obb.conf
            else:
                continue

        obb_boxes_invalid_indexes = []
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

        obb_boxes_valid = []
        confidences_valid = []
        for i, [box, conf] in enumerate(zip(obb_boxes, confidences)):
            if i not in obb_boxes_invalid_indexes:
                obb_boxes_valid.append(box)
                confidences_valid.append(conf)

        return RidgeDetection.sort_boxes(obb_boxes_valid, confidences_valid)