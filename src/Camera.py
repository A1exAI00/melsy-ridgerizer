from src.misc import get_next_filename
from dataclasses import dataclass

import cv2


CAMERA_MAX_WIDTH = 3840
CAMERA_MAX_HEIGHT = 2160


@dataclass
class CameraConfig:
    index: int | None = None
    width: int | None = None
    height: int | None = None
    buffer_size: int | None = None
    exposure: int | None = None


class Camera:
    def __init__(self, camera_config: CameraConfig) -> None:
        self.config = camera_config
        return

    def create_capture(self) -> None:
        self.capture = cv2.VideoCapture(self.config.index)
        if not self.capture.isOpened():
            raise Exception(f"Error: Could not open camera at index {self.config.index}")
        
        # Configure camera
        if hasattr(self.config, "width") and self.config.height is not None:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        if hasattr(self.config, "height") and self.config.height is not None:
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        if hasattr(self.config, "buffer_size") and self.config.buffer_size is not None:
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)
        if hasattr(self.config, "exposure") and self.config.exposure is not None:
            self.capture.set(cv2.CAP_PROP_EXPOSURE, self.config.exposure)
        return

    def save_image(self, dir: str, name: str = "image", ext: str = "png") -> None:
        ret, frame = self.capture.read()
        new_filename = get_next_filename(dir, name, ext) + ext
        cv2.imwrite(new_filename, frame)
        return
    
    def get_image(self):
        ret, frame = self.capture.read()
        return (ret, frame)

    def close(self) -> None:
        self.capture.release()
        cv2.destroyAllWindows()
        return


if __name__ == "__main__":
    cam = Camera(index=3, width=100, height=100)
    cam.create_capture()

    while True:
        ret, frame = cam.capture.read()

        if not ret:
            print("Can't receive frame. Exiting ...")
            break

        cv2.imshow("Webcam Feed", frame)

        # Press 'q' to quit the window
        if cv2.waitKey(1) == ord("q"):
            break

    cam.close()
