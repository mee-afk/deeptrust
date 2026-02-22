"""
MinIO S3 Storage Service
Handles file uploads, downloads, and URL generation.
"""
from minio import Minio
from minio.error import S3Error
import os
import logging
from io import BytesIO
from datetime import timedelta

logger = logging.getLogger(__name__)

# MinIO configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "deeptrust")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "deeptrust_dev_password")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "deepfake-uploads")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


class StorageService:
    """MinIO S3 storage operations"""
    
    def __init__(self):
        self._client = None
        self._bucket_initialized = False
    
    @property
    def client(self):
        """Lazy initialize MinIO client"""
        if self._client is None:
            self._client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
            logger.info(f"✅ MinIO client initialized: {MINIO_ENDPOINT}")
        return self._client
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist (called on first use)"""
        if self._bucket_initialized:
            return
            
        try:
            if not self.client.bucket_exists(MINIO_BUCKET):
                self.client.make_bucket(MINIO_BUCKET)
                logger.info(f"✅ Created bucket: {MINIO_BUCKET}")
            else:
                logger.info(f"✅ Bucket exists: {MINIO_BUCKET}")
            self._bucket_initialized = True
        except S3Error as e:
            logger.error(f"❌ Bucket initialization failed: {e}")
            raise
    
    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload file to MinIO.
        
        Args:
            file_data: File content as bytes
            object_name: S3 object key (path in bucket)
            content_type: MIME type
            
        Returns:
            Object path in bucket
        """
        self._ensure_bucket_exists()
        
        try:
            file_stream = BytesIO(file_data)
            file_size = len(file_data)
            
            self.client.put_object(
                MINIO_BUCKET,
                object_name,
                file_stream,
                file_size,
                content_type=content_type
            )
            
            logger.info(f"✅ Uploaded: {object_name} ({file_size} bytes)")
            return object_name
            
        except S3Error as e:
            logger.error(f"❌ Upload failed: {e}")
            raise
    
    def download_file(self, object_name: str) -> bytes:
        """
        Download file from MinIO.
        
        Args:
            object_name: S3 object key
            
        Returns:
            File content as bytes
        """
        self._ensure_bucket_exists()
        
        try:
            response = self.client.get_object(MINIO_BUCKET, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"✅ Downloaded: {object_name}")
            return data
            
        except S3Error as e:
            logger.error(f"❌ Download failed: {e}")
            raise
    
    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Generate presigned URL for file access.
        
        Args:
            object_name: S3 object key
            expires: URL expiry in seconds (default 1 hour)
            
        Returns:
            Presigned URL
        """
        self._ensure_bucket_exists()
        
        try:
            url = self.client.presigned_get_object(
                MINIO_BUCKET,
                object_name,
                expires=timedelta(seconds=expires)
            )
            
            logger.info(f"✅ Generated URL for: {object_name}")
            return url
            
        except S3Error as e:
            logger.error(f"❌ URL generation failed: {e}")
            raise
    
    def delete_file(self, object_name: str):
        """
        Delete file from MinIO.
        
        Args:
            object_name: S3 object key
        """
        self._ensure_bucket_exists()
        
        try:
            self.client.remove_object(MINIO_BUCKET, object_name)
            logger.info(f"✅ Deleted: {object_name}")
            
        except S3Error as e:
            logger.error(f"❌ Delete failed: {e}")
            raise
    
    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in bucket"""
        self._ensure_bucket_exists()
        
        try:
            self.client.stat_object(MINIO_BUCKET, object_name)
            return True
        except S3Error:
            return False


# Singleton instance
storage_service = StorageService()