from flask import Flask, request, send_from_directory
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
            return f"""
            Processing complete.<br>
            Output saved to <a href='/download/{output_filename}'>{output_filename}</a><br>
            Shapefile components:<br>
            <a href='/download_shapefile'>Download Shapefile (all parts)</a>
            """

    return '''
    <!doctype html>
    <title>Upload TIFF</title>
    <h1>Upload a TIFF file</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

@app.route('/download_shapefile')
def download_shapefile():
    # Shapefile consists of several files with the same basename
    base = 'bboxes_merged'
    exts = ['shp', 'shx', 'dbf', 'prj', 'cpg']
    links = []
    for ext in exts:
        fname = f"{base}.{ext}"
        if os.path.exists(os.path.join(OUTPUT_FOLDER, fname)):
            links.append(f'<a href="/download/{fname}">{fname}</a>')
    return "<br>".join(links)

if __name__ == '__main__':
    app.run(debug=True)
