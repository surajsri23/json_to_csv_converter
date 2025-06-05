from flask import Flask, render_template_string, request, send_file
import json
import csv
import io
import os

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>JSON &lt;-&gt; CSV Converter</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- Bootstrap CSS & Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { background: #f8fafc; }
        .converter-card { max-width: 500px; margin: 40px auto; }
        .toggle-btn { float: right; }
        .icon-btn { border: none; background: none; }
        textarea { resize: vertical; }
    </style>
</head>
<body>
<div class="container">
    <div class="card shadow converter-card">
        <div class="card-header bg-primary text-white d-flex align-items-center justify-content-between">
            <span><i class="bi bi-arrow-left-right"></i> {{ mode_label }} Converter</span>
            <button type="button" class="btn btn-light btn-sm toggle-btn" onclick="toggleMode()">
                <i class="bi bi-arrow-repeat"></i>
                Switch to {{ 'CSV to JSON' if mode == 'json2csv' else 'JSON to CSV' }}
            </button>
        </div>
        <div class="card-body">
            <form method="post" enctype="multipart/form-data">
                <input type="hidden" name="mode" id="mode" value="{{ mode }}">
                <div class="mb-3">
                    <label class="form-label"><i class="bi bi-upload"></i> Upload {{ 'JSON' if mode == 'json2csv' else 'CSV' }} File</label>
                    <input type="file" class="form-control" name="data_file" accept="{{ '.json' if mode == 'json2csv' else '.csv' }}">
                </div>
                <div class="mb-3">
                    <label class="form-label"><i class="bi bi-clipboard"></i> Or paste {{ 'JSON' if mode == 'json2csv' else 'CSV' }} here:</label>
                    <textarea name="data_text" class="form-control" rows="8" placeholder="Paste your data here..."></textarea>
                </div>
                <button type="submit" class="btn btn-success w-100">
                    <i class="bi bi-arrow-right-circle"></i> Convert
                </button>
            </form>
            {% if result_ready %}
                <div class="mt-4 text-center">
                    <a href="{{ url_for('download_result') }}" class="btn btn-outline-primary">
                        <i class="bi bi-download"></i> Download {{ 'CSV' if mode == 'json2csv' else 'JSON' }}
                    </a>
                </div>
            {% endif %}
            {% if error %}
                <div class="alert alert-danger mt-3" role="alert">
                    <i class="bi bi-exclamation-triangle"></i> {{ error }}
                </div>
            {% endif %}
        </div>
    </div>
</div>
<script>
function toggleMode() {
    var modeInput = document.getElementById('mode');
    modeInput.value = modeInput.value === 'json2csv' ? 'csv2json' : 'json2csv';
    document.forms[0].submit();
}
</script>
</body>
</html>
"""

result_buffer = io.StringIO()
result_mimetype = 'text/csv'
result_filename = 'converted.csv'

def csv_to_json(csv_content):
    csv_content = csv_content.strip()
    reader = csv.DictReader(io.StringIO(csv_content))
    return list(reader)

@app.route('/', methods=['GET', 'POST'])
def index():
    global result_buffer, result_mimetype, result_filename
    error = None
    result_ready = False
    mode = request.form.get('mode', 'json2csv')
    mode_label = "JSON to CSV" if mode == 'json2csv' else "CSV to JSON"

    if request.method == 'POST':
        file = request.files.get('data_file')
        data_text = request.form.get('data_text', '').strip()
        data = None

        if mode == 'json2csv':
            if file and file.filename.endswith('.json'):
                try:
                    data = json.load(file)
                except Exception as e:
                    error = f"Error loading file: {str(e)}"
            elif data_text:
                try:
                    data = json.loads(data_text)
                except Exception as e:
                    error = f"Error parsing pasted JSON: {str(e)}"
            else:
                error = "Please upload a JSON file or paste JSON data."
            if data is not None and not error:
                try:
                    if isinstance(data, dict):
                        data = [data]
                    if not isinstance(data, list):
                        raise ValueError("JSON must be an object or array of objects.")
                    result_buffer = io.StringIO()
                    writer = csv.DictWriter(result_buffer, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                    result_buffer.seek(0)
                    result_mimetype = 'text/csv'
                    result_filename = 'converted.csv'
                    result_ready = True
                except Exception as e:
                    error = f"Error converting to CSV: {str(e)}"
        else:
            if file and file.filename.endswith('.csv'):
                try:
                    csv_content = file.read().decode('utf-8')
                    data = csv_to_json(csv_content)
                except Exception as e:
                    error = f"Error loading file: {str(e)}"
            elif data_text:
                try:
                    data = csv_to_json(data_text)
                except Exception as e:
                    error = f"Error parsing pasted CSV: {str(e)}"
            else:
                error = "Please upload a CSV file or paste CSV data."
            if data is not None and not error:
                try:
                    result_buffer = io.StringIO()
                    json.dump(data, result_buffer, indent=2)
                    result_buffer.seek(0)
                    result_mimetype = 'application/json'
                    result_filename = 'converted.json'
                    result_ready = True
                except Exception as e:
                    error = f"Error converting to JSON: {str(e)}"

    return render_template_string(
        HTML,
        mode=mode,
        mode_label=mode_label,
        result_ready=result_ready,
        error=error
    )

@app.route('/download')
def download_result():
    global result_buffer, result_mimetype, result_filename
    result_buffer.seek(0)
    return send_file(
        io.BytesIO(result_buffer.getvalue().encode()),
        mimetype=result_mimetype,
        as_attachment=True,
        download_name=result_filename
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
