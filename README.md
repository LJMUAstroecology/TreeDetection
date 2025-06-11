# TreeDetection

A Python tool for processing large TIFF images by slicing them into smaller TIFF tiles, processing them, and stitching them back together while preserving metadata.

## Overview

This tool is designed to handle large TIFF images by breaking them down into manageable tiles, allowing for processing of individual sections, and then reassembling them into a complete image. It's particularly useful for processing large aerial or satellite imagery where memory constraints might be an issue.

## Features

- Slice large TIFF images into smaller tiles
- Customizable tile size and stride parameters
- Optional padding for edge cases
- Preserve original TIFF metadata
- Support for processing individual tiles
- Automatic stitching of processed tiles back into a complete TIFF

## Requirements

- Python 3.10
- Required packages:
  - numpy
  - PIL (Python Imaging Library)
  - tifffile
  - matplotlib

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/LJMUAstroecology/TreeDetection.git
   cd TreeDetection
   ```

### Using Conda

1. Create a new conda environment:
   ```bash
   conda create -n TreeDetection python=3.9
   ```

2. Activate the environment:
   ```bash
   conda activate TreeDetection
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

The main script `EndToEnd.py` provides a complete pipeline for image processing:

1. **Image Slicing**: The `ImageSlicer` class handles the slicing of large TIFF images into smaller tiles.
   ```python
   slicer = ImageSlicer(
       source='path/to/image.tif',
       size=(1026, 1824),  # Tile size
       strides=(926, 1724),  # Stride between tiles
       padding=False  # Optional padding
   )
   transformed_images = slicer.transform()
   ```

2. **Processing Tiles**: Each tile can be processed individually. The script includes an example of injecting fake detections, but this can be replaced with your own processing logic.

3. **Stitching**: The processed tiles are stitched back together into a complete TIFF image, preserving the original metadata.

## File Structure

- `EndToEnd.py`: Main script containing all the processing logic
- `Sliced_Images/`: Directory for storing sliced image tiles
- `Detected_Images/`: Directory for storing processed image tiles
- `stitched_output.tiff`: Final output file

## Configuration

The script uses the following default parameters:
- Tile size: 1026x1824 pixels
- Stride: 926x1724 pixels
- Input: TIFF format
- Output: TIFF format with preserved metadata

## Example

```python
# Define paths
original_tiff_path = 'path/to/input.tif'
sliced_dir = 'Sliced_Images'
detected_dir = 'Detected_Images'
output_tiff_path = 'stitched_output.tiff'

# Create slicer instance
slicer = ImageSlicer(original_tiff_path, size=(1026, 1824), strides=(926, 1724), padding=False)
transformed_images = slicer.transform()

# Process and stitch images
# ... (processing steps) ...

# Stitch the images back into a TIFF
stitch_images_to_tiff(detected_dir, output_tiff_path, original_tiff_path, 
                     tile_size=(1026, 1824), strides=(926, 1724))
```

## Notes

- The script includes a sample detection injection function (`inject_fake_detections`) that can be replaced with your own processing logic
- File naming convention for tiles: `image_row_column.png`
- The stitching process preserves the original TIFF metadata
- Make sure to have sufficient disk space for the intermediate files

## License: TBD


