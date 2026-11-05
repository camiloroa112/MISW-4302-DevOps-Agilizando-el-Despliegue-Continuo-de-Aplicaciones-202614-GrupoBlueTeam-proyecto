# 1st Party Imports
import re
import sys
import json
from pathlib import Path

# The container name and port must be identical across taskdef, appspec, Dockerfile and ECS.
EXPECTED_CONTAINER_NAME = "blacklist"
EXPECTED_CONTAINER_PORT = 8000

# Placeholders required by the CodeDeployToECS action contract.
IMAGE_PLACEHOLDER = "<IMAGE1_NAME>"
TASKDEF_PLACEHOLDER = "<TASK_DEFINITION>"


# Resolve the repository root as the parent of the "scripts" folder.
def get_repository_root() -> Path:
    """
    Introduction:
        - This function returns the repository root regardless of the current working directory
    Returns:
        - Path: The absolute path to the repository root
    """

    # The script lives in <root>/scripts, so the root is one level up
    return Path(__file__).resolve().parent.parent


# Load the task definition JSON and return it as a dict.
def load_taskdef(root: Path) -> dict:
    """
    Introduction:
        - This function reads deploy/taskdef.json and parses it as JSON
    Returns:
        - dict: The parsed task definition
    """

    # Read and parse the task definition file
    return json.loads((root / "deploy" / "taskdef.json").read_text(encoding = "utf-8"))


# Read the AppSpec file as raw text (it is small and placeholder-based).
def load_appspec_text(root: Path) -> str:
    """
    Introduction:
        - This function reads deploy/appspec.yaml as text
    Returns:
        - str: The AppSpec file contents
    """

    # Read the AppSpec file contents
    return (root / "deploy" / "appspec.yaml").read_text(encoding = "utf-8")


# Read the Dockerfile as raw text to confirm the exposed port.
def load_dockerfile_text(root: Path) -> str:
    """
    Introduction:
        - This function reads the Dockerfile as text
    Returns:
        - str: The Dockerfile contents
    """

    # Read the Dockerfile contents
    return (root / "Dockerfile").read_text(encoding = "utf-8")


# Validate the task definition and collect human-readable errors.
def check_taskdef(taskdef: dict) -> list[str]:
    """
    Introduction:
        - This function validates the container name, port, image placeholder and Fargate settings
    Returns:
        - list[str]: A list of error messages (empty when valid)
    """

    # Accumulate the errors found
    errors: list[str] = []

    # The task definition must declare exactly one essential container
    containers = taskdef.get("containerDefinitions", [])

    # There must be at least one container definition
    if not containers:
        errors.append("taskdef.json: containerDefinitions is empty")
        return errors

    # Use the first container definition for the checks
    container = containers[0]

    # The container name must match the expected value
    if container.get("name") != EXPECTED_CONTAINER_NAME:
        errors.append(f"taskdef.json: container name is {container.get('name')!r}, expected {EXPECTED_CONTAINER_NAME!r}")

    # The image field must be the CodeDeploy image placeholder
    if container.get("image") != IMAGE_PLACEHOLDER:
        errors.append(f"taskdef.json: image is {container.get('image')!r}, expected {IMAGE_PLACEHOLDER!r}")

    # The container must map the expected port
    ports = [mapping.get("containerPort") for mapping in container.get("portMappings", [])]

    # The expected container port must be present
    if EXPECTED_CONTAINER_PORT not in ports:
        errors.append(f"taskdef.json: containerPort {EXPECTED_CONTAINER_PORT} not found in {ports}")

    # Fargate requires awsvpc networking
    if taskdef.get("networkMode") != "awsvpc":
        errors.append(f"taskdef.json: networkMode is {taskdef.get('networkMode')!r}, expected 'awsvpc'")

    # Fargate must be a required compatibility
    if "FARGATE" not in taskdef.get("requiresCompatibilities", []):
        errors.append("taskdef.json: requiresCompatibilities must include 'FARGATE'")

    # The architecture must match the image built in CodeBuild (linux/amd64)
    architecture = taskdef.get("runtimePlatform", {}).get("cpuArchitecture")

    # The runtime platform must be x86_64 to match the built image
    if architecture != "X86_64":
        errors.append(f"taskdef.json: runtimePlatform.cpuArchitecture is {architecture!r}, expected 'X86_64'")

    # Return the collected errors
    return errors


# Validate the AppSpec text and collect human-readable errors.
def check_appspec(appspec_text: str) -> list[str]:
    """
    Introduction:
        - This function validates the TaskDefinition placeholder, container name and port
    Returns:
        - list[str]: A list of error messages (empty when valid)
    """

    # Accumulate the errors found
    errors: list[str] = []

    # The AppSpec must keep the TaskDefinition placeholder for CodeDeploy to replace
    if TASKDEF_PLACEHOLDER not in appspec_text:
        errors.append(f"appspec.yaml: missing placeholder {TASKDEF_PLACEHOLDER}")

    # The AppSpec must reference the same container name (ignore commented lines)
    active_lines = "\n".join(line for line in appspec_text.splitlines() if not line.strip().startswith("#"))

    # The container name must appear in the active AppSpec content
    if f'ContainerName: "{EXPECTED_CONTAINER_NAME}"' not in active_lines and f"ContainerName: {EXPECTED_CONTAINER_NAME}" not in active_lines:
        errors.append(f"appspec.yaml: ContainerName must be {EXPECTED_CONTAINER_NAME!r}")

    # The container port must appear in the active AppSpec content
    if f"ContainerPort: {EXPECTED_CONTAINER_PORT}" not in active_lines:
        errors.append(f"appspec.yaml: ContainerPort must be {EXPECTED_CONTAINER_PORT}")

    # Return the collected errors
    return errors


# Validate the Dockerfile exposes the expected port.
def check_dockerfile(dockerfile_text: str) -> list[str]:
    """
    Introduction:
        - This function confirms the Dockerfile exposes and binds the expected container port
    Returns:
        - list[str]: A list of error messages (empty when valid)
    """

    # Accumulate the errors found
    errors: list[str] = []

    # The Dockerfile should EXPOSE the expected port
    if not re.search(rf"EXPOSE\s+{EXPECTED_CONTAINER_PORT}\b", dockerfile_text):
        errors.append(f"Dockerfile: missing 'EXPOSE {EXPECTED_CONTAINER_PORT}'")

    # The gunicorn bind should use the expected port
    if f":{EXPECTED_CONTAINER_PORT}" not in dockerfile_text:
        errors.append(f"Dockerfile: no bind to port {EXPECTED_CONTAINER_PORT} found")

    # Return the collected errors
    return errors


# Run every check and report the result.
def main() -> int:
    """
    Introduction:
        - This function runs all deploy-artifact coherence checks and prints the result
    Returns:
        - int: 0 when everything is coherent, 1 otherwise
    """

    # Resolve the repository root
    root = get_repository_root()

    # Load every file under validation
    taskdef = load_taskdef(root)
    appspec_text = load_appspec_text(root)
    dockerfile_text = load_dockerfile_text(root)

    # Collect the errors from every check
    errors: list[str] = []
    errors += check_taskdef(taskdef)
    errors += check_appspec(appspec_text)
    errors += check_dockerfile(dockerfile_text)

    # Report failures and exit non-zero
    if errors:

        # Print a header and each error on its own line
        print("Deploy artifact validation FAILED:")

        # Print every error message
        for error in errors:
            print(f"  - {error}")

        # Signal failure
        return 1

    # Report success
    print(f"Deploy artifact validation OK: container '{EXPECTED_CONTAINER_NAME}' on port {EXPECTED_CONTAINER_PORT}, placeholders present.")

    # Signal success
    return 0


# Run the validator when executed directly
if __name__ == "__main__":
    sys.exit(main())
