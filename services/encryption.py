import boto3
import base64

kms_client = boto3.client('kms')

def decrypt_jwt_secret(encrypted_key):
    response = kms_client.decrypt(
        CiphertextBlob=base64.b64decode(encrypted_key)
    )
    return response['Plaintext'].decode('utf-8')