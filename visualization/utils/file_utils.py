"""
File utilities for handling different file formats
"""
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

def read_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Read and parse a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        return None

def read_csv_file(file_path: Path, **kwargs) -> Optional[pd.DataFrame]:
    """Read a CSV file into a pandas DataFrame"""
    try:
        return pd.read_csv(file_path, **kwargs)
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
        return None

def write_json_file(data: Dict[str, Any], file_path: Path) -> bool:
    """Write data to a JSON file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error writing JSON file {file_path}: {e}")
        return False

def write_csv_file(df: pd.DataFrame, file_path: Path, **kwargs) -> bool:
    """Write a DataFrame to a CSV file"""
    try:
        df.to_csv(file_path, index=False, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Error writing CSV file {file_path}: {e}")
        return False

def get_file_info(file_path: Path) -> Dict[str, Any]:
    """Get information about a file"""
    if not file_path.exists():
        return {"exists": False}
    
    stat = file_path.stat()
    
    return {
        "exists": True,
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "created": stat.st_ctime,
        "extension": file_path.suffix,
        "name": file_path.name,
        "stem": file_path.stem
    }

def ensure_directory(directory: Path) -> bool:
    """Ensure a directory exists, create if it doesn't"""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")
        return False

def find_files_by_pattern(directory: Path, pattern: str) -> List[Path]:
    """Find files matching a pattern in a directory"""
    try:
        if directory.exists():
            return list(directory.glob(pattern))
        return []
    except Exception as e:
        logger.error(f"Error finding files in {directory} with pattern {pattern}: {e}")
        return []

def safe_filename(filename: str) -> str:
    """Create a safe filename by removing/replacing invalid characters"""
    import re
    
    # Replace invalid characters with underscores
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    safe_name = safe_name.strip(' .')
    
    # Ensure it's not empty
    if not safe_name:
        safe_name = "unnamed"
    
    return safe_name

def get_file_extension_info(file_path: Path) -> Dict[str, Any]:
    """Get information about file type based on extension"""
    extension = file_path.suffix.lower()
    
    extension_info = {
        ".csv": {"type": "csv", "description": "Comma-Separated Values", "readable": True},
        ".json": {"type": "json", "description": "JSON Data", "readable": True},
        ".xlsx": {"type": "excel", "description": "Excel Spreadsheet", "readable": True},
        ".xls": {"type": "excel", "description": "Excel Spreadsheet (Legacy)", "readable": True},
        ".txt": {"type": "text", "description": "Text File", "readable": True},
        ".sol": {"type": "solution", "description": "Optimization Solution", "readable": True},
        ".lp": {"type": "lp", "description": "Linear Programming Model", "readable": True},
        ".pkl": {"type": "pickle", "description": "Python Pickle File", "readable": False},
        ".pdf": {"type": "pdf", "description": "PDF Document", "readable": False},
        ".png": {"type": "image", "description": "PNG Image", "readable": False},
        ".jpg": {"type": "image", "description": "JPEG Image", "readable": False},
        ".jpeg": {"type": "image", "description": "JPEG Image", "readable": False},
        ".svg": {"type": "image", "description": "SVG Image", "readable": False},
    }
    
    return extension_info.get(extension, {
        "type": "unknown",
        "description": "Unknown File Type",
        "readable": False
    })
