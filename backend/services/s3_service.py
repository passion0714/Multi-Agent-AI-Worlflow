import os
import boto3
from typing import Optional
from loguru import logger
from botocore.exceptions import ClientError

class S3Service:
    """Service for uploading call recordings to AWS S3 for Lead Hoop"""
    
    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.bucket = os.getenv("S3_BUCKET", "leadhoop-recordings")
        self.folder = os.getenv("S3_FOLDER", "ieim/eluminus_merge_142")
        
        if not self.access_key or not self.secret_key:
            raise ValueError("AWS credentials are required")
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )
    
    async def upload_recording(self, recording_data: bytes, filename: str) -> Optional[str]:
        """Upload call recording to S3 bucket"""
        try:
            # Construct the full S3 key
            s3_key = f"{self.folder}/{filename}"
            
            # Upload the file
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=recording_data,
                ContentType="audio/mpeg",
                Metadata={
                    "source": "vapi",
                    "publisher_id": os.getenv("PUBLISHER_ID", "142"),
                    "uploaded_by": "merge_ai_workflow"
                }
            )
            
            logger.info(f"Successfully uploaded recording to S3: {s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"AWS S3 error uploading recording: {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading recording to S3: {e}")
            return None
    
    def verify_bucket_access(self) -> bool:
        """Verify that we can access the S3 bucket"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            logger.info(f"Successfully verified access to S3 bucket: {self.bucket}")
            return True
        except ClientError as e:
            logger.error(f"Cannot access S3 bucket {self.bucket}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error verifying S3 bucket access: {e}")
            return False
    
    def list_recordings(self, prefix: Optional[str] = None) -> list:
        """List recordings in the S3 bucket"""
        try:
            list_prefix = f"{self.folder}/"
            if prefix:
                list_prefix += prefix
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=list_prefix
            )
            
            recordings = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    recordings.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'filename': obj['Key'].split('/')[-1]
                    })
            
            return recordings
            
        except Exception as e:
            logger.error(f"Error listing S3 recordings: {e}")
            return []
    
    def get_recording_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for accessing a recording"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
    
    def delete_recording(self, s3_key: str) -> bool:
        """Delete a recording from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"Successfully deleted recording: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting recording {s3_key}: {e}")
            return False 