from os import path

import cv2

from src.misc import get_next_filename
from dataclasses import dataclass


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
    def __init__(self, config: CameraConfig) -> None:
        """Constructor for Camera class.

        :param config: Config for camera device.
        :type config: CameraConfig

        :returns:
        :rtype: None
        """
        self.config = config
        return

    def create_capture(self) -> None:
        """Establich the connection with the camera device specified with `CameraConfig.index`.

        Other parameters from `CameraConfig` are set at this point.

        :returns:
        :rtype: None
        """
        self.capture = cv2.VideoCapture(self.config.index)
        if not self.capture.isOpened():
            raise Exception(
                f"Error: Could not open camera at index {self.config.index}"
            )

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
        """Save image from camera on a filesystem.

        :param dir: Directory to save image to.
        :type dir: str
        :param name: Name of the file.
        :type name: str
        :param ext: Extention of the file.
        :type ext: str

        :returns:
        :rtype: None
        """
        ret, frame = self.capture.read()

        if not ret:
            raise Exception("Could not get camera feed.")
        
        new_filename = get_next_filename(dir, name, ext) + ext
        cv2.imwrite(path.join(dir, new_filename), frame)
        return

    def get_image(self):
        """Save image from camera on a filesystem.

        :returns: Return boolean code and cv2.MatLike frame object.
        :rtype: Tuple[bool, cv2.MatLike]
        """
        return self.capture.read()

    def close(self) -> None:
        """Close camera capture.

        :returns: 
        :rtype: None
        """
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
