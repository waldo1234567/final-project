from flask import Blueprint, request, jsonify
from config import HOT_THRESHOLD
from services import s3_services
from models.file import create_file_entry, get_file_entry, get_all_files, delete_file_entry,get_file_entry_for_deletion,reconstruct_file
from werkzeug.utils import secure_filename
from flask import send_file
from utils.pdf_utils import generate_pdf_from_content
from utils.metrics import UPLOAD_THROUGHPUT
from services.cache_services import (
    increment_download_count,
    get_cached_chunk_urls,
    cache_chunk_urls,
    increment_cache_hit,
    increment_cache_miss,
)
from services.region_selector import detect_user_region
from config import KMS_CLIENT
from services.crypto_service import decrypt_chunk
import gzip
import os
from models.file import create_file_entry_preupload, mark_file_as_failed, update_file_urls_and_mark_available

file_bp = Blueprint('file_bp', __name__)

@file_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message' : 'No selected file'}),400
    filename = secure_filename(file.filename)
    
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    file_id, plaintext_key = create_file_entry_preupload(filename, file_size)
    
    uploaded_urls = []
    try:
        file.seek(0)
        uploaded_urls = s3_services.upload_chunks_to_s3(file, filename, data_key=plaintext_key, file_id=file_id)

        if not uploaded_urls:
            # upload failed or returned no urls
            # clean up partial upload and mark failed
            s3_services.delete_s3_objects(uploaded_urls)
            mark_file_as_failed(file_id, reason="no chunks uploaded")
            return jsonify({'message': 'failed to upload file!'}), 500

        # 3) finalize metadata: store urls and mark available
        update_file_urls_and_mark_available(file_id, uploaded_urls)

        return jsonify({'message': 'file uploaded successfully!', 'file_id': file_id}), 201

    except Exception as e:
        # cleanup partial uploads
        try:
            s3_services.delete_s3_objects(uploaded_urls)
        except Exception as cleanup_err:
            print("Cleanup error:", cleanup_err)

        mark_file_as_failed(file_id, reason=str(e))
        print("Upload exception:", e)
        return jsonify({'message': 'failed to upload file!'}), 500

    finally:
        # best-effort zero-out plaintext key
        try:
            plaintext_key = b'\x00' * len(plaintext_key)
        except Exception:
            pass
        finally:
            try:
                del plaintext_key
            except Exception:
                pass


@file_bp.route('/upload-editor-file', methods=['POST'])
def upload_editor_file():
    try:
        editor_content = request.json.get('content')
        filename = request.json.get('filename' , 'document_from_editor.pdf')

        if not editor_content:
            return jsonify({'error' : 'content is required'}),400
        
        pdf_buffer = generate_pdf_from_content(editor_content)
        
        chunks_url = s3_services.upload_editor_generated_file(pdf_buffer, filename)
        
        if not chunks_url:
            return jsonify({'message': 'failed to upload file!'}),500

        file_id = create_file_entry(filename , chunks_url , pdf_buffer)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'file_id': file_id,
            'urls': chunks_url
        }), 200  
        
    except Exception as e:
        return jsonify({'error': str(e)}),500
    
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
    user_region = request.args.get('region')
    if not user_region:
        user_region = detect_user_region()

    file_entry = get_file_entry(file_id, user_region)
    encrypted_data_key = file_entry["encrypted_data_key"]
    
    dk_resp = KMS_CLIENT.decrypt(CiphertextBlob=encrypted_data_key)
    data_key = dk_resp["Plaintext"]
    if not file_entry:
        return jsonify({'message': 'File not found!'}), 404
    
    count = increment_download_count(file_id, user_region)
    
    chunk_urls = None
    cache_hit = False
    if count >= HOT_THRESHOLD:
        chunk_urls = get_cached_chunk_urls(file_id, user_region)
        if chunk_urls:
            cache_hit = True
            
    if cache_hit:
        increment_cache_hit(file_id, user_region)
    else:
        increment_cache_miss(file_id, user_region)
    
    if not chunk_urls:
        chunk_urls = sorted(file_entry['urls'], key=lambda x: x['chunk_number'])

        if count >= HOT_THRESHOLD:
            cache_chunk_urls(file_id, user_region, chunk_urls)
        
    print('file entry:' ,file_entry)
    print('Type of file_entry:', type(file_entry))
    
    chunks, content_type = s3_services.download_chunks_from_s3(chunk_urls)
    if chunks is None:
        return jsonify({'message': 'Failed to reconstruct file: not enough valid chunks.'}), 500
    decrypted_chunks = []
    for comp in chunks:
        encrypted = gzip.decompress(comp)
        pt = decrypt_chunk(encrypted, data_key)
        decrypted_chunks.append(pt)
    
    if not chunks:
        return jsonify({'message': 'Failed to download file from s3'}), 500
    
    if chunks:
        reconstructed_file = reconstruct_file(decrypted_chunks)

        resp = send_file(
            reconstructed_file, 
            download_name=file_entry['filename'],
            as_attachment=True,
            mimetype=content_type or 'application/octet-stream'
                   )
        resp.headers['X-Chunk-URL-Cache'] = 'HIT' if cache_hit else 'MISS'
        return resp
    else:
        return jsonify({'message' : 'Failed to download file from s3'}),500
    
@file_bp.route("/metrics-test")
def metrics_test():
    UPLOAD_THROUGHPUT.labels(region="canary").set(42)
    return "OK"