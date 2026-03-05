from os import makedirs, path

import cv2


class Camera:
    def __init__(
        self,
        index: int,
        width: int = 3840,
        height: int = 2160,
        buffer_size: int = 1,
        exposure: int = 100,
    ) -> None:
        self.index = index
        self.width = width
        self.height = height
        self.buffer_size = buffer_size
        self.exposure = exposure
        return

    def create_capture(self) -> None:
        self.capture = cv2.VideoCapture(self.index)
        if not self.capture.isOpened():
            print("Error: Could not open camera.")
            exit()
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
        self.capture.set(cv2.CAP_PROP_EXPOSURE, self.exposure)
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
