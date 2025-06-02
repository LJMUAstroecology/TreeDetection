import os
import numpy as np
from PIL import Image, ImageDraw
import tifffile
import matplotlib.pyplot as plt

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
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    # Generate random box coordinates
    for _ in range(5):  # Inject 5 random boxes
        x1 = np.random.randint(0, img.width - 50)
        y1 = np.random.randint(0, img.height - 50)
        x2 = x1 + np.random.randint(20, 50)
        y2 = y1 + np.random.randint(20, 50)
        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)

    img.save(output_path)

def is_valid_filename(filename):
    parts = filename.split('_')
    if len(parts) != 3:
        return False
    if not parts[0] == 'image':
        return False
    try:
        int(parts[1])
        int(parts[2].split('.')[0])
    except ValueError:
        return False
    return True


def stitch_images_to_tiff(input_dir, output_path, original_tiff_path, tile_size, strides):
    # Load the original TIFF to get metadata and shape
    with tifffile.TiffFile(original_tiff_path) as tif:
        original_meta = {tag.name: tag.value for tag in tif.pages[0].tags.values()}
        original_image = tif.asarray()

    # Create a blank image with the same shape as the original
    stitched_image = Image.new('RGB', (original_image.shape[1], original_image.shape[0]))

    # List all processed PNG images
    images = [img for img in os.listdir(input_dir) if img.endswith('.png') and is_valid_filename(img)]

    # Ensure correct sorting of filenames
    try:
        images.sort(key=lambda x: (int(x.split('_')[1]), int(x.split('_')[2].split('.')[0])))
    except ValueError as e:
        print("Error while sorting filenames:", e)
        for img in images:
            try:
                print("Filename parts:", img.split('_')[1], img.split('_')[2].split('.')[0])
            except Exception as ex:
                print("Error parsing filename:", img, ex)
        raise

    for img_name in images:
        row, col = map(lambda x: int(x.split('.')[0]), img_name.split('_')[1:])
        img_path = os.path.join(input_dir, img_name)
        img = Image.open(img_path)

        stitched_image.paste(img, (col, row))

    # Save the stitched image with original metadata
    stitched_array = np.array(stitched_image)
    tifffile.imwrite(output_path, stitched_array, metadata=original_meta)


# Define paths
original_tiff_path = '/Users/astslong/data/ortho_data/morarano/morarano2y1_ort1.tif'  # Path to the original TIFF file
sliced_dir = 'Sliced_Images'  # Directory to save sliced images
detected_dir = 'Detected_Images'  # Directory to save images with detections
output_tiff_path = 'stitched_output.tiff'  # Output stitched TIFF file path

# Slicing
slicer = ImageSlicer(original_tiff_path, size=(1026, 1824), strides=(926, 1724), padding=False)
transformed_images = slicer.transform()

# Save sliced images
if not os.path.exists(sliced_dir):
    os.makedirs(sliced_dir)
for i, images in enumerate(transformed_images['0']):
    img, row, col = images
    Image.fromarray(img).save(os.path.join(sliced_dir, f'image_{row}_{col}.png'))

# Inject fake detections
if not os.path.exists(detected_dir):
    os.makedirs(detected_dir)
for img_name in os.listdir(sliced_dir):
    if is_valid_filename(img_name):
        inject_fake_detections(os.path.join(sliced_dir, img_name), os.path.join(detected_dir, img_name))

# Stitch the images back into a TIFF
stitch_images_to_tiff(detected_dir, output_tiff_path, original_tiff_path, tile_size=(1026, 1824), strides=(926, 1724))

print("End-to-end process complete. Output saved to", output_tiff_path)
