from os import getcwd, path, listdir
import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import cv2
from ultralytics import YOLO

from src.GCodeSender import (
    GCodeSenter,
    DEVICES,
    SomeGCodes,
)
from src.Camera import Camera


class AxisControlWidget(QWidget):
    def __init__(self, axis_name: str, gcode_sender: GCodeSenter):
        super().__init__()
        self.axis_name = axis_name.upper()
        self.gcode_sender = gcode_sender
        self.target_pos = 0.0

        layout = QHBoxLayout()

        layout.addWidget(QLabel(axis_name))

        self.target_edit = QLineEdit("0.00")
        self.target_edit.setFixedWidth(80)
        self.target_edit.returnPressed.connect(self.move_to_target)
        layout.addWidget(self.target_edit)

        self.minus_btn = QPushButton("-")
        self.minus_btn.setFixedWidth(40)
        self.minus_btn.clicked.connect(self.move_minus)
        layout.addWidget(self.minus_btn)

        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedWidth(40)
        self.plus_btn.clicked.connect(self.move_plus)
        layout.addWidget(self.plus_btn)

        self.step_edit = QLineEdit("1.0")
        self.step_edit.setFixedWidth(60)
        layout.addWidget(self.step_edit)

        self.setLayout(layout)

    def move_minus(self):
        try:
            current_pos = self.gcode_sender.get_pos()[
                {"X": 0, "Y": 1, "Z": 2}[self.axis_name]
            ]
            step = float(self.step_edit.text())
            self.target_pos = current_pos - step
            self.target_edit.setText(f"{self.target_pos:.2f}")
            self.move_to_target()
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid step value")

    def move_plus(self):
        try:
            current_pos = self.gcode_sender.get_pos()[
                {"X": 0, "Y": 1, "Z": 2}[self.axis_name]
            ]
            step = float(self.step_edit.text())
            self.target_pos = current_pos + step
            self.target_edit.setText(f"{self.target_pos:.2f}")
            self.move_to_target()
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid step value")

    def move_to_target(self):
        try:
            self.target_pos = float(self.target_edit.text())
            kwargs = {self.axis_name.lower(): self.target_pos}
            self.gcode_sender.go_to(**kwargs, need_to_await=True)
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        directory_images = path.join("datasets", "data_square_size", "images", "val")
        filename_image = listdir(directory_images)[22]
        image_path = path.join(directory_images, filename_image)

        model = YOLO(trained_model_path)
        results = model(
            image_path,
            # iou=1.0,
            # conf=0.2,
        )
        self.setWindowTitle("Jog panel")
        self.setGeometry(100, 100, 300, 300)

        self.gcode_sender = GCodeSenter(DEVICES[0])

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        splitter = QSplitter(Qt.Horizontal)

        controls_widget = QWidget()
        controls_layout = QVBoxLayout()

        self.widget_x = AxisControlWidget("X", self.gcode_sender)
        controls_layout.addWidget(self.widget_x)

        self.widget_y = AxisControlWidget("Y", self.gcode_sender)
        controls_layout.addWidget(self.widget_y)

        self.widget_z = AxisControlWidget("Z", self.gcode_sender)
        controls_layout.addWidget(self.widget_z)

        btn_layout = QHBoxLayout()

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_device)
        btn_layout.addWidget(self.connect_btn)

        self.home_btn = QPushButton("Home All")
        self.home_btn.clicked.connect(self.home_all)
        self.home_btn.setEnabled(False)
        btn_layout.addWidget(self.home_btn)

        self.refresh_btn = QPushButton("Refresh Positions")
        self.refresh_btn.clicked.connect(self.refresh_positions)
        self.refresh_btn.setEnabled(False)
        btn_layout.addWidget(self.refresh_btn)

        btn_layout.addStretch()
        controls_layout.addLayout(btn_layout)

        controls_widget.setLayout(controls_layout)

        positions_layout_1 = QHBoxLayout()
        self.position_1 = QPushButton("Eu position")
        self.position_1.clicked.connect(self.move_to_pos_1)
        self.position_1_x = QLineEdit("0.00")
        self.position_1_x.setFixedWidth(80)
        self.position_1_y = QLineEdit("0.00")
        self.position_1_y.setFixedWidth(80)
        self.position_1_z = QLineEdit("0.00")
        self.position_1_z.setFixedWidth(80)
        positions_layout_1.addWidget(self.position_1)
        positions_layout_1.addWidget(self.position_1_x)
        positions_layout_1.addWidget(self.position_1_y)
        positions_layout_1.addWidget(self.position_1_z)

        positions_layout_2 = QHBoxLayout()
        self.position_2 = QPushButton("Safe position")
        self.position_2.clicked.connect(self.move_to_pos_2)
        self.position_2_x = QLineEdit("0.00")
        self.position_2_x.setFixedWidth(80)
        self.position_2_y = QLineEdit("0.00")
        self.position_2_y.setFixedWidth(80)
        self.position_2_z = QLineEdit("0.00")
        self.position_2_z.setFixedWidth(80)
        positions_layout_2.addWidget(self.position_2)
        positions_layout_2.addWidget(self.position_2_x)
        positions_layout_2.addWidget(self.position_2_y)
        positions_layout_2.addWidget(self.position_2_z)

        positions_layout_3 = QHBoxLayout()
        self.position_3 = QPushButton("Safe height")
        self.position_3.clicked.connect(self.move_to_pos_3)
        self.position_3_x = QLineEdit("0.00")
        self.position_3_x.setFixedWidth(80)
        self.position_3_x.setEnabled(False)
        self.position_3_y = QLineEdit("0.00")
        self.position_3_y.setFixedWidth(80)
        self.position_3_y.setEnabled(False)
        self.position_3_z = QLineEdit("0.00")
        self.position_3_z.setFixedWidth(80)
        positions_layout_3.addWidget(self.position_3)
        positions_layout_3.addWidget(self.position_3_x)
        positions_layout_3.addWidget(self.position_3_y)
        positions_layout_3.addWidget(self.position_3_z)

        controls_layout.addLayout(positions_layout_1)
        controls_layout.addLayout(positions_layout_2)
        controls_layout.addLayout(positions_layout_3)

        save_open_positions_layout = QHBoxLayout()
        self.save_positons = QPushButton("Save positions")
        self.save_positons.clicked.connect(self.save_positions)
        self.open_positons = QPushButton("Open positions")
        self.open_positons.clicked.connect(self.open_positions)
        save_open_positions_layout.addWidget(self.save_positons)
        save_open_positions_layout.addWidget(self.open_positons)

        controls_layout.addLayout(save_open_positions_layout)

        apply_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply)
        self.move_next_btn = QPushButton("Next")
        self.move_next_btn.clicked.connect(self.move_next)
        self.move_prev_btn = QPushButton("Prev")
        self.move_prev_btn.clicked.connect(self.move_prev)
        apply_layout.addWidget(self.apply_btn)
        apply_layout.addWidget(self.move_next_btn)
        apply_layout.addWidget(self.move_prev_btn)

        controls_layout.addLayout(apply_layout)
        controls_layout.addStretch()

        camera_widget = QWidget()
        camera_layout = QVBoxLayout()
        camera_widget.setLayout(camera_layout)

        self.camera_feed = QLabel("Camera")
        self.camera_feed.setAlignment(Qt.AlignCenter)
        camera_layout.addWidget(self.camera_feed)

        self.camera = Camera(4, width=1000, height=1000)
        self.camera.create_capture()

        self.camera_timer = QTimer()
        self.camera_timer.timeout.connect(self.update_camera)
        self.camera_timer.start(30)

        splitter.addWidget(controls_widget)
        splitter.addWidget(camera_widget)

        main_layout.addWidget(splitter)

    def connect_device(self):
        try:
            self.gcode_sender.connect()
            self.gcode_sender.send_command(
                SomeGCodes.SET_STEPS_PER_UNIT_GCODE, need_to_await=False
            )
            self.gcode_sender.send_command(
                SomeGCodes.SET_CURRENT_LIMIT_GCODE, need_to_await=False
            )
            self.gcode_sender.send_command(
                SomeGCodes.SET_MAX_FEEDRATE_GCODE, need_to_await=False
            )
            self.gcode_sender.send_command(
                SomeGCodes.SET_ACCELERATION_GCODE, need_to_await=False
            )
            self.gcode_sender.send_command(
                SomeGCodes.SET_MICROSTEPPING_GCODE, need_to_await=False
            )

            self.connect_btn.setEnabled(False)
            self.home_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)

            QMessageBox.information(self, "Success", "Device connected successfully")
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))

    def home_all(self):
        self.gcode_sender.home()
        self.refresh_positions()
        return

    def refresh_positions(self):
        x, y, z = self.gcode_sender.get_pos()
        self.widget_x.target_edit.setText(f"{x:.2f}")
        self.widget_y.target_edit.setText(f"{y:.2f}")
        self.widget_z.target_edit.setText(f"{z:.2f}")
        return

    def closeEvent(self, event):
        self.gcode_sender.close()
        event.accept()
        return

    def move_to_pos_1(self):
        x = float(self.position_1_x.text())
        y = float(self.position_1_y.text())
        z = float(self.position_1_z.text())

        self.widget_x.target_edit.setText(f"{x:.2f}")
        self.widget_y.target_edit.setText(f"{y:.2f}")
        self.widget_z.target_edit.setText(f"{z:.2f}")

        self.widget_x.move_to_target()
        self.widget_y.move_to_target()
        self.widget_z.move_to_target()
        return

    def move_to_pos_2(self):
        x = float(self.position_2_x.text())
        y = float(self.position_2_y.text())
        z = float(self.position_2_z.text())

        self.widget_x.target_edit.setText(f"{x:.2f}")
        self.widget_y.target_edit.setText(f"{y:.2f}")
        self.widget_z.target_edit.setText(f"{z:.2f}")

        self.widget_z.move_to_target()
        self.widget_x.move_to_target()
        self.widget_y.move_to_target()
        return

    def move_to_pos_3(self):
        z = float(self.position_3_z.text())

        self.widget_z.target_edit.setText(f"{z:.2f}")

        self.widget_z.move_to_target()
        return

    def apply(self):
        x, y, z = self.gcode_sender.get_pos()
        self.widget_y.target_edit.setText(f"{y+1:.2f}")
        self.widget_y.move_to_target()
        self.widget_y.target_edit.setText(f"{y:.2f}")
        self.widget_y.move_to_target()
        return

    def move_next(self):
        x, y, z = self.gcode_sender.get_pos()
        self.widget_z.target_edit.setText(f"{z-0.5:.2f}")
        self.widget_z.move_to_target()
        self.widget_x.target_edit.setText(f"{x+0.15:.2f}")
        self.widget_x.move_to_target()
        self.widget_z.target_edit.setText(f"{z:.2f}")
        self.widget_z.move_to_target()
        return

    def move_prev(self):
        x, y, z = self.gcode_sender.get_pos()
        self.widget_z.target_edit.setText(f"{z-0.5:.2f}")
        self.widget_z.move_to_target()
        self.widget_x.target_edit.setText(f"{x-0.15:.2f}")
        self.widget_x.move_to_target()
        self.widget_z.target_edit.setText(f"{z:.2f}")
        self.widget_z.move_to_target()
        return

    def save_positions(self):
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Positions", getcwd(), "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            if not file_path.endswith(".txt"):
                file_path += ".txt"

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"{self.position_1_x.text()}\n")
                    f.write(f"{self.position_1_y.text()}\n")
                    f.write(f"{self.position_1_z.text()}\n")
                    f.write(f"{self.position_2_x.text()}\n")
                    f.write(f"{self.position_2_y.text()}\n")
                    f.write(f"{self.position_2_z.text()}\n")
                    f.write(f"{self.position_3_x.text()}\n")
                    f.write(f"{self.position_3_y.text()}\n")
                    f.write(f"{self.position_3_z.text()}\n")
            except Exception as e:
                QMessageBox.critical(self, "Error saving file", str(e))

    def open_positions(self):
        file_path, selected_filter = QFileDialog.getOpenFileName(
            self, "Open Positions", getcwd(), "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    contents = f.readlines()
                    self.position_1_x.setText(contents[0])
                    self.position_1_y.setText(contents[1])
                    self.position_1_z.setText(contents[2])
                    self.position_2_x.setText(contents[3])
                    self.position_2_y.setText(contents[4])
                    self.position_2_z.setText(contents[5])
                    self.position_3_x.setText(contents[6])
                    self.position_3_y.setText(contents[7])
                    self.position_3_z.setText(contents[8])
            except Exception as e:
                QMessageBox.critical(self, "Error opening file", str(e))
        return
    
    def detect_ridges(self, frame):

        for result in results:
            if result.obb is not None:
                obb_boxes = result.obb.xyxyxyxy
                confidences = result.obb.conf
                class_ids = result.obb.cls

                print(f"Found {len(obb_boxes)} windows:")
                for i, [box, conf] in enumerate(zip(obb_boxes, confidences)):
                    # if conf < 0.5:
                    #     continue
                    box = box.tolist()
                    xs = [box[i][0] for i in range(len(box))]
                    ys = [box[i][1] for i in range(len(box))]
                    xs.append(xs[0])
                    ys.append(ys[0])
                    ax.plot(xs, ys, "g-", markersize=8)
                    # print(f"  Window {i+1}: Corners: {box}, Confidence: {confidences[i]:.2f}")
            else:
                print("No windows detected in this image.")

    def update_camera(self):
        """Convert OpenCV image to QImage and display it"""
        # Convert BGR to RGB
        ret, frame = self.camera.capture.read()
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Get image dimensions
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w

        # Convert to QImage
        qt_image = QImage(
            rgb_image.data,
            w,
            h,
            bytes_per_line,
            QImage.Format_RGB888,
        )

        # Scale image to fit label while maintaining aspect ratio
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            self.camera_feed.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        # Display in label
        self.camera_feed.setPixmap(scaled_pixmap)
        return


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
