import os
import numpy as np
from PIL import Image, ImageDraw
import tifffile
import matplotlib.pyplot as plt
import rasterio
from rasterio.windows import Window
from rasterio.transform import Affine, xy
from flask import Flask, request, render_template
import json
import csv

class ImageSlicer:
    def __init__(self, source, size, strides, padding=False):
        self.source = source
        self.size = size
        self.strides = strides
        self.padding = padding

    def __offset_op(self, input_length, output_length, stride):
        offset = input_length - (stride * ((input_length - output_length) // stride) + output_length)
        return offset

    def __padding_op(self, Image):
        if self.offset_x > 0:
            padding_x = self.strides[0] - self.offset_x
        else:
            padding_x = 0
        if self.offset_y > 0:
            padding_y = self.strides[1] - self.offset_y
        else:
            padding_y = 0
        Padded_Image = np.zeros(shape=(Image.shape[0] + padding_x, Image.shape[1] + padding_y, Image.shape[2]), dtype=Image.dtype)
        Padded_Image[padding_x // 2:(padding_x // 2) + Image.shape[0], padding_y // 2:(padding_y // 2) + Image.shape[1], :] = Image
        return Padded_Image

    def __convolution_op(self, Image):
        small_images = []
        for i in range(0, Image.shape[0] - self.size[0] + 1, self.strides[0]):
            for j in range(0, Image.shape[1] - self.size[1] + 1, self.strides[1]):
                small_images.append((Image[i:i + self.size[0], j:j + self.size[1], :], i, j))
        return small_images

    def transform(self):
        if not os.path.exists(self.source):
            raise Exception("Path does not exist!")

        Image = tifffile.imread(self.source)
        Images = [Image]
        transformed_images = {}

        if self.padding:
            if self.strides[0] is None:
                self.strides[0] = self.size[0]
            if self.strides[1] is None:
                self.strides[1] = self.size[1]

            self.offset_x = Images[0].shape[0] % self.size[0]
            self.offset_y = Images[0].shape[1] % self.size[1]

            Images = [self.__padding_op(img) for img in Images]

        for i, Image in enumerate(Images):
            transformed_images[str(i)] = self.__convolution_op(Image)

        return transformed_images

    def save_images(self, transformed, save_dir, filename):
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        for key, val in transformed.items():
            for img, row, col in val:
                plt.imsave(os.path.join(save_dir, f'{filename}_{row}_{col}.png'), img)

def inject_fake_detections(image_path, output_path):
    # This version works for TIFFs using rasterio to preserve georeferencing
    with rasterio.open(image_path) as src:
        data = src.read()
        meta = src.meta.copy()
        transform = src.transform

    img = np.moveaxis(data, 0, -1)  # (bands, H, W) -> (H, W, bands)
    pil_img = Image.fromarray(img.astype(np.uint8))
    draw = ImageDraw.Draw(pil_img)
    bbox_gps_list = []
    for _ in range(5):
        x1 = np.random.randint(0, pil_img.width - 50)
        y1 = np.random.randint(0, pil_img.height - 50)
        x2 = x1 + np.random.randint(20, 50)
        y2 = y1 + np.random.randint(20, 50)
        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)

        # Convert pixel coordinates to geospatial coordinates
        top_left = xy(transform, y1, x1)
        bottom_right = xy(transform, y2, x2)
        bbox_gps = {
            "image": os.path.basename(image_path),
            "pixel_bbox": [x1, y1, x2, y2],
            "gps_bbox": {
                "top_left": top_left,
                "bottom_right": bottom_right
            }
        }
        bbox_gps_list.append(bbox_gps)

    img_with_boxes = np.array(pil_img)
    # Move axis back to (bands, H, W)
    if img_with_boxes.ndim == 3:
        data_out = np.moveaxis(img_with_boxes, -1, 0)
    else:
        data_out = img_with_boxes[np.newaxis, ...]
    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(data_out.astype(meta['dtype']))

    return bbox_gps_list

def is_valid_tiff_filename(filename):
    # Accepts tile_{row}_{col}.tif or .tiff
    if not (filename.endswith('.tif') or filename.endswith('.tiff')):
        return False
    parts = filename.replace('.tiff', '').replace('.tif', '').split('_')
    if len(parts) != 3 or not parts[0] == 'tile':
        return False
    try:
        int(parts[1])
        int(parts[2])
    except ValueError:
        return False
    return True

def slice_geotiff_to_tiffs(input_path, output_dir, tile_width, tile_height):
    os.makedirs(output_dir, exist_ok=True)
    with rasterio.open(input_path) as src:
        meta = src.meta.copy()
        for i in range(0, src.height, tile_height):
            for j in range(0, src.width, tile_width):
                window = Window(j, i, tile_width, tile_height)
                transform = rasterio.windows.transform(window, src.transform)
                win_width = min(tile_width, src.width - j)
                win_height = min(tile_height, src.height - i)
                meta.update({
                    "height": win_height,
                    "width": win_width,
                    "transform": transform
                })
                tile = src.read(window=window, out_shape=(src.count, win_height, win_width))
                out_path = os.path.join(output_dir, f"tile_{i}_{j}.tif")
                with rasterio.open(out_path, "w", **meta) as dst:
                    dst.write(tile)

def stitch_tiff_tiles(input_dir, output_path):
    # Gather all tile filenames
    tile_files = [f for f in os.listdir(input_dir) if is_valid_tiff_filename(f)]
    if not tile_files:
        raise ValueError("No TIFF tiles found in the directory.")

    # Parse row and col from filenames
    tile_info = []
    for fname in tile_files:
        parts = fname.replace('.tif', '').replace('.tiff', '').split('_')
        row, col = int(parts[1]), int(parts[2])
        tile_info.append((row, col, fname))
    tile_info.sort()  # Sort by row, then col

    # Open first tile to get metadata
    first_tile_path = os.path.join(input_dir, tile_info[0][2])
    with rasterio.open(first_tile_path) as src:
        meta = src.meta.copy()
        tile_height, tile_width = src.height, src.width
        dtype = src.dtypes[0]
        count = src.count
        crs = src.crs
        base_transform = src.transform

    # Find max extents by reading each tile's size
    max_bottom = max_right = 0
    for row, col, fname in tile_info:
        with rasterio.open(os.path.join(input_dir, fname)) as src:
            bottom = row + src.height
            right = col + src.width
            max_bottom = max(max_bottom, bottom)
            max_right = max(max_right, right)
    out_height = max_bottom
    out_width = max_right

    # Prepare output array
    stitched = np.zeros((count, out_height, out_width), dtype=dtype)

    # Write each tile into the output array
    for row, col, fname in tile_info:
        with rasterio.open(os.path.join(input_dir, fname)) as src:
            data = src.read()
            h, w = src.height, src.width
            # Ensure band count matches
            if data.shape[0] > count:
                # More bands than expected, drop extras (e.g., drop alpha)
                data = data[:count, :, :]
            elif data.shape[0] < count:
                # Fewer bands, pad with zeros
                pad_shape = (count - data.shape[0], h, w)
                data = np.concatenate([data, np.zeros(pad_shape, dtype=data.dtype)], axis=0)
            stitched[:, row:row+h, col:col+w] = data

    # Update transform for the stitched raster
    meta.update({
        "height": out_height,
        "width": out_width,
        "transform": Affine(base_transform.a, base_transform.b, base_transform.c,
                            base_transform.d, base_transform.e, base_transform.f),
        "crs": crs
    })

    # Write stitched raster
    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(stitched)

    print(f"Stitched TIFF saved to {output_path}")

def run_end_to_end(
    original_tiff_path,
    sliced_dir='Sliced_Images',
    detected_dir='Detected_Images',
    output_tiff_path='stitched_output.tiff',
    tile_size=(1026, 1824)
):
    # 1. Slice TIFF directly into TIFF tiles
    slice_geotiff_to_tiffs(
        input_path=original_tiff_path,
        output_dir=sliced_dir,
        tile_width=tile_size[1],  # width (columns)
        tile_height=tile_size[0]  # height (rows)
    )

    # 2. Inject fake detections into each TIFF tile and save to detected_dir
    if not os.path.exists(detected_dir):
        os.makedirs(detected_dir)
    all_bboxes = []
    for img_name in os.listdir(sliced_dir):
        if is_valid_tiff_filename(img_name):
            bboxes = inject_fake_detections(
                os.path.join(sliced_dir, img_name),
                os.path.join(detected_dir, img_name)
            )
            all_bboxes.extend(bboxes)

    # Save all bounding box info to JSON
    with open(os.path.join(detected_dir, "detections_gps.json"), "w") as f:
        json.dump(all_bboxes, f, indent=2)

    # Save all bounding box info to CSV with unique IDs
    csv_path = os.path.join(detected_dir, "detections_gps.csv")
    with open(csv_path, "w", newline="") as csvfile:
        fieldnames = ["id", "image", "pixel_bbox", "gps_top_left", "gps_bottom_right"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for idx, bbox in enumerate(all_bboxes, 1):
            writer.writerow({
                "id": idx,
                "image": bbox["image"],
                "pixel_bbox": bbox["pixel_bbox"],
                "gps_top_left": bbox["gps_bbox"]["top_left"],
                "gps_bottom_right": bbox["gps_bbox"]["bottom_right"]
            })

    # 3. Stitch the TIFF tiles back into a single TIFF
    stitch_tiff_tiles(detected_dir, output_tiff_path)

    print("End-to-end process complete. Output saved to", output_tiff_path)

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            input_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(input_path)

            output_path = os.path.join(OUTPUT_FOLDER, 'stitched_output.tiff')
            run_end_to_end(
                original_tiff_path=input_path,
                sliced_dir='Sliced_Images',
                detected_dir='Detected_Images',
                output_tiff_path=output_path,
                tile_size=(1026, 1824)
            )

            output_filename = os.path.basename(output_path)
            return f"Processing complete. Output saved to {output_filename}"

    return '''
    <!doctype html>
    <title>Upload TIFF</title>
    <h1>Upload a TIFF file</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

if __name__ == '__main__':
    app.run(debug=True)
