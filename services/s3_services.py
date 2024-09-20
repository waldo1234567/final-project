import boto3
from config import Config
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

s3_client = boto3.client('s3', region_name=Config.S3_REGION,
                         aws_access_key_id = Config.AWS_ACCESS_KEY,
                         aws_secret_access_key = Config.AWS_SECRET_ACCESS)

def upload_files_to_s3(file,filename):
    try:
        s3_client.upload_fileobj(file,Config.S3_BUCKET_NAME,filename)
        url = f"https://{Config.S3_BUCKET_NAME}.s3.{Config.S3_REGION}.amazonaws.com/{filename}"
        return url
    except FileNotFoundError:
        print(f"Error: The file was not found: {filename}")
        return None
    except NoCredentialsError:
        print("Error: AWS credentials not found.")
        return None
    except PartialCredentialsError:
        print("Error: Incomplete AWS credentials.")
        return None
    except ClientError as e:
        # Catch all client errors and log the response
        print(f"Error uploading file to S3: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        # Catch any other exceptions
        print(f"An unexpected error occurred: {e}")
        return None
    
def delete_file_from_s3(filename):
    try:
        s3_client.delete_object(Bucket = Config.S3_BUCKET_NAME, Key = filename)
        return True
    except Exception as e:
        print(f"Error deleting file from S3: {e}")
        return False