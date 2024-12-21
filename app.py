import os
from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from werkzeug.utils import secure_filename
import subprocess
import pandas as pd

# Initialize Flask app
app = Flask(__name__)

# Input and output directories
INPUT_FOLDER = '/Users/saaijeeshsn/Documents/bookstore_local/CU-BookStore-Work-Scheduling/00_Input/'
OUTPUT_FOLDER = '/Users/saaijeeshsn/Documents/bookstore_local/CU-BookStore-Work-Scheduling/01_Output/'

# Route to render the upload form
@app.route('/')
def home():
    return render_template('upload_form.html')  # Render the HTML form for uploads

# File upload route
@app.route('/upload-files', methods=['POST'])
def upload_files():
    # Check if both required files are present in the request
    if 'daily_employee_files' not in request.files or 'daily_shift_files' not in request.files:
        return jsonify({"error": "Both 'Employee Availability' and 'Shift Requirements' files are required."}), 400

    # Retrieve files
    employee_availability_file = request.files['daily_employee_files']
    shift_requirements_file = request.files['daily_shift_files']

    # Save files locally
    try:
        emp_file_path = os.path.join(INPUT_FOLDER, secure_filename('01_Emp_Availability_Initial.xlsx'))
        shift_file_path = os.path.join(INPUT_FOLDER, secure_filename('02_Emp_Count_Requirement.xlsx'))

        employee_availability_file.save(emp_file_path)
        shift_requirements_file.save(shift_file_path)

        print(f"Files saved successfully: {emp_file_path}, {shift_file_path}")
    except Exception as e:
        return jsonify({"error": f"Error saving files: {e}"}), 500

    # Trigger the `test.py` script for processing
    try:
        subprocess.run(['python', '/Users/saaijeeshsn/Documents/bookstore_local/CU-BookStore-Work-Scheduling/Code/test.py'], check=True) ##TODO
        print("Processing script executed successfully.")
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Error running processing script: {e}"}), 500

    # Redirect to the results page after processing is complete
    return redirect(url_for('display_results'))

# Route to display results as tables
@app.route('/results')
def display_results():
    try:
        # Paths to the output files
        final_allocation_path = os.path.join(OUTPUT_FOLDER, 'Final_Allocation.xlsx')
        emp_view_path = os.path.join(OUTPUT_FOLDER, 'Final_Allocation_Emp_View.xlsx')

        # Verify files exist
        if not os.path.exists(final_allocation_path) or not os.path.exists(emp_view_path):
            return jsonify({"error": "Output files not found. Please ensure processing completed successfully."}), 404

        # Read Excel files into Pandas DataFrames
        final_allocation_df = pd.read_excel(final_allocation_path)
        emp_view_df = pd.read_excel(emp_view_path)

        # Debugging: Print first few rows of DataFrames
        print("Final Allocation DataFrame:")
        print(final_allocation_df.head())
        print("Employee View DataFrame:")
        print(emp_view_df.head())

        # Render results in a template
        return render_template(
            'results.html',
            final_allocation=final_allocation_df.to_html(classes='table table-striped', index=False),
            emp_view=emp_view_df.to_html(classes='table table-striped', index=False),
            final_allocation_file='Final_Allocation.xlsx',
            emp_view_file='Final_Allocation_Emp_View.xlsx'
        )
    except Exception as e:
        return jsonify({"error": f"Error displaying results: {e}"}), 500


# Route to download an individual file
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found."}), 404

        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Error downloading file: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
