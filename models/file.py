from bson.objectid import ObjectId
from datetime import datetime,timezone
from config import mongo,Config
import os
import io


def serialize_files(file):
    return{
        '_id': str(file['_id']),
        'filename': file['filename'],
        'urls': file['urls'],
        'upload_time': file['upload_time'],
        'size': file['size']
    }


def get_files_collection():
    
    return mongo.db.files

def create_file_entry(filename,chunk_urls,file):
    files_collection = get_files_collection()

    file_size = file.seek(0, os.SEEK_END)
    file.seek(0)

    file_entry = {
        'filename': filename,
        'urls': chunk_urls,  # List of URLs with region info
        'upload_time': datetime.now(timezone.utc),
        'size': file_size  # Optionally store the file size
    }
    result = files_collection.insert_one(file_entry)
    return str(result.inserted_id)

def get_file_entry(file_id,user_region):
    files_collection = get_files_collection()
    file_entry = files_collection.find_one({'_id': ObjectId(file_id)})
    if not file_entry:
        return None
    urls = file_entry.get('urls', [])
    

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
    file_chunks = []
    file.seek(0)

    while True:
        chunk = file.read(Config.CHUNK_SIZE)
        if not chunk:
            break
        file_chunks.append(chunk)

        file.seek(0)

        return file_chunks
    
def reconstruct_file(chunks):
    reconstructed_file = io.BytesIO()

    for chunk in chunks:
        reconstructed_file.write(chunk)

    reconstructed_file.seek(0)
    return reconstructed_file