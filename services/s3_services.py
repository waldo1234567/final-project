import boto3
from config import Config
import io
import time
import concurrent.futures
from threading import Thread
from models.file import compress_chunk,decompress_chunk,verify_md5,generate_md5


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

bucket_health = {region: True for region in Config.S3_BUCKET_NAME}

    
def delete_file_from_s3(filename,urls):
    try:
        for url_info in urls:
            region = url_info['region']
            client = s3_clients[region]
            bucket_name = Config.S3_BUCKET_NAME[region]
            
            chunk_filename = url_info['url'].split('/')[-1]
            
            client.delete_object(Bucket = bucket_name, Key = chunk_filename)
            
            print(f"Deleted {chunk_filename} from {bucket_name} in region {region}.")
        return True
    except Exception as e:
        print(f"Error deleting file from S3: {e}")
        return False
    
def upload_chunks_to_s3(file, filename):
    file.seek(0)  
    urls = []
    chunk_number = 1

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []

        while True:
            chunk = file.read(Config.CHUNK_SIZE)
            if not chunk:
                break 

            for region, s3_client in s3_clients.items():
                futures.append(executor.submit(upload_chunk,chunk,filename,chunk_number,region))
            
            chunk_number += 1  

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                urls.append(result)
    
    return urls

def upload_chunk(chunk,filename,chunk_number,region):
    try:
        compressed_chunk = compress_chunk(chunk)
        
        s3_client = s3_clients[region]
        chunk_file = io.BytesIO(compressed_chunk)  
        chunk_filename = f"{filename}_chunk_{chunk_number}.gz"
        bucket_name = Config.S3_BUCKET_NAME[region]
        
        md5_checksum = generate_md5(chunk)
        
        s3_client.upload_fileobj(
            chunk_file, 
            bucket_name, 
            chunk_filename,
            ExtraArgs={
                'Metadata':{
                    'md5_checksum' : md5_checksum
                }
            }
        )
        
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{chunk_filename}"
        return {'url': url, 'region': region, 'chunk_number': chunk_number, 'md5_checksum' : md5_checksum}
    except Exception as e:
        print(f"Error uploading chunk {chunk_number} to S3 in region {region}: {str(e)}")
        return None

def download_chunks_from_s3(chunk_urls):
    chunks = []
    errors = [] 

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures=[]

        for chunk_info in chunk_urls:
            url = chunk_info['url']
            backup_url = chunk_info.get('backup_url', None)
            expected_md5 = chunk_info['md5_checksum']

            futures.append(executor.submit(download_chunk_with_failover, url, backup_url, chunk_info['region'],expected_md5))

        for future in concurrent.futures.as_completed(futures):
            result=future.result()
            if result:
                chunks.append(result)
            else:
                errors.append("Failed to download chunks")

    if errors:
        print("Errors encountered during download:")
        for error in errors:
            print(error)
    
    return chunks if chunks else None

def check_bucket_health():
    while True:
        for region, bucket_name in Config.S3_BUCKET_NAME.items():
            try:
                s3_clients[region].head_bucket(Bucket = bucket_name)
                bucket_health[region] = True
                print(f"Bucket {bucket_name} in {region} is healthy.")
            except Exception as e:
                bucket_health[region] = False
                print(f"Bucket {bucket_name} in {region} is DOWN: {e}")
        time.sleep(60)

def start_health_monitoring():
    thread = Thread(target=check_bucket_health)
    thread.daemon = True
    thread.start()

def download_chunk_with_failover(primary_url,backup_url,region,expected_md5):
    try:
        chunk_data = donwload_chunk_from_s3(primary_url, region)
        
        if chunk_data:
            print(f"Downloaded chunk from primary URL: {primary_url}")
            if verify_md5(chunk_data, expected_md5):
                print(f"Checksum verification passed for {primary_url}")
                return chunk_data
            else:
                print(f"Checksum verification failed for {primary_url}")
                return None
    except Exception as e:
        print(f"Primary download failed : {e}")

    if backup_url:
        try:
            chunk_data = donwload_chunk_from_s3(backup_url, region)
            if chunk_data:
                print(f"Downloaded chunk from backup URL: {backup_url}")
                if verify_md5(chunk_data, expected_md5):
                    print(f"Checksum verification passed for {backup_url}")
                    return chunk_data
                else:
                    print(f"Checksum verification failed for {backup_url}")
        except Exception as e:
            print(f"Backup download failed for {backup_url}: {e}")
    
    return None

def donwload_chunk_from_s3(url,region):
    try:
        bucket = url.split('.')[0].split('//')[1] 
        key = url.split('/')[-1]

        s3_client = boto3.client('s3', region_name=region)
            
        response = s3_client.get_object(Bucket=bucket, Key=key)
        compressed_chunk_data = response['Body'].read()
        
        chunk_data = decompress_chunk(compressed_chunk_data)
        return chunk_data
    except Exception as e:
        raise e