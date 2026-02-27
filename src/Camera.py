from os import makedirs, path

import cv2


class Camera:
    def __init__(
        self, width: int = 3840, height: int = 2160, buffer_size: int = 1
    ) -> None:
        self.width = width
        self.height = height
        self.buffer_size = buffer_size
        return

    def create_capture(self) -> None:
        self.capture = cv2.VideoCapture(3)
        if not self.capture.isOpened():
            print("Error: Could not open camera.")
            exit()
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return

    def save_image(
        self, directory, filename: str = "image", extension: str = "png"
    ) -> None:
        ret, frame = self.capture.read()
        cv2.imwrite(
            self.get_next_filename(directory, filename, extension) + extension, frame
        )
        return

    def close(self) -> None:
        self.capture.release()
        cv2.destroyAllWindows()
        return

    @staticmethod
    def get_next_filename(
        directory: str, base_name: str = "image", extension: str = "png"
    ) -> str:
        makedirs(directory, exist_ok=True)

        counter = 1
        while True:
            filename = path.join(directory, f"{base_name}{counter:03d}.{extension}")
            if not path.exists(filename):
                return filename
            counter += 1
        return
