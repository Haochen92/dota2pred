import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from prefect import flow, task
from urllib.parse import urlparse

from dota_oracle_common.utils import get_logger, load_workspace_env
from dota_oracle_common.s3 import S3Wrapper


load_workspace_env()
logger = get_logger(__name__)


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@task
def backup_postgresql_db() -> Path:
    """
    Create a PostgreSQL backup using pg_dump in custom format.
    Uses standard POSTGRES_* env vars for connection.
    """
    db_name = _env("POSTGRES_DB", "dota2")
    db_user = _env("POSTGRES_USER", "postgres")
    db_host = _env("POSTGRES_HOST", "localhost")
    db_port = _env("POSTGRES_PORT", "5432")
    db_password = _env("POSTGRES_PASSWORD", "")

    # Fallback: derive connection details from DATABASE_URL if specific POSTGRES_* vars are not provided
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            parsed = urlparse(db_url)
            # Only override missing/placeholder values
            if not os.getenv("POSTGRES_DB") and parsed.path:
                db_name = parsed.path.lstrip("/")
            if not os.getenv("POSTGRES_USER") and parsed.username:
                db_user = parsed.username
            if not os.getenv("POSTGRES_PASSWORD") and parsed.password:
                db_password = parsed.password
            if not os.getenv("POSTGRES_HOST") and parsed.hostname:
                db_host = parsed.hostname
            if not os.getenv("POSTGRES_PORT") and parsed.port:
                db_port = str(parsed.port)
        except Exception as e:
            logger.warning(f"Failed to parse DATABASE_URL for backup fallback: {e}")

    output_dir = Path(_env("DB_BACKUP_DIR", "/tmp/db_backups")).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dump_file_name = f"{db_name}_backup_{timestamp}.dump"
    dump_file_path = output_dir / dump_file_name

    cmd = [
        "pg_dump",
        "-h",
        db_host,
        "-p",
        db_port,
        "-U",
        db_user,
        "-F",
        "c",
        "-f",
        str(dump_file_path),
        db_name,
    ]

    env = os.environ.copy()
    if db_password:
        env["PGPASSWORD"] = db_password

    logger.info(
        f"Starting pg_dump for db='{db_name}' host='{db_host}' port='{db_port}' to '{dump_file_path}'"
    )
    try:
        subprocess.run(cmd, check=True, env=env)
        logger.info(f"Backup created successfully: {dump_file_path}")
        return dump_file_path
    except subprocess.CalledProcessError as e:
        logger.error(f"pg_dump failed: {e}", exc_info=True)
        raise


@task
def upload_backup_to_s3(file_path: Path) -> str:
    """
    Upload the backup file to S3 using S3Wrapper.
    Uses AWS_BUCKET_NAME from env and optional DB_BACKUP_S3_PREFIX (default: 'postgresql/').
    """
    s3_prefix = _env("DB_BACKUP_S3_PREFIX", "postgresql/")
    object_key = f"{s3_prefix}{file_path.name}"

    try:
        s3 = S3Wrapper()
        ok = s3.upload_file(file_path=str(file_path), object_key=object_key)
        if not ok:
            raise RuntimeError("S3 upload reported failure")
        logger.info(f"Uploaded backup to s3://{os.getenv('AWS_BUCKET_NAME', 'UNKNOWN_BUCKET')}/{object_key}")
        return object_key
    except Exception as e:
        logger.error(f"Failed to upload backup to S3: {e}", exc_info=True)
        raise


@flow
def backup_db_flow() -> None:
    dump_path = backup_postgresql_db()
    upload_backup_to_s3(dump_path)


if __name__ == "__main__":
    backup_db_flow()
