import sys
from dota_oracle_common.utils.set_logging import get_logger
from alembic.config import Config
from alembic import command

logger = get_logger("alembic_migrations")

# Run migration for both test and production database


def run_migrations(db_url, description):
    """Run Alembic migrations for a specific database."""
    logger.info(f"Running migrations for {description}")

    # Create Alembic configuration
    alembic_cfg = Config("../alembic.ini")
    alembic_cfg.set_main_option("script_location", ".")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    try:
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        logger.info(f"Successfully migrated {description}")
        print(f"Successfully migrated {description}")
        return True
    except Exception as e:
        logger.error(f"Error migrating {description}: {e}")
        print(f"Error migrating {description}: {e}")
        return False


def main():
    # Database configurations
    # Updated to match your Docker Compose configuration
    databases = [
        {"url": "postgresql://liuhaochen:110799@localhost:6000/dota2", "description": "Production database (dota2)"},
    ]

    # Track success
    success = True

    # Run migrations for each database
    for db in databases:
        if not run_migrations(db["url"], db["description"]):
            success = False

    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
