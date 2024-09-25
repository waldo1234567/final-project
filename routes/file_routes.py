from flask import Blueprint, request, jsonify
from services import s3_services
from models.file import create_file_entry, get_file_entry, get_all_files, delete_file_entry,get_file_entry_for_deletion,split_file_into_chunks,reconstruct_file
import os
from werkzeug.utils import secure_filename
from flask import send_file

file_bp = Blueprint('file_bp', __name__)

@file_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message' : 'No selected file'}),400
    filename = secure_filename(file.filename)
    
    chunks_url = s3_services.upload_chunks_to_s3(file, filename)

    if not chunks_url:
        return jsonify({'message': 'failed to upload file!'}),500
    
    file_id = create_file_entry(file.filename, chunks_url,file)
    return jsonify({'message': 'file uploaded successfully!', 'file_id': file_id}),201

@file_bp.route('/files',methods=['GET'])
def list_files():
    files = get_all_files()
    return jsonify(files),200

@file_bp.route('/files/<file_id>',methods=['GET'])
def get_file(file_id):
    user_region = request.args.get('region')
    file_url = get_file_entry(file_id, user_region)

    
    if not file_url:
        return jsonify({'message': 'file not found !'}),404
   
    return jsonify({'url' : file_url}),200

@file_bp.route('/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    file_entry = get_file_entry_for_deletion(file_id)
    if not file_entry:
        return jsonify({'message' : 'File not found !'}),404
    if s3_services.delete_file_from_s3(file_entry['filename'],file_entry['urls']):
        delete_result = delete_file_entry(file_id)
        if delete_result.deleted_count > 0:  # Check if the delete operation affected any document
            return jsonify({'message': 'File deleted successfully'}), 200
        else:
            return jsonify({'message': 'Failed to delete file from MongoDB'}), 500
    return jsonify({'message': 'Failed to delete file from S3'}), 500

@file_bp.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    user_region = request.args.get('region', 'us-east-1')

    file_entry = get_file_entry(file_id,user_region)

    if not file_entry:
        return jsonify({'message' : 'File not found!'}),404
    
    print('file entry:' ,file_entry)
    print('Type of file_entry:', type(file_entry))
    urls = file_entry.get('urls',[])
    if not urls:
        return jsonify({'message': 'No URLs found for this file!'}), 404
    
    chunks = s3_services.download_chunks_from_s3(urls)

    if chunks:
        reconstructed_file = reconstruct_file(chunks)

        return send_file(reconstructed_file, download_name=file_entry['filename'],as_attachment=True)
    
    else:
        return jsonify({'message' : 'Failed to download file from s3'}),500