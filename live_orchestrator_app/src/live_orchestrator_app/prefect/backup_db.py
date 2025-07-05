from prefect import flow, task
import subprocess
from pathlib import Path
from datetime import datetime
from prefect_aws import AwsCredentials, S3Bucket

S3_BUCKET_NAME = "liuhaochen92"
S3_FOLDER_NAME = "postgresql"

DB_NAME = "dota2"
DB_USER = "liuhaochen"
BACKUP_PATH = Path("~/projects/database").expanduser()  # Using Pathlib

aws_credentials = AwsCredentials.load("s3")
s3_bucket = S3Bucket(bucket_name=S3_BUCKET_NAME, bucket_folder=S3_FOLDER_NAME, credentials=aws_credentials)


@task
def backup_postgresql_db():
    """Create a backup of the PostgreSQL database."""
    timestamp = datetime.now().strftime("%Y%m%d")
    dump_file_name = f"{DB_NAME}_backup_{timestamp}.dump"
    dump_file_path = BACKUP_PATH / dump_file_name  # Pathlib usage

    try:
        # Command to dump the PostgreSQL database
        dump_command = [
            "pg_dump",
            "-U",
            DB_USER,
            "-F",
            "c",  # Custom format
            "-f",
            str(dump_file_path),  # Convert Pathlib object to string for subprocess
            DB_NAME,
        ]
        # Run the command
        subprocess.run(dump_command, check=True)
        print(f"Backup created successfully: {dump_file_path}")
        return dump_file_path
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while creating backup: {e}")
        raise


@flow
def upload_to_s3():
    dump_file_path = backup_postgresql_db()
    try:
        s3_bucket.upload_from_path(dump_file_path)
    except Exception as e:
        print(f"Error occured while uploading to s3: {e}")
        raise


if __name__ == "__main__":
    upload_to_s3()
