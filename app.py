from flask import Flask, request, jsonify, render_template
from pan_json import PANProcessor
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
processor = PANProcessor()

# Create directories on startup
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process_pan():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    try:
        # Generate timestamped filename
        original_name = os.path.splitext(file.filename)[0]
        extension = os.path.splitext(file.filename)[1]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{original_name}_{timestamp}{extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        
        # Process image
        data, missing = processor.process_image(filepath)
        
        if missing:
            return jsonify({
                'status': 'error',
                'message': f"Missing fields: {', '.join(missing)}",
                'missing_fields': missing
            }), 400
            
        # Save JSON output
        json_filename = f"{original_name}_{timestamp}.json"
        saved_json_path = processor.save_to_json(data, json_filename)
        
        return jsonify({
            'status': 'success',
            'data': data,
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)