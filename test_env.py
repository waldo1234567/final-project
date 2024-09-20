import os

print("ENCRYPTED_JWT_SECRET_KEY:", os.getenv('ENCRYPTED_JWT_SECRET_KEY'))
print("AWS_SECRET_KEY:", os.getenv('AWS_ACCESS_KEY_ID'))
print("AWS_ACCESS_KEY:", os.getenv('AWS_SECRET_ACCESS_KEY'))
print("MONGO_URI: ",os.getenv('MONGO_URI'))