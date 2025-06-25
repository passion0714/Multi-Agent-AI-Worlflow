import os
import boto3
import tempfile
from typing import Optional, Dict, Any
from loguru import logger
from botocore.exceptions import ClientError
from datetime import datetime

class S3Service:
    """Service for handling S3 operations for call recordings and other files"""
    
    def __init__(self):
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "mergeai.call.recordings")
        
        # Initialize S3 client
        try:
            if self.aws_access_key and self.aws_secret_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                logger.info(f"S3 Service initialized - Bucket: {self.bucket_name}, Region: {self.aws_region}")
            else:
                logger.warning("S3 credentials not configured - S3 operations will be disabled")
                self.s3_client = None
                
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test S3 connection and bucket access"""
        if not self.s3_client:
            return {
                "success": False,
                "error": "S3 client not configured (missing credentials)"
            }
        
        try:
            # Test bucket access
            response = self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            return {
                "success": True,
                "message": f"S3 bucket '{self.bucket_name}' accessible",
                "bucket": self.bucket_name,
                "region": self.aws_region
            }
            
        except self.s3_client.exceptions.NoSuchBucket:
            return {
                "success": False,
                "error": f"S3 bucket '{self.bucket_name}' does not exist"
            }
        except self.s3_client.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            return {
                "success": False,
                "error": f"S3 access error ({error_code}): {error_message}",
                "error_code": error_code
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"S3 connection error: {str(e)}"
            }
    
    async def upload_recording(self, recording_data: bytes, filename: str) -> Optional[str]:
        """Upload call recording to S3"""
        if not self.s3_client:
            logger.warning("S3 client not configured - cannot upload recording")
            return None
            
        try:
            # Generate S3 key with proper structure
            timestamp = datetime.utcnow().strftime("%Y/%m/%d")
            s3_key = f"recordings/{timestamp}/{filename}"
            
            logger.info(f"Uploading recording to S3: {s3_key}")
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=recording_data,
                ContentType='audio/mpeg',
                Metadata={
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'source': 'vapi_call_recording'
                }
            )
            
            logger.info(f"Successfully uploaded recording: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to upload recording {filename}: {e}")
            return None
    
    async def get_recording_url(self, s3_key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate presigned URL for recording access"""
        if not self.s3_client:
            logger.warning("S3 client not configured - cannot generate presigned URL")
            return None
            
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            
            logger.debug(f"Generated presigned URL for {s3_key}")
            return presigned_url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            return None
    
    async def upload_csv_file(self, csv_data: bytes, filename: str) -> Optional[str]:
        """Upload CSV file to S3"""
        if not self.s3_client:
            logger.warning("S3 client not configured - cannot upload CSV")
            return None
            
        try:
            # Generate S3 key for CSV files
            timestamp = datetime.utcnow().strftime("%Y/%m/%d")
            s3_key = f"csv_uploads/{timestamp}/{filename}"
            
            logger.info(f"Uploading CSV to S3: {s3_key}")
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=csv_data,
                ContentType='text/csv',
                Metadata={
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'source': 'csv_import'
                }
            )
            
            logger.info(f"Successfully uploaded CSV: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to upload CSV {filename}: {e}")
            return None
    
    async def list_recordings(self, prefix: str = "recordings/", max_keys: int = 100) -> list:
        """List recordings in S3 bucket"""
        if not self.s3_client:
            logger.warning("S3 client not configured - cannot list recordings")
            return []
            
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            recordings = []
            for obj in response.get('Contents', []):
                recordings.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag'].strip('"')
                })
            
            logger.info(f"Found {len(recordings)} recordings in S3")
            return recordings
            
        except Exception as e:
            logger.error(f"Failed to list recordings: {e}")
            return []
    
    async def delete_recording(self, s3_key: str) -> bool:
        """Delete recording from S3"""
        if not self.s3_client:
            logger.warning("S3 client not configured - cannot delete recording")
            return False
            
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Successfully deleted recording: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete recording {s3_key}: {e}")
            return False
    
    def get_bucket_info(self) -> Dict[str, Any]:
        """Get S3 bucket configuration information"""
        return {
            "bucket_name": self.bucket_name,
            "region": self.aws_region,
            "client_configured": self.s3_client is not None,
            "credentials_configured": bool(self.aws_access_key and self.aws_secret_key)
        } 