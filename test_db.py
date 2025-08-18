from pymongo import MongoClient
from bson import ObjectId
import os

client = MongoClient(os.getenv("MONGO_URI"))
target = ObjectId("68a32dfdd8918d5c896476d6")   # replace with your file id
found = False
for dbname in client.list_database_names():
    if dbname in ("admin","local","config"): continue
    doc = client[dbname].files.find_one({"_id": target})
    if doc:
        print("Found in DB:", dbname)
        print("status:", doc.get("status"))
        print("upload_time:", doc.get("upload_time"))
        print("filename:", doc.get("filename"))
        found = True
        break
if not found:
    print("Not found by _id in any DB accessible with the URI.")