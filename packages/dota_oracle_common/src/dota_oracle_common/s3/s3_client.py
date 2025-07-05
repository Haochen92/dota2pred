import boto3
from mypy_boto3_s3 import S3Client
from s3transfer import S3Transfer
from botocore.exceptions import ClientError
import os
import logging
from dota_oracle_common.utils import load_workspace_env

load_workspace_env()
logger = logging.getLogger(__name__)


class S3Wrapper:
    def __init__(self) -> None:
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION", "ap-southeast-1")
        self.bucket_name = os.getenv("AWS_BUCKET_NAME", "liuhaochen92")

        if not all([self.access_key, self.secret_access_key]):
            raise ValueError("Missing AWS credentials")

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
        )

        self.transfer = S3Transfer(self.s3_client)

    def get_client(self) -> S3Client:
        return self.s3_client

    def upload_file(
        self,
        *,
        file_path: str,
        object_key: str,
    ) -> bool:
        """
        Upload File to s3 Object storage

        args:
            file_path: file path of object to be stored
            object_key: full path of object in s3 bucket
        """

        try:
            self.transfer.upload_file(filename=file_path, bucket=self.bucket_name, key=object_key)

        except ClientError as e:
            logger.error(e)
            return False

        logger.info(
            f"""
            File {file_path} has been successfully uploaded
            to {self.bucket_name}:{object_key}
            """
        )
        return True

    def download_file(
        self,
        *,
        file_path: str,
        object_key: str,
    ) -> bool:
        """
        Download File from s3 Object storage

        args:
            file_path: file path for download location
            object_key: full path of object in s3 bucket to retrieve
        """

        try:
            self.transfer.download_file(filename=file_path, bucket=self.bucket_name, key=object_key)

        except ClientError as e:
            logger.error(e)
            return False

        logger.info(
            f"""
            File from {self.bucket_name}:{object_key}
            has been successfully downloaded to {file_path}
            """
        )
        return True
