import time
from bson.objectid import ObjectId
from datetime import datetime,timezone
from config import KMS_CLIENT, KMS_KEY_ID,mongo,Config
from datetime import datetime, timezone
import os
import io
import gzip
import hashlib
import zfec
from utils.metrics import RECONSTRUCT_LATENCY
from pymongo import MongoClient

_client = None

def get_mongo_client():
    global _client
    if _client is None:
        _client = MongoClient(Config.MONGO_URI)
    return _client

def serialize_files(file):
    return{
        '_id': str(file['_id']),
        'filename': file['filename'],
        'urls': file['urls'],
        'upload_time': file['upload_time'],
        'size': file['size']
    }

def calculate_k_and_m(file_size , base_k = 6, base_m = 3):
    if file_size < 10 * 1024 * 1024:
        k = base_k
        m = base_m
    elif file_size < 100 * 1024 * 1024:
        k = base_k + 2
        m = base_m + 2
    else:
        k = base_k + 4
        m = base_m + 4
    
    return k , m

    
def get_files_collection():
    client = get_mongo_client()
    db = client["dfs_project"]
    return db["files"]

def create_file_entry(filename,chunk_urls,file):
    resp = KMS_CLIENT.generate_data_key(KeyId=KMS_KEY_ID, KeySpec="AES_256")
    plaintext_key = resp["Plaintext"]           # bytes, 32-byte key
    encrypted_data_key = resp["CiphertextBlob"]  # bytes, encrypted key
    
    
    files_collection = get_files_collection()

    file_size = file.seek(0, os.SEEK_END)
    file.seek(0)
    
    file_entry = {
        'filename': filename,
        'urls': chunk_urls, 
        'upload_time': datetime.now(timezone.utc),
        'size': file_size,
        "encrypted_data_key": encrypted_data_key,
    }
    result = files_collection.insert_one(file_entry)
    return str(result.inserted_id), plaintext_key


def create_file_entry_preupload(filename: str, file_size: int):
    # Generate data key from KMS
    resp = KMS_CLIENT.generate_data_key(KeyId=KMS_KEY_ID, KeySpec="AES_256")
    plaintext_key = resp["Plaintext"]           # bytes, in-memory only
    encrypted_data_key = resp["CiphertextBlob"] # bytes to store

    files_collection = get_files_collection()

    file_entry = {
        'filename': filename,
        'urls': [], 
        'upload_time': datetime.now(timezone.utc),
        'size': file_size,
        'encrypted_data_key': encrypted_data_key,
        'status': 'uploading'
    }
    result = files_collection.insert_one(file_entry)
    return str(result.inserted_id), plaintext_key

def update_file_urls_and_mark_available(file_id: str, chunk_urls: list):
    files_collection = get_files_collection()
    return files_collection.update_one(
        {'_id': ObjectId(file_id)},
        {'$set': {'urls': chunk_urls, 'status': 'available', 'upload_time': datetime.now(timezone.utc)}}
    )

def mark_file_as_failed(file_id: str, reason: str = None):
    files_collection = get_files_collection()
    update = {'$set': {'status': 'failed'}}
    if reason:
        update['$set']['failure_reason'] = reason
    files_collection.update_one({'_id': ObjectId(file_id)}, update)

def get_file_entry(file_id,user_region):
    files_collection = get_files_collection()
    file_entry = files_collection.find_one({'_id': ObjectId(file_id)})
    if not file_entry:
        return None
    urls = file_entry.get('urls', [])
    
    relevant_url = None
    
    for url_info in urls:
        if url_info['region'] == user_region:
            relevant_url= url_info['url']
            break
    if not relevant_url and urls:
        relevant_url = urls[0]['url']

    return file_entry

def get_all_files():
    files_collecion = get_files_collection()
    files = list(files_collecion.find())
    return [serialize_files(file) for file in files]

def delete_file_entry(file_id):
    files_collection = get_files_collection()
    result = files_collection.delete_one({'_id': ObjectId(file_id)})
    return result

def get_file_entry_for_deletion(file_id):
    files_collection = get_files_collection()
    file_entry = files_collection.find_one({'_id' : ObjectId(file_id)})
    return file_entry



def split_file_into_chunks(file):
    file.seek(0)
    file_data = file.read()

    k, m = calculate_k_and_m(len(file_data))

    chunk_size = len(file_data) // k
    padding_size = (k - (len(file_data) % k)) % k
    file_data += b'\x00' * padding_size

    # Make raw k chunks (bytes)
    chunks = [file_data[i * chunk_size:(i + 1) * chunk_size] for i in range(k)]

    enc = zfec.Encoder(k, k + m)
    encoded_chunks = enc.encode(chunks)

    # Convert each shard (list of ints) into bytes
    encoded_chunks_bytes = [bytes(c) for c in encoded_chunks]

    return encoded_chunks_bytes, k, m, padding_size

def reconstruct_file(chunks):
    try:
        
        reconstructed_file = io.BytesIO()

        for chunk in chunks:
            if chunk is not None:
                reconstructed_file.write(chunk)
            else:
                print("One of the chunks is None !!!!!!")
        reconstructed_file.seek(0)
        return reconstructed_file
    except Exception as e:
        print(f"Error reconstructing file: {e}")
        return None

def reconstruct_missing_chunks(valid_chunks, chunk_indices, k , total_chunks):
    start = time.time()
    decoder = zfec.Decoder(k ,total_chunks)

    if len(valid_chunks) < k :
        print("Not enough Chunks to Reconstruct file")
        return None
    
    valid_chunks_k = valid_chunks[:k]
    chunk_indices_k = chunk_indices[:k]
    
    recovered_chunks = decoder.decode(valid_chunks_k , chunk_indices_k)
    RECONSTRUCT_LATENCY.observe(time.time() - start)
    return recovered_chunks 

def compress_chunk(chunk):
    compressed_chunk = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed_chunk, mode='wb') as gz:
        if not isinstance(chunk, bytes):
            chunk = chunk.encode()
        gz.write(chunk)
    return compressed_chunk.getvalue()

def decompress_chunk(compressed_data):
    try:
        decompressed_chunk = io.BytesIO()
        with gzip.GzipFile(fileobj=io.BytesIO(compressed_data), mode='rb') as gz:
            decompressed_chunk.write(gz.read())
        return decompressed_chunk.getvalue()
    except Exception as e:
        print(f"Decompression error : {e}")
        return None

def generate_md5(chunk):
    md5_hash = hashlib.md5()
    md5_hash.update(chunk)
    return md5_hash.hexdigest()

def verify_md5(chunk,original_md5):
    md5_hash = hashlib.md5()
    md5_hash.update(chunk)
    return md5_hash.hexdigest() == original_md5