from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for
import os
from werkzeug.utils import secure_filename
from EndToEnd import run_end_to_end

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'tif', 'tiff'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part', 400
        file = request.files['file']
        if file.filename == '':
            return 'No selected file', 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)
            # Run the end-to-end process
            output_path = run_end_to_end(upload_path, app.config['OUTPUT_FOLDER'])
            output_filename = os.path.basename(output_path)
            return redirect(url_for('download_file', filename=output_filename))
    return render_template_string('''
        <!doctype html>
        <title>Upload TIFF for Processing</title>
        <h1>Upload a TIFF file</h1>
        <form method=post enctype=multipart/form-data>
          <input type=file name=file accept=".tif,.tiff">
          <input type=submit value=Upload>
        </form>
    ''')

@app.route('/outputs/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
