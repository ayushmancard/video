from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename
import os
import uuid
import threading
from datetime import datetime

video_bp = Blueprint('video', __name__)

# Configuration
UPLOAD_FOLDER = '/tmp/video_uploads'
PROCESSED_FOLDER = '/tmp/video_processed'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# In-memory storage for processing status
processing_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@video_bp.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not supported'}), 400
    
    # Generate unique ID for this upload
    upload_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    file_extension = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{upload_id}.{file_extension}"
    
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(filepath)
    
    # Initialize processing status
    processing_status[upload_id] = {
        'status': 'uploaded',
        'progress': 0,
        'message': 'File uploaded successfully',
        'original_filename': filename,
        'upload_time': datetime.now().isoformat()
    }
    
    return jsonify({
        'upload_id': upload_id,
        'filename': filename,
        'message': 'File uploaded successfully'
    }), 200

@video_bp.route('/process/<upload_id>', methods=['POST'])
def process_video(upload_id):
    if upload_id not in processing_status:
        return jsonify({'error': 'Upload ID not found'}), 404
    
    if processing_status[upload_id]['status'] == 'processing':
        return jsonify({'error': 'Video is already being processed'}), 400
    
    # Get processing options from request
    data = request.json or {}
    options = {
        'scale': data.get('scale', 2),  # 2x upscaling by default
        'denoise': data.get('denoise', True),
        'sharpen': data.get('sharpen', True),
        'enhance_colors': data.get('enhance_colors', True)
    }
    
    # Start processing in background thread
    thread = threading.Thread(target=process_video_background, args=(upload_id, options))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': 'Processing started',
        'upload_id': upload_id,
        'options': options
    }), 200

@video_bp.route('/status/<upload_id>', methods=['GET'])
def get_status(upload_id):
    if upload_id not in processing_status:
        return jsonify({'error': 'Upload ID not found'}), 404
    
    return jsonify(processing_status[upload_id]), 200

@video_bp.route('/download/<upload_id>', methods=['GET'])
def download_video(upload_id):
    if upload_id not in processing_status:
        return jsonify({'error': 'Upload ID not found'}), 404
    
    status = processing_status[upload_id]
    if status['status'] != 'completed':
        return jsonify({'error': 'Video processing not completed'}), 400
    
    processed_file = os.path.join(PROCESSED_FOLDER, f"{upload_id}_enhanced.mp4")
    if not os.path.exists(processed_file):
        return jsonify({'error': 'Processed file not found'}), 404
    
    return send_file(
        processed_file,
        as_attachment=True,
        download_name=f"enhanced_{status['original_filename']}"
    )

def process_video_background(upload_id, options):
    """Background function to process video"""
    try:
        processing_status[upload_id]['status'] = 'processing'
        processing_status[upload_id]['progress'] = 10
        processing_status[upload_id]['message'] = 'Starting video processing...'
        
        # Get input file
        input_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(upload_id)]
        if not input_files:
            raise Exception('Input file not found')
        
        input_file = os.path.join(UPLOAD_FOLDER, input_files[0])
        output_file = os.path.join(PROCESSED_FOLDER, f"{upload_id}_enhanced.mp4")
        
        # Update progress
        processing_status[upload_id]['progress'] = 30
        processing_status[upload_id]['message'] = 'Analyzing video...'
        
        # Import video processing function
        from src.utils.video_processor import enhance_video
        
        # Process the video
        processing_status[upload_id]['progress'] = 50
        processing_status[upload_id]['message'] = 'Enhancing video quality...'
        
        enhance_video(input_file, output_file, options, upload_id, processing_status)
        
        # Complete
        processing_status[upload_id]['status'] = 'completed'
        processing_status[upload_id]['progress'] = 100
        processing_status[upload_id]['message'] = 'Video processing completed successfully'
        processing_status[upload_id]['completion_time'] = datetime.now().isoformat()
        
    except Exception as e:
        processing_status[upload_id]['status'] = 'error'
        processing_status[upload_id]['message'] = f'Error processing video: {str(e)}'
        processing_status[upload_id]['error_time'] = datetime.now().isoformat()

@video_bp.route('/cleanup/<upload_id>', methods=['DELETE'])
def cleanup_files(upload_id):
    """Clean up uploaded and processed files"""
    if upload_id not in processing_status:
        return jsonify({'error': 'Upload ID not found'}), 404
    
    # Remove files
    for folder in [UPLOAD_FOLDER, PROCESSED_FOLDER]:
        for filename in os.listdir(folder):
            if filename.startswith(upload_id):
                try:
                    os.remove(os.path.join(folder, filename))
                except OSError:
                    pass
    
    # Remove from status
    del processing_status[upload_id]
    
    return jsonify({'message': 'Files cleaned up successfully'}), 200

