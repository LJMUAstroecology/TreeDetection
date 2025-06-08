from flask import Flask, request
import os
from EndToEnd import run_end_to_end

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
            # Call run_end_to_end, do NOT assign its result to output_path
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
