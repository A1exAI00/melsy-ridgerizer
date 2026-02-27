import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from PIL import Image
import os
from typing import Dict


class FourierImageAnalyzer:
    def __init__(
        self,
        image_path: str,
        known_pattern_period: float,
        analize_band_width: int,
        is_horizontal: bool,
    ) -> None:
        self.image_path = image_path
        self.known_period = known_pattern_period
        self.analize_band_width = analize_band_width
        self.is_horizontal = is_horizontal
        return

    def analyze_periodic_pattern(self, visualize_matplotlib: bool = False) -> Dict:

        # Load image (convert to grayscale if needed)
        img = Image.open(self.image_path).convert("L")
        img_array = np.array(img, dtype=float)

        # Get image dimensions
        height, width = img_array.shape

        if self.is_horizontal:
            # Calculate center rows to average
            center = height // 2
            start_row = center - self.analize_band_width // 2
            end_row = start_row + self.analize_band_width

            # Extract and average the rows
            rows_section = img_array[start_row:end_row, :]
            averaged_signal = np.mean(rows_section, axis=0)
        else:
            center = width // 2
            start_column = center - self.analize_band_width // 2
            end_column = start_row + self.analize_band_width

            column_section = img_array[:, start_column:end_column]
            averaged_signal = np.mean(column_section, axis=1)

        # Remove DC component (mean) for better FFT analysis
        signal_no_dc = averaged_signal - np.mean(averaged_signal)

        # Apply window function to reduce spectral leakage
        window = np.hanning(width)
        windowed_signal = signal_no_dc * window

        # Compute FFT
        fft = np.fft.fft(windowed_signal)
        fft_freq = np.fft.fftfreq(width)

        # Get magnitude spectrum (only positive frequencies)
        magnitude = np.abs(fft[: width // 2])
        frequencies = fft_freq[: width // 2]

        # Find dominant frequency (excluding DC)
        # Skip the first few bins to avoid low-frequency noise
        min_freq_idx = 5  # Skip very low frequencies
        if len(magnitude) > min_freq_idx:
            dominant_idx = min_freq_idx + np.argmax(magnitude[min_freq_idx:])
            dominant_freq = frequencies[dominant_idx]

            # Calculate spatial period in pixels
            if dominant_freq != 0:
                spatial_period_pixels = 1 / abs(dominant_freq)
            else:
                spatial_period_pixels = float("inf")

            # Calculate phase at dominant frequency
            phase_radians = np.angle(fft[dominant_idx])
            phase_shift_pixels = (phase_radians / (2 * np.pi)) * spatial_period_pixels

            # Ensure phase shift is within [0, spatial_period)
            phase_shift_pixels = phase_shift_pixels % spatial_period_pixels

            # Confidence metric (normalized magnitude of dominant frequency)
            confidence = magnitude[dominant_idx] / np.sum(magnitude[min_freq_idx:])

        else:
            spatial_period_pixels = float("inf")
            phase_shift_pixels = 0
            dominant_freq = 0
            confidence = 0

        self.spatial_period_pixels = spatial_period_pixels
        self.phase_shift_pixels = phase_shift_pixels
        self.dominant_frequency_cycles_per_pixel = abs(dominant_freq)
        self.confidence = confidence
        self.averaged_signal = averaged_signal
        self.fft_magnitude = magnitude
        self.fft_frequencies = frequencies

        self.coefficient_from_pixels_to_mm = (
            self.known_period / self.spatial_period_pixels
        )
        self.phase_shift_mm = (
            self.phase_shift_pixels * self.coefficient_from_pixels_to_mm
        )

        if visualize_matplotlib:
            # Create visualization
            fig, axes = plt.subplots(3, 1, figsize=(12, 10))

            # Plot original image with averaged rows highlighted
            axes[0].imshow(img_array, cmap="gray")
            axes[0].axhline(y=start_row, color="r", linestyle="--", alpha=0.5)
            axes[0].axhline(y=end_row - 1, color="r", linestyle="--", alpha=0.5)
            axes[0].set_title(f"Original Image (averaged rows {start_row}-{end_row-1})")
            axes[0].axis("off")

            # Plot averaged signal
            x_pixels = np.arange(width)
            axes[1].plot(x_pixels, averaged_signal, "b-", linewidth=1)
            axes[1].set_xlabel("Pixel position")
            axes[1].set_ylabel("Intensity")
            axes[1].set_title("Averaged Signal (10 rows)")
            axes[1].grid(True, alpha=0.3)

            # Plot FFT magnitude spectrum
            axes[2].plot(frequencies[min_freq_idx:], magnitude[min_freq_idx:], "g-")
            axes[2].axvline(
                x=dominant_freq,
                color="r",
                linestyle="--",
                label=f"Dominant freq: {dominant_freq:.4f} cycles/pixel",
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
    filename = os.listdir(directory)[0]
    image_path = f"{directory}/{filename}"

    known_pattern_period = 0.1  # mm
    band_width = 10

    analyzer = FourierImageAnalyzer(
        image_path=image_path,
        known_pattern_period=known_pattern_period,
        analize_band_width=band_width,
        is_horizontal=True,
    )
    analyzer.analyze_periodic_pattern(visualize_matplotlib=True)

    print(
        "Pixels to mm coefficient = ",
        analyzer.coefficient_from_pixels_to_mm,
        " mm/pixel",
    )
    print("Spatial period = ", analyzer.spatial_period_pixels, " pixels")
    print("Phase shift = ", analyzer.phase_shift_pixels, " pixels")
    print("Phase shift = ", analyzer.phase_shift_mm, " mm")

    return


def main_multiple_run():
    directory = "images/home_accuracy"

    known_pattern_period = 0.1  # mm
    band_width = 10

    periods = []
    phase_shifts = []
    for filename in os.listdir(directory):
        image_path = f"{directory}/{filename}"

        try:
            analyzer = FourierImageAnalyzer(
                image_path=image_path,
                known_pattern_period=known_pattern_period,
                analize_band_width=band_width,
                is_horizontal=True,
            )
            analyzer.analyze_periodic_pattern(visualize_matplotlib=False)

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
    main_single_run()
    # main_multiple_run()
