from pymongo import MongoClient

client = MongoClient('mongodb+srv://waldowalerian:b6f75HOXIxPwOkEw@cluster0.n8eh7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client.get_database('dfs_project')
print(db.list_collection_names()) 