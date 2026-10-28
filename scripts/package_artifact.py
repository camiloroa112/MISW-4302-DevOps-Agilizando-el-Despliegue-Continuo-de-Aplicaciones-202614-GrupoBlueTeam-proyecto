# 1st Party Imports
import os
import sys
import zipfile
import argparse
import subprocess
from pathlib import Path

# Paths (relative to the repository root) that must be included in the Elastic Beanstalk Docker artifact
INCLUDE_PATHS = ("Dockerfile", ".dockerignore", "application.py", "requirements.txt", "pyproject.toml", "uv.lock", "app", ".ebextensions",)

# Directory names that must never be packaged, even if they appear inside an included folder
EXCLUDED_DIR_NAMES = frozenset({"__pycache__", ".venv", "venv", ".pytest_cache", ".git", "tests", "scripts", "docs"})

# File names or suffixes that must never be packaged (secrets, environment files, temporary files)
EXCLUDED_FILE_NAMES = frozenset({".env"})

# File suffixes that must never be packaged (compiled Python, archives, logs)
EXCLUDED_FILE_SUFFIXES = (".pyc", ".pyo", ".zip", ".log")


# Resolve the repository root as the parent directory of the "scripts" folder that holds this file
def get_repository_root() -> Path:
    """
    Introduction:
        - This function returns the repository root regardless of the current working directory
    Returns:
        - Path: The absolute path to the repository root
    """

    # The script lives in <root>/scripts, so the root is one level up
    return Path(__file__).resolve().parent.parent

# Read the short commit SHA so the artifact name is traceable to a specific revision
def get_commit_sha(root: Path) -> str:
    """
    Introduction:
        - This function returns the short commit SHA, or a fallback when git is not available
    Returns:
        - str: The short commit SHA, the CodeBuild resolved source version, or "nogit"
    """

    # CodeBuild exposes the resolved source version; prefer it when present
    codebuild_version = os.environ.get("CODEBUILD_RESOLVED_SOURCE_VERSION")

    # A full SHA from CodeBuild is shortened to seven characters for readability
    if codebuild_version:
        return codebuild_version[:7]

    # Fall back to asking git directly when running locally
    try:
        
        # Use git to get the short SHA of the current commit (seven characters)
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd = root, capture_output = True, text = True, check = True)
        
        # Return the stripped output (the short SHA) to the caller
        return result.stdout.strip()

    # Any failure (git missing, not a repository) yields a neutral placeholder
    except (subprocess.CalledProcessError, FileNotFoundError):
        
        # Return a neutral placeholder so the artifact name is still valid and unique
        return "nogit"


# Decide whether a single file should be added to the artifact
def should_include_file(path: Path) -> bool:
    """
    Introduction:
        - This function rejects secrets, environment files, caches and temporary files
    Returns:
        - bool: True when the file is safe to package
    """

    # Reject files whose name is explicitly excluded (for example ".env")
    if path.name in EXCLUDED_FILE_NAMES:
        return False

    # Reject environment files such as ".env.local" or ".env.production"
    if path.name.startswith(".env"):
        return False

    # Reject files by suffix (compiled Python, archives, logs)
    if path.suffix in EXCLUDED_FILE_SUFFIXES:
        return False

    # Reject any file living inside an excluded directory
    if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
        return False

    # Everything else is safe to include
    return True


# Collect every file that must be written into the artifact
def collect_files(root: Path) -> list[Path]:
    """
    Introduction:
        - This function walks the included paths and returns the files to package
    Returns:
        - list[Path]: Absolute paths to every file that belongs in the artifact
    """

    # Accumulate the files to package
    collected: list[Path] = []

    # Walk each configured include path
    for relative in INCLUDE_PATHS:

        # Build the absolute source path
        source = root / relative

        # Skip include paths that do not exist in this checkout
        if not source.exists():
            continue

        # Add a single file directly when it passes the filters
        if source.is_file():

            # Only add the file if it is not excluded by name, suffix, or parent directory
            if should_include_file(source):
                collected.append(source)

        # Recurse into directories and add every file that passes the filters
        else:
            
            # Walk the directory tree in a reproducible order so the ZIP is deterministic
            for child in sorted(source.rglob("*")):

                # Only add files (not directories) that pass the filters
                if child.is_file() and should_include_file(child):
                    
                    # Add the file to the collection
                    collected.append(child)

    # Return the collected files
    return collected

# Build the deployable ZIP artifact and return its path
def build_artifact(output_dir: Path, name: str | None = None) -> Path:
    """
    Introduction:
        - This function writes the Elastic Beanstalk Docker artifact as a reproducible ZIP
    Returns:
        - Path: The path to the generated ZIP artifact
    """

    # Resolve the repository root
    root = get_repository_root()

    # Build the artifact name from the commit SHA unless the caller provides one
    artifact_name = name or f"blacklist-service-{get_commit_sha(root)}.zip"

    # Make sure the output directory exists
    output_dir.mkdir(parents = True, exist_ok = True)

    # Resolve the final artifact path
    artifact_path = output_dir / artifact_name

    # Gather the files to package
    files = collect_files(root)

    # Fail loudly if, for any reason, there is nothing to package
    if not files:
        raise RuntimeError("No files were collected for the artifact; check INCLUDE_PATHS")

    # Write the ZIP with stored paths relative to the repository root so Elastic Beanstalk sees a clean layout
    with zipfile.ZipFile(artifact_path, "w", compression = zipfile.ZIP_DEFLATED) as archive:
        
        # Add every collected file to the ZIP with a path relative to the repository root
        for file_path in files:

            # The path inside the ZIP is relative to the repository root, using forward slashes
            arcname = file_path.relative_to(root).as_posix()

            # Add the file to the archive
            archive.write(file_path, arcname)

    # Report the result on standard output so CodeBuild logs show it
    print(f"Artifact created: {artifact_path} ({len(files)} files)")

    # Return the artifact path
    return artifact_path

# Parse command-line arguments
def parse_arguments(argv: list[str]) -> argparse.Namespace:
    """
    Introduction:
        - This function defines the optional output directory and artifact name
    Returns:
        - argparse.Namespace: The parsed arguments
    """

    # Build the parser
    parser = argparse.ArgumentParser(description = "Package the deployable Elastic Beanstalk Docker artifact as a ZIP.")

    # Where the ZIP is written (defaults to a "dist" folder in the repository root)
    parser.add_argument("--output-dir", default = None, help = "Directory where the ZIP is written (default: <root>/dist)")

    # An explicit artifact name overrides the commit-based default
    parser.add_argument("--name", default = None, help = "Explicit artifact file name (default: blacklist-service-<sha>.zip)")

    # Return the parsed arguments
    return parser.parse_args(argv)

# Entry point used by CodeBuild and local runs
def main(argv: list[str]) -> int:
    """
    Introduction:
        - This function builds the artifact from the command line
    Returns:
        - int: A process exit code (0 on success)
    """

    # Parse the arguments
    arguments = parse_arguments(argv)

    # Resolve the output directory (default: <root>/dist)
    output_dir = Path(arguments.output_dir) if arguments.output_dir else get_repository_root() / "dist"

    # Build the artifact
    build_artifact(output_dir, arguments.name)

    # Signal success
    return 0

# Run the packager when executed directly
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))