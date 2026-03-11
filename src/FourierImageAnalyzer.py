import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from PIL import Image
import os
from typing import Dict


class FourierImageAnalyzer:
    def __init__(
        self,
        image_PIL: Image = None,
        image_path: str = None,
        is_horizontal: bool = True,
    ) -> None:
        self.image_array = self.get_image_array(image_PIL, image_path)
        self.height, self.width = self.image_array.shape
        self.is_horizontal = is_horizontal
        return

    def analyze_periodic_pattern(
        self,
        analize_band_center: int,
        analize_band_width: int,
        known_period: float,
    ) -> Dict:

        if self.is_horizontal:
            self.start_row = analize_band_center - analize_band_width // 2
            self.end_row = self.start_row + analize_band_width

            rows_section = self.image_array[self.start_row : self.end_row, :]
            averaged_signal = np.mean(rows_section, axis=0)
        else:
            raise Exception("Not implemented")

        signal_no_dc = averaged_signal - np.mean(averaged_signal)

        window = np.hanning(self.width)
        windowed_signal = signal_no_dc * window

        fft = np.fft.fft(windowed_signal)
        fft_freq = np.fft.fftfreq(self.width)

        magnitude = np.abs(fft[: self.width // 2])
        frequencies = fft_freq[: self.width // 2]

        min_freq_idx = 5  # Skip very low frequencies
        if len(magnitude) > min_freq_idx:
            dominant_idx = min_freq_idx + np.argmax(magnitude[min_freq_idx:])
            dominant_freq = frequencies[dominant_idx]

            if dominant_freq != 0:
                spatial_period_pixels = 1 / abs(dominant_freq)
            else:
                spatial_period_pixels = float("inf")

            phase_radians = np.angle(fft[dominant_idx])
            phase_shift_pixels = (phase_radians / (2 * np.pi)) * spatial_period_pixels
            phase_shift_pixels = phase_shift_pixels % spatial_period_pixels

        else:
            spatial_period_pixels = float("inf")
            phase_shift_pixels = 0
            dominant_freq = 0

        self.img_array = self.image_array
        self.min_freq_idx = min_freq_idx
        self.spatial_period_pixels = spatial_period_pixels
        self.phase_shift_pixels = phase_shift_pixels
        self.dominant_frequency_cycles_per_pixel = abs(dominant_freq)
        self.averaged_signal = averaged_signal
        self.fft_magnitude = magnitude
        self.fft_frequencies = frequencies

        self.coefficient_from_pixels_to_mm = known_period / self.spatial_period_pixels
        self.phase_shift_mm = (
            self.phase_shift_pixels * self.coefficient_from_pixels_to_mm
        )

        return

    @staticmethod
    def get_image_array(image_PIL: Image = None, image_path: str = None) -> np.ndarray:
        if image_PIL is None and image_path is None:
            raise Exception("Did not provide image nor image_path")
        if image_PIL is not None and image_path is not None:
            raise Exception("Either image nor image_path should be provided")

        if image_PIL is not None:
            img = image_PIL.convert("L")
            img_array = np.array(img, dtype=float)

        if image_path is not None:
            img = Image.open(image_path).convert("L")
            img_array = np.array(img, dtype=float)

        return img_array

    def visualize_matplotlib(self):
        # Create visualization
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))

        # Plot original image with averaged rows highlighted
        axes[0].imshow(self.img_array, cmap="gray")
        axes[0].axhline(y=self.start_row, color="r", linestyle="--", alpha=0.5)
        axes[0].axhline(y=self.end_row - 1, color="r", linestyle="--", alpha=0.5)
        axes[0].set_title(
            f"Original Image (averaged rows {self.start_row}-{self.end_row-1})"
        )
        axes[0].axis("off")

        # Plot averaged signal
        x_pixels = np.arange(self.width)
        axes[1].plot(x_pixels, self.averaged_signal, "b-", linewidth=1)
        axes[1].plot(
            x_pixels,
            (
                np.sin(
                    1/self.spatial_period_pixels * 2 * np.pi * x_pixels
                    + self.phase_shift_pixels * 2 * np.pi
                )
                + 1
            )
            * np.max(self.averaged_signal)/2,
            "g-",
            linewidth=1,
        )
        axes[1].set_xlabel("Pixel position")
        axes[1].set_ylabel("Intensity")
        axes[1].set_title("Averaged Signal (10 rows)")
        axes[1].grid(True, alpha=0.3)

        # Plot FFT magnitude spectrum
        axes[2].plot(
            self.fft_frequencies[self.min_freq_idx :],
            self.fft_magnitude[self.min_freq_idx :],
            "g-",
        )
        axes[2].axvline(
            x=self.dominant_frequency_cycles_per_pixel,
            color="r",
            linestyle="--",
            label=f"Dominant freq: {self.dominant_frequency_cycles_per_pixel:.4f} cycles/pixel",
        )
        axes[2].set_xlabel("Spatial frequency (cycles/pixel)")
        axes[2].set_ylabel("Magnitude")
        axes[2].set_title("FFT Magnitude Spectrum")
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()
        return


def main_single_run():
    directory = "images/home_accuracy"
    directory = "images/home_accuracy_ring_light"
    filename = os.listdir(directory)[0]
    image_path = f"{directory}/{filename}"

    known_pattern_period = 0.15  # mm
    band_width = 100

    analyzer = FourierImageAnalyzer(
        image_path=image_path,
    )
    analyzer.analyze_periodic_pattern(
        analize_band_center=1000,
        analize_band_width=band_width,
        known_period=known_pattern_period,
    )
    analyzer.visualize_matplotlib()

    print(
        "Pixels to mm coefficient = ",
        analyzer.coefficient_from_pixels_to_mm,
        " mm/pixel",
    )
    print("Spatial period = ", analyzer.spatial_period_pixels, " pixels")
    print("Phase shift = ", analyzer.phase_shift_pixels, " pixels")
    print("Phase shift = ", analyzer.phase_shift_mm, " mm")

    return


def main_single_run2():
    directory = "images/home_accuracy"
    directory = "images/home_accuracy_ring_light"
    filename = os.listdir(directory)[0]
    image_path = f"{directory}/{filename}"

    known_pattern_period = 0.15  # mm
    band_width = 100

    analyzer1 = FourierImageAnalyzer(
        image_path=image_path,
    )
    analyzer1.analyze_periodic_pattern(
        analize_band_center=500,
        analize_band_width=band_width,
        known_period=known_pattern_period,
    )

    analyzer2 = FourierImageAnalyzer(
        image_path=image_path,
    )
    analyzer2.analyze_periodic_pattern(
        analize_band_center=1500,
        analize_band_width=band_width,
        known_period=known_pattern_period,
    )

    fig, axes = plt.subplots(1, 1, figsize=(12, 10))

    # Plot original image with averaged rows highlighted
    axes.imshow(analyzer1.img_array, cmap="gray")
    axes.axhline(y=analyzer1.start_row, color="r", linestyle="--", alpha=0.5)
    axes.axhline(y=analyzer2.start_row, color="r", linestyle="--", alpha=0.5)
    axes.axhline(y=analyzer1.end_row - 1, color="r", linestyle="--", alpha=0.5)
    axes.axhline(y=analyzer2.end_row - 1, color="r", linestyle="--", alpha=0.5)

    ridges_offset_n = 0
    while (
        ridges_offset_n * analyzer1.spatial_period_pixels < analyzer1.width
        and ridges_offset_n * analyzer2.spatial_period_pixels < analyzer2.width
    ):
        axes.axline(
            (
                analyzer1.phase_shift_pixels
                + analyzer1.spatial_period_pixels * ridges_offset_n,
                500,
            ),
            (
                analyzer2.phase_shift_pixels
                + analyzer2.spatial_period_pixels * ridges_offset_n,
                1500,
            ),
            color="black",
            linestyle="--",
            alpha=0.5,
        )
        ridges_offset_n += 1
    axes.axis("off")

    plt.tight_layout()
    plt.show()
    return


def main_multiple_run():
    directory = "images/home_accuracy"

    known_pattern_period = 0.15  # mm
    band_width = 10

    periods = []
    phase_shifts = []
    for filename in os.listdir(directory):
        image_path = f"{directory}/{filename}"

        try:
            analyzer = FourierImageAnalyzer(
                known_pattern_period=known_pattern_period,
                analize_band_width=band_width,
                is_horizontal=True,
            )
            analyzer.analyze_periodic_pattern(
                image_path=image_path, visualize_matplotlib=False
            )

            periods.append(analyzer.spatial_period_pixels)
            phase_shifts.append(analyzer.phase_shift_mm)

        except FileNotFoundError:
            print(f"Error: Image file '{image_path}' not found.")
        except Exception as e:
            print(f"Error analyzing image: {str(e)}")

    print("Period (mean) = ", np.mean(periods), " pixels")
    print("Period (std) = ", np.std(periods), " pixels")
    print("Phase shift (mean) = ", np.mean(phase_shifts), " mm")
    print("Phase shift (std) = ", np.std(phase_shifts), " mm")


if __name__ == "__main__":
    # main_single_run()
    main_single_run2()
    # main_multiple_run()
