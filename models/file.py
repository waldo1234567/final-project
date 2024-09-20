import os
from bson.objectid import ObjectId
from datetime import datetime,timezone
from config import mongo

# def save_file(file):
#     filename = file.filename
#     filename = secure_filename(filename)

#     file_url = upload_files_to_s3(file,filename)

#     if(file_url) :
#         return {'message': 'File uploaded successfully!', 'file_url': file_url}, 201
#     else:
#         return {'message': 'File upload failed.'}, 400
def serialize_files(file):
    return{
        '_id': str(file['_id']),
        'filename': file['filename'],
        'url': file['url']
    }


def get_files_collection():
    
    return mongo.db.files

def create_file_entry(filename,urls):
    files_collection = get_files_collection()
    file_entry = {
        'filename': filename,
        'urls': urls,  # List of URLs with region info
        'upload_time': datetime.now(timezone.utc),
        'size': sum(file.getbuffer().nbytes for url in urls),  # Optionally store the file size
    }
    result = files_collection.insert_one(file_entry)
    return str(result.inserted_id)

def get_file_entry(file_id):
    files_collection = get_files_collection()
    file = files_collection.find_one({'_id': ObjectId(file_id)})
    if file :
        return serialize_files(file)
    return None

def get_all_files():
    files_collecion = get_files_collection()
    files = list(files_collecion.find())
    return [serialize_files(file) for file in files]

def delete_file_entry(file_id):
    files_collection = get_files_collection()
    return files_collection.delete_one({'_id': file_id})