import shutil
from pathlib import Path
from prefect import flow


@flow
def clear_prefect_cache():
    # Define the path to the Prefect cache directory
    prefect_cache_dir = Path.home() / ".prefect/storage"

    # Check if the directory exists
    if prefect_cache_dir.exists() and prefect_cache_dir.is_dir():
        # Remove all files and directories inside the cache directory
        for item in prefect_cache_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        print(f"Cleared Prefect cache at {prefect_cache_dir}")
    else:
        print(f"Prefect cache directory not found at {prefect_cache_dir}")


if __name__ == "__main__":
    clear_prefect_cache()
