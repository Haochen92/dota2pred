from .build_service import main
import subprocess

def docker_compose_up():
    subprocess.run(
        ['docker', 'compose', 'up', '-d', '--force-recreate', '--no-deps', 'bentoml'],
        check=True  # This will raise an exception if the command fails
    )
    
if __name__ == "__main__":
    main()
    docker_compose_up()

