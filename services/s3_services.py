import boto3
from config import Config
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
import io
import requests

s3_clients ={
    'us-east-1' : boto3.client('s3', region_name='us-east-1',
                         aws_access_key_id = Config.AWS_ACCESS_KEY,
                         aws_secret_access_key = Config.AWS_SECRET_ACCESS),
    'us-west-1' : boto3.client('s3', region_name='us-west-1',
                         aws_access_key_id = Config.AWS_ACCESS_KEY,
                         aws_secret_access_key = Config.AWS_SECRET_ACCESS),
    'ap-southeast-1' : boto3.client('s3', region_name='ap-southeast-1',
                         aws_access_key_id = Config.AWS_ACCESS_KEY,
                         aws_secret_access_key = Config.AWS_SECRET_ACCESS)

} 

def upload_files_to_s3(file,filename):
    urls=[]
    try:

        file_data = file.read()

        for region, bucket_name in zip(s3_clients.keys(), Config.S3_BUCKET_NAME.values()):
            # Use pre-initialized S3 client for the specific region
            s3_client = s3_clients[region]
            
            file_copy = io.BytesIO(file_data)

            # Upload file to the respective bucket
            s3_client.upload_fileobj(file_copy, bucket_name, filename)

            # Generate the file URL for the region and bucket
            url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{filename}"
            urls.append({'url': url, 'region': region})

        return urls
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
    
def delete_file_from_s3(filename,urls):
    try:
        for url_info in urls:
            region = url_info['region']
            client = s3_clients[region]
            bucket_name = Config.S3_BUCKET_NAME[region]
            client.delete_object(Bucket = bucket_name, Key = filename)
        return True
    except Exception as e:
        print(f"Error deleting file from S3: {e}")
        return False
    
def upload_chunks_to_s3(file, filename):
    file.seek(0)  # Ensure the file pointer is at the start
    urls = []

    # Read the file in chunks and upload
    chunk_number = 1
    while True:
        chunk = file.read(Config.CHUNK_SIZE)
        if not chunk:
            break  # End of file

        for region, s3_client in s3_clients.items():
            try:
                chunk_file = io.BytesIO(chunk)  # Create an in-memory file for this chunk
                chunk_filename = f"{filename}_chunk_{chunk_number}"
                bucket_name = Config.S3_BUCKET_NAME[region]

                # Upload the chunk to the specific S3 bucket
                s3_client.upload_fileobj(chunk_file, bucket_name, chunk_filename)

                # Generate the URL for this chunk in the current region
                url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{chunk_filename}"
                urls.append({'url': url, 'region': region, 'chunk_number': chunk_number})

            except Exception as e:
                print(f"Error uploading chunk {chunk_number} to S3 in region {region}: {str(e)}")
                return None

            chunk_number += 1  # Move to the next chunk

    return urls

def download_chunks_from_s3(chunk_urls):
    chunks = []
    errors = []  # List to keep track of failed URLs

    for chunk_info in chunk_urls:
        try:
            region = chunk_info['region']
            url = chunk_info['url']
            bucket = url.split('.')[0].split('//')[1] 
            key = url.split('/')[-1]

            s3_client = boto3.client('s3', region_name=region)
            
            response = s3_client.get_object(Bucket=bucket, Key=key)
            chunk_data = response['Body'].read()

            chunks.append(chunk_data)
        except Exception as e:
            error_message = f"Error downloading chunk from {chunk_info['url']}: {e}"
            print(error_message)
            errors.append(error_message)

    if errors:
        print("Errors encountered during download:")
        for error in errors:
            print(error)
    
    return chunks if chunks else None
