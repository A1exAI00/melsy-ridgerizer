from src.misc import get_next_filename

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
            get_next_filename(directory, filename, extension) + extension, frame
        )
        return

    def close(self) -> None:
        self.capture.release()
        cv2.destroyAllWindows()
        return


if __name__ == "__main__":
    # Initialize the camera (0 is usually the default built-in camera)
    cam = Camera(index=3, width=100, height=100)
    cam.create_capture()

    while True:
        # Capture frame-by-frame
        ret, frame = cam.capture.read()

        # If frame is read correctly, ret is True
        if not ret:
            print("Can't receive frame. Exiting ...")
            break

        # Display the resulting frame
        cv2.imshow("Webcam Feed", frame)

        # Press 'q' to quit the window
        if cv2.waitKey(1) == ord("q"):
            break

    # When everything is done, release the capture and destroy windows
    cam.close()