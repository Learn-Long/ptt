import os
import json
import threading
from flask import Flask, render_template, jsonify

app = Flask(__name__)

JSON_REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hyperlink_spam_report.json')
file_lock = threading.Lock()


@app.route('/')
def index():
    return render_template('report.html')


@app.route('/api/report')
def api_report():
    try:
        with file_lock:
            with open(JSON_REPORT_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({'error': 'Report file not found. Run hyperlink_spam_detector.py first.'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in report file.'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
