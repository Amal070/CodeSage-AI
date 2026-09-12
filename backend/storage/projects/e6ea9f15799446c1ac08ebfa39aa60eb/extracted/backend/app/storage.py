"""File and ZIP Archive Extraction Service"""
import zipfile
import shutil
from pathlib import Path

def extract_project_zip(zip_path: str, extract_dir: str) -> list[str]:
    """Safely extracts uploaded ZIP archive and returns extracted files list."""
    target = Path(extract_dir)
    target.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zip_path, 'r') as archive:
        for member in archive.namelist():
            archive.extract(member, target)
            extracted.append(member)
    return extracted
