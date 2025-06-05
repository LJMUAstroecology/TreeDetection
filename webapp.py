# Import necessary modules from Flask for web app functionality
from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for
import os  # For file and directory operations
from werkzeug.utils import secure_filename  # For safely handling uploaded filenames
from EndToEnd import run_end_to_end  # Import the main processing function from EndToEnd.py

# Define the folder where uploaded files will be stored
UPLOAD_FOLDER = 'uploads'
# Define the folder where output files will be stored
OUTPUT_FOLDER = 'outputs'
# Define allowed file extensions for upload
ALLOWED_EXTENSIONS = {'tif', 'tiff'}

# Create the Flask web application
app = Flask(__name__)
# Set configuration for upload and output folders
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Ensure the upload and output directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Function to check if the uploaded file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Define the main route for file upload and processing
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':  # If the form is submitted
        if 'file' not in request.files:  # Check if file part is present
            return 'No file part', 400
        file = request.files['file']  # Get the uploaded file
        if file.filename == '':  # Check if a file was selected
            return 'No selected file', 400
        if file and allowed_file(file.filename):  # Check file extension
            filename = secure_filename(file.filename)  # Sanitize filename
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  # Full path for upload
            file.save(upload_path)  # Save the uploaded file
            # Run the end-to-end image processing pipeline
            output_path = run_end_to_end(upload_path, app.config['OUTPUT_FOLDER'])
            output_filename = os.path.basename(output_path)  # Get output filename
            # Redirect to the download link for the processed file
            return redirect(url_for('download_file', filename=output_filename))
    # Render the upload form for GET requests
    return render_template_string('''
        <!doctype html>
        <title>Upload TIFF for Processing</title>
        <h1>Upload a TIFF file</h1>
        <form method=post enctype=multipart/form-data>
          <input type=file name=file accept=".tif,.tiff">
          <input type=submit value=Upload>
        </form>
    ''')

# Define the route for downloading the processed output file
@app.route('/outputs/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# Run the Flask app if this script is executed directly
if __name__ == '__main__':
    app.run(debug=True)
