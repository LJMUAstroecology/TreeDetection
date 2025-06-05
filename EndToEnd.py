# Import required modules
import os  # For file and directory operations
import numpy as np  # For numerical operations and array handling
from PIL import Image, ImageDraw  # For image processing and drawing
import tifffile  # For reading and writing TIFF files
import matplotlib.pyplot as plt  # For saving images

# Define a class for slicing images into smaller tiles
class ImageSlicer:
    def __init__(self, source, size, strides, padding=False):
        self.source = source  # Path to the source image
        self.size = size  # Size of each tile (height, width)
        self.strides = strides  # Step size for moving the window
        self.padding = padding  # Whether to pad the image

    def __offset_op(self, input_length, output_length, stride):
        # Calculate offset for padding
        offset = input_length - (stride * ((input_length - output_length) // stride) + output_length)
        return offset

    def __padding_op(self, Image):
        # Pad the image if needed
        if self.offset_x > 0:
            padding_x = self.strides[0] - self.offset_x
        else:
            padding_x = 0
        if self.offset_y > 0:
            padding_y = self.strides[1] - self.offset_y
        else:
            padding_y = 0
        # Create a new padded image
        Padded_Image = np.zeros(shape=(Image.shape[0] + padding_x, Image.shape[1] + padding_y, Image.shape[2]), dtype=Image.dtype)
        # Place the original image in the center
        Padded_Image[padding_x // 2:(padding_x // 2) + Image.shape[0], padding_y // 2:(padding_y // 2) + Image.shape[1], :] = Image
        return Padded_Image

    def __convolution_op(self, Image):
        # Slide a window over the image and extract tiles
        small_images = []
        for i in range(0, Image.shape[0] - self.size[0] + 1, self.strides[0]):
            for j in range(0, Image.shape[1] - self.size[1] + 1, self.strides[1]):
                small_images.append((Image[i:i + self.size[0], j:j + self.size[1], :], i, j))
        return small_images

    def transform(self):
        # Main function to slice the image
        if not os.path.exists(self.source):
            raise Exception("Path does not exist!")

        Image = tifffile.imread(self.source)  # Read the TIFF image
        Images = [Image]  # List of images (single image here)
        transformed_images = {}  # Dictionary to store tiles

        if self.padding:
            # If padding is enabled, calculate and apply padding
            if self.strides[0] is None:
                self.strides[0] = self.size[0]
            if self.strides[1] is None:
                self.strides[1] = self.size[1]

            self.offset_x = Images[0].shape[0] % self.size[0]
            self.offset_y = Images[0].shape[1] % self.size[1]

            Images = [self.__padding_op(img) for img in Images]

        for i, Image in enumerate(Images):
            # For each image, extract tiles
            transformed_images[str(i)] = self.__convolution_op(Image)

        return transformed_images

    def save_images(self, transformed, save_dir, filename):
        # Save the tiles as PNG images
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        for key, val in transformed.items():
            for img, row, col in val:
                plt.imsave(os.path.join(save_dir, f'{filename}_{row}_{col}.png'), img)

# Function to inject fake detections (draw random rectangles) on an image
def inject_fake_detections(image_path, output_path):
    img = Image.open(image_path)  # Open the image
    draw = ImageDraw.Draw(img)  # Create a drawing context

    # Generate random box coordinates
    for _ in range(5):  # Inject 5 random boxes
        x1 = np.random.randint(0, img.width - 50)
        y1 = np.random.randint(0, img.height - 50)
        x2 = x1 + np.random.randint(20, 50)
        y2 = y1 + np.random.randint(20, 50)
        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)  # Draw rectangle

    img.save(output_path)  # Save the modified image

# Function to check if a filename matches the expected pattern
def is_valid_filename(filename):
    parts = filename.split('_')  # Split by underscore
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

# Function to stitch processed tiles back into a single TIFF image
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
        row, col = map(lambda x: int(x.split('.')[0]), img_name.split('_')[1:])  # Get row, col from filename
        img_path = os.path.join(input_dir, img_name)  # Full path to image
        img = Image.open(img_path)  # Open the image

        stitched_image.paste(img, (col, row))  # Paste tile at correct position

    # Save the stitched image with original metadata
    stitched_array = np.array(stitched_image)
    tifffile.imwrite(output_path, stitched_array, metadata=original_meta)

# The following code is for running the pipeline as a script
# Define paths
original_tiff_path = '/Users/astslong/data/ortho_data/morarano/morarano2y1_ort1.tif'  # Path to the original TIFF file
sliced_dir = 'Sliced_Images'  # Directory to save sliced images
detected_dir = 'Detected_Images'  # Directory to save images with detections
output_tiff_path = 'stitched_output.tiff'  # Output stitched TIFF file path

# Slicing
slicer = ImageSlicer(original_tiff_path, size=(1026, 1824), strides=(926, 1724), padding=False)  # Create slicer
transformed_images = slicer.transform()  # Slice the image

# Save sliced images
if not os.path.exists(sliced_dir):
    os.makedirs(sliced_dir)
for i, images in enumerate(transformed_images['0']):
    img, row, col = images
    Image.fromarray(img).save(os.path.join(sliced_dir, f'image_{row}_{col}.png'))  # Save each tile

# Inject fake detections
if not os.path.exists(detected_dir):
    os.makedirs(detected_dir)
for img_name in os.listdir(sliced_dir):
    if is_valid_filename(img_name):
        inject_fake_detections(os.path.join(sliced_dir, img_name), os.path.join(detected_dir, img_name))

# Stitch the images back into a TIFF
stitch_images_to_tiff(detected_dir, output_tiff_path, original_tiff_path, tile_size=(1026, 1824), strides=(926, 1724))

print("End-to-end process complete. Output saved to", output_tiff_path)
