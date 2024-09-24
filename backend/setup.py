from pathlib import Path
import sys
import site

venv_path = sys.prefix

site_packages_path = Path(site.getsitepackages()[0])

pth_file = site_packages_path / 'project.pth'

root_path = Path.cwd().resolve()
src_path = root_path/'src'
data_path = root_path/'data'
model_path = root_path/'models'
constants_path = root_path/'constants'

dir_paths = [root_path, src_path,data_path,model_path]

if not pth_file.exists():
    # If it doesn't exist, create it and write the paths
    with pth_file.open('w') as file:
        for path in dir_paths:
            file.write(str(path) + '\n')
else:
    # If it exists, check the paths and add the missing ones
    with pth_file.open('r') as file:
        existing_paths = file.readlines()

    # Strip out newline characters for comparison
    existing_paths = [path.strip() for path in existing_paths]

    # Check which paths are missing
    missing_paths = [path for path in dir_paths if str(path) not in existing_paths]

    # If there are any missing paths, append them to the file
    if missing_paths:
        with pth_file.open('a') as file:
            for path in missing_paths:
                file.write(str(path) + '\n')

print(f"Processed {pth_file}.")