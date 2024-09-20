from flask import Blueprint, request, jsonify
from services import s3_services
from models.file import create_file_entry, get_file_entry, get_all_files, delete_file_entry

file_bp = Blueprint('file_bp', __name__)

@file_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message' : 'No selected file'}),400
    
    url = s3_services.upload_files_to_s3(file,file.filename)
    if not url:
        return jsonify({'message': 'failed to upload file!'}),500
    
    file_id = create_file_entry(file.filename, url)
    return jsonify({'message': 'file uploaded successfully!', 'file_id': file_id}),201

@file_bp.route('/files',methods=['GET'])
def list_files():
    files = get_all_files()
    return jsonify(files),200

@file_bp.route('/files/<file_id>',methods=['GET'])
def get_file(file_id):
    file_entry = get_file_entry(file_id)
    if not file_entry:
        return jsonify({'message': 'file not found !'}),404
    return jsonify(file_entry),200

@file_bp.route('/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    file_entry = get_file_entry(file_id)
    if not file_entry:
        return jsonify({'message' : 'File not found !'}),404
    if s3_services.delete_file_from_s3(file_entry['filename']):
        delete_file_entry(file_id)
        return jsonify({'message': 'File deleted successfully'}),200
    return jsonify({'message': 'Failed to delete file from S3'}), 500