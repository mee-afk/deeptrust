"""
MinIO S3 Storage Integration
============================
This module encapsulates all interactions with the MinIO object storage service. 
It provides high-level abstractions for asset persistence, programmatic retrieval, 
and secure transient URL generation.
"""

from minio import Minio
from minio.error import S3Error
import os
import logging
from io import BytesIO
from datetime import timedelta

# Initialize scoped logger for storage operations
logger = logging.getLogger(__name__)

# Object Storage configuration parameters, sourced from environment.
# These connect to the private MinIO service within the internal network.
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "deeptrust")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "deeptrust_dev_password")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "deepfake-uploads")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


class StorageService:
    """
    Service class responsible for S3-compatible storage operations.
    
    Implements a robust pattern for managing media assets, featuring lazy 
    client initialization and automatic bucket provisioning.
    """
    
    def __init__(self):
        """ Initializes the service container. """
        self._client = None
        self._bucket_initialized = False
    
    @property
    def client(self) -> Minio:
        """
        Lazy accessor for the MinIO low-level driver.
        Ensures resources are only established when a storage operation is requested.
        """
        if self._client is None:
            self._client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
            logger.info(f"Persistent storage connection established at {MINIO_ENDPOINT}")
        return self._client
    
    def _ensure_bucket_exists(self):
        """
        Internal safety check to confirm the target bucket is provisioned.
        Automatically creates the primary asset bucket if missing.
        """
        if self._bucket_initialized:
            return
            
        try:
            if not self.client.bucket_exists(MINIO_BUCKET):
                self.client.make_bucket(MINIO_BUCKET)
                logger.info(f"Initialized new asset bucket: {MINIO_BUCKET}")
            else:
                logger.info(f"Connected to existing asset bucket: {MINIO_BUCKET}")
            self._bucket_initialized = True
        except S3Error as e:
            logger.error(f"Failed to verify/initialize storage bucket: {e}")
            raise
    
    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Streams binary data into the persistent storage bucket.
        
        Args:
            file_data (bytes): The raw binary content of the media.
            object_name (str): The unique destination key (path) within the bucket.
            content_type (str): Explicit MIME type for correct browser handling on retrieval.
            
        Returns:
            str: The internal object key of the successfully persisted file.
        """
        self._ensure_bucket_exists()
        
        try:
            file_stream = BytesIO(file_data)
            file_size = len(file_data)
            
            # Atomic upload of the binary stream
            self.client.put_object(
                MINIO_BUCKET,
                object_name,
                file_stream,
                file_size,
                content_type=content_type
            )
            
            logger.info(f"Asset persisted successfully: {object_name} ({file_size} bytes)")
            return object_name
            
        except S3Error as e:
            logger.error(f"S3 protocol error during upload for {object_name}: {e}")
            raise
    
    def download_file(self, object_name: str) -> bytes:
        """
        Retrieves binary data from the persistent storage bucket.
        
        Args:
            object_name (str): The unique object key.
            
        Returns:
            bytes: The full content of the file.
        """
        self._ensure_bucket_exists()
        
        try:
            # Open stream and read full binary content into memory
            response = self.client.get_object(MINIO_BUCKET, object_name)
            data = response.read()
            # Explicit resource cleanup for the response object
            response.close()
            response.release_conn()
            
            logger.info(f"Asset retrieved from storage: {object_name}")
            return data
            
        except S3Error as e:
            logger.error(f"S3 protocol error during retrieval for {object_name}: {e}")
            raise
    
    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Generates a secure, time-limited transient link for authenticated downloads.
        
        This allows the frontend to fetch media directly from storage without 
        exposing private credentials or routing large binaries through the API.
        
        Args:
            object_name (str): Target asset key.
            expires (int): Seconds until the link expires. Defaults to 3600 (1 hour).
        """
        self._ensure_bucket_exists()
        
        try:
            url = self.client.presigned_get_object(
                MINIO_BUCKET,
                object_name,
                expires=timedelta(seconds=expires)
            )
            
            logger.info(f"Generated secure transient URL for: {object_name}")
            return url
            
        except S3Error as e:
            logger.error(f"Transient URL generation failure for {object_name}: {e}")
            raise
    
    def delete_file(self, object_name: str):
        """
        Atomically removes an asset from persistent storage.
        
        Args:
            object_name (str): Key of the file to prune.
        """
        self._ensure_bucket_exists()
        
        try:
            self.client.remove_object(MINIO_BUCKET, object_name)
            logger.info(f"Asset permanently purged from storage: {object_name}")
            
        except S3Error as e:
            logger.error(f"Asset deletion failed for {object_name}: {e}")
            raise
    
    def file_exists(self, object_name: str) -> bool:
        """ 
        Verifies the existence of an object key within the active bucket. 
        Utilized for integrity checks before processing requests.
        """
        self._ensure_bucket_exists()
        
        try:
            self.client.stat_object(MINIO_BUCKET, object_name)
            return True
        except S3Error:
            # Any S3 error (typically 404) implies the object is missing or unreachable
            return False


# Shared singleton instance providing storage services to the application
storage_service = StorageService()