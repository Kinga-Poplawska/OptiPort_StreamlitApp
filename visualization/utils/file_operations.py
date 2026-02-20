"""
Utility functions for file import, export, and template generation
"""
import pandas as pd
import json
import io
import streamlit as st
from pathlib import Path
from typing import Dict, List, Tuple, Union, Any

from config.file_formats import FILE_FORMATS, TEMPLATE_README


class FileImportExport:
    """Handle file import, export, and template generation operations"""
    
    @staticmethod
    def validate_csv_import(df: pd.DataFrame, file_type: str) -> Dict[str, Any]:
        """
        Validate imported CSV data against expected format
        
        Args:
            df: Imported DataFrame
            file_type: Type of file ('stock_properties' or 'financial_properties')
            
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'warnings': List[str],
                'missing_columns': List[str],
                'unknown_columns': List[str]
            }
        """
        format_spec = FILE_FORMATS.get(file_type, {})
        required_cols = format_spec.get('required_columns', [])
        optional_cols = format_spec.get('optional_columns', [])
        all_expected_cols = set(required_cols + optional_cols)
        
        imported_cols = set(df.columns)
        
        # Find missing and unknown columns
        missing_cols = set(required_cols) - imported_cols
        unknown_cols = imported_cols - all_expected_cols
        
        warnings = []
        
        if missing_cols:
            warnings.append(f"⚠️ Missing expected columns: {', '.join(sorted(missing_cols))}. These cells will remain empty.")
        
        if unknown_cols:
            warnings.append(f"⚠️ Unknown columns found: {', '.join(sorted(unknown_cols))}. These will be ignored during import.")
        
        return {
            'valid': len(missing_cols) == 0,  # Valid if no required columns missing
            'warnings': warnings,
            'missing_columns': list(missing_cols),
            'unknown_columns': list(unknown_cols)
        }
    
    @staticmethod
    def validate_json_import(data: dict, file_type: str) -> Dict[str, Any]:
        """
        Validate imported JSON data against expected schema
        
        Args:
            data: Imported dictionary
            file_type: Type of file ('general_finances' or 'portfolio_caps')
            
        Returns:
            Dictionary with validation results
        """
        format_spec = FILE_FORMATS.get(file_type, {})
        schema = format_spec.get('schema', {})
        
        warnings = []
        missing_keys = []
        unknown_keys = []
        structure_issues = []
        
        # Check if data is actually a dictionary
        if not isinstance(data, dict):
            return {
                'valid': False,
                'warnings': [f"Ungültiges Format: JSON muss ein Objekt sein, ist aber {type(data).__name__}"],
                'error': "JSON ist kein Dictionary",
                'missing_keys': [],
                'unknown_keys': []
            }
        
        def check_nested_keys(expected: dict, actual: dict, path: str = ""):
            """Recursively check nested dictionary structure"""
            # Safety check - if actual isn't a dict, we can't process it
            if not isinstance(actual, dict):
                structure_issues.append(f"'{path}' sollte ein Objekt sein, ist aber {type(actual).__name__}")
                return
                
            for key, value_type in expected.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in actual:
                    missing_keys.append(current_path)
                elif isinstance(value_type, dict):
                    if isinstance(actual.get(key), dict):
                        # Recursively check nested structure
                        check_nested_keys(value_type, actual[key], current_path)
                    else:
                        structure_issues.append(f"'{current_path}' sollte ein Objekt sein, ist aber {type(actual.get(key)).__name__}")
            
            # Check for unknown keys in actual
            for key in actual:
                if key not in expected:
                    current_path = f"{path}.{key}" if path else key
                    unknown_keys.append(current_path)
        
        try:
            check_nested_keys(schema, data)
        except Exception as e:
            warnings.append(f"⚠️ Fehler bei der Schemavalidierung: {str(e)}")
        
        if missing_keys:
            warnings.append(f"⚠️ Fehlende Schlüssel: {', '.join(missing_keys)}. Standardwerte werden verwendet.")
            
        if structure_issues:
            warnings.append(f"⚠️ Strukturprobleme: {', '.join(structure_issues)}")
        
        if unknown_keys:
            warnings.append(f"⚠️ Unknown keys found: {', '.join(unknown_keys)}. These will be ignored.")
        
        return {
            'valid': True,  # We allow missing keys with defaults
            'warnings': warnings,
            'missing_keys': missing_keys,
            'unknown_keys': unknown_keys
        }
    
    @staticmethod
    def generate_csv_template(file_type: str) -> str:
        """
        Generate CSV template string with zeros/empty values
        
        Args:
            file_type: Type of file ('stock_properties' or 'financial_properties')
            
        Returns:
            CSV string with template data (all zeros)
        """
        format_spec = FILE_FORMATS.get(file_type, {})
        delimiter = format_spec.get('delimiter', ',')
        
        # Get column definitions
        required_cols = format_spec.get('required_columns', [])
        optional_cols = format_spec.get('optional_columns', [])
        all_cols = required_cols + optional_cols
        column_types = format_spec.get('column_types', {})
        
        if not all_cols:
            return ""
        
        # Create empty row with zeros/empty values
        empty_row = {}
        for col in all_cols:
            col_type = column_types.get(col, 'str')
            if col_type == 'int':
                empty_row[col] = 0
            elif col_type == 'float':
                empty_row[col] = 0.0
            elif col_type == 'bool':
                empty_row[col] = False
            else:
                empty_row[col] = ''
        
        # Create DataFrame with single empty row
        df = pd.DataFrame([empty_row])
        
        # Convert to CSV string
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, sep=delimiter)
        csv_string = csv_buffer.getvalue()
        
        return csv_string
    
    @staticmethod
    def generate_json_template(file_type: str) -> str:
        """
        Generate JSON template string with zeros/empty values
        
        Args:
            file_type: Type of file ('general_finances' or 'portfolio_caps')
            
        Returns:
            JSON string with template data (all zeros)
        """
        format_spec = FILE_FORMATS.get(file_type, {})
        schema = format_spec.get('schema', {})
        
        def create_empty_from_schema(schema_obj):
            """Recursively create empty structure from schema - uses null for empty cells"""
            result = {}
            for key, value in schema_obj.items():
                if isinstance(value, dict):
                    result[key] = create_empty_from_schema(value)
                else:
                    # Use None (null in JSON) for all types - appears as empty in UI
                    result[key] = None
            return result
        
        # Create empty template from schema
        template_data = create_empty_from_schema(schema)
        
        # Convert to formatted JSON string
        json_string = json.dumps(template_data, indent=2)
        
        return json_string
    
    @staticmethod
    def generate_readme() -> str:
        """
        Generate README content for templates
        
        Returns:
            README markdown string
        """
        return TEMPLATE_README
    
    @staticmethod
    def export_csv(df: pd.DataFrame, file_type: str) -> str:
        """
        Export DataFrame to CSV string with correct delimiter
        
        Args:
            df: DataFrame to export
            file_type: Type of file to determine delimiter
            
        Returns:
            CSV string
        """
        format_spec = FILE_FORMATS.get(file_type, {})
        delimiter = format_spec.get('delimiter', ',')
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, sep=delimiter)
        csv_string = csv_buffer.getvalue()
        
        return csv_string
    
    @staticmethod
    def export_json(data: dict, file_type: str) -> str:
        """
        Export dictionary to formatted JSON string
        
        Args:
            data: Dictionary to export
            file_type: Type of file (for consistency)
            
        Returns:
            JSON string
        """
        # Use indent for readability
        json_string = json.dumps(data, indent=2)
        
        return json_string
    
    @staticmethod
    def parse_uploaded_csv(uploaded_file, file_type: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Parse uploaded CSV file and validate
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            file_type: Type of file being uploaded
            
        Returns:
            Tuple of (DataFrame, validation_result)
        """
        format_spec = FILE_FORMATS.get(file_type, {})
        delimiter = format_spec.get('delimiter', ',')
        
        try:
            # Try with specified delimiter
            df = pd.read_csv(uploaded_file, sep=delimiter)
        except Exception as e:
            # Try with alternative delimiter
            uploaded_file.seek(0)
            alt_delimiter = ';' if delimiter == ',' else ','
            try:
                df = pd.read_csv(uploaded_file, sep=alt_delimiter)
            except Exception:
                return None, {
                    'valid': False,
                    'warnings': [],
                    'error': f"Could not parse CSV file: {str(e)}"
                }
        
        # Validate the DataFrame
        validation = FileImportExport.validate_csv_import(df, file_type)
        
        return df, validation
    
    @staticmethod
    def parse_uploaded_json(uploaded_file, file_type: str) -> Tuple[dict, Dict[str, Any]]:
        """
        Parse uploaded JSON file and validate
        
        Args:
            uploaded_file: Streamlit UploadedFile object
            file_type: Type of file being uploaded
            
        Returns:
            Tuple of (dict, validation_result)
        """
        try:
            # Read the file content and preserve it for debugging
            file_content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset pointer to beginning of file
            
            # Try to parse as JSON
            try:
                data = json.loads(file_content)
            except json.JSONDecodeError as je:
                # Provide more helpful error message with context
                error_line = je.lineno
                error_col = je.colno
                error_msg = je.msg
                context = file_content.decode('utf-8').split('\n')[max(0, error_line-3):error_line+2]
                
                # Create a more informative error message
                error_message = f"Fehler beim Lesen der JSON-Datei in Zeile {error_line}, Spalte {error_col}: {error_msg}"
                
                return None, {
                    'valid': False,
                    'warnings': [],
                    'error': error_message
                }
            except Exception as e:
                return None, {
                    'valid': False,
                    'warnings': [],
                    'error': f"Fehler beim Lesen der JSON-Datei: {str(e)}"
                }
        except Exception as e:
            return None, {
                'valid': False,
                'warnings': [],
                'error': f"Fehler beim Lesen der Datei: {str(e)}"
            }
        
        # Validate the data
        validation = FileImportExport.validate_json_import(data, file_type)
        
        return data, validation
    
    @staticmethod
    def get_filename(file_type: str) -> str:
        """Get the standard filename for a file type"""
        format_spec = FILE_FORMATS.get(file_type, {})
        return format_spec.get('filename', f'{file_type}.txt')
    
    @staticmethod
    def concatenate_buildings(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        """
        Concatenate new buildings to existing buildings with sequential IDs
        
        Args:
            existing_df: Existing buildings DataFrame
            new_df: New buildings DataFrame to append
            
        Returns:
            Combined DataFrame with sequential IDs
        """
        # Determine ID column
        id_col = None
        for col_name in ['building_id', 'id', 'ID', 'Building_ID']:
            if col_name in existing_df.columns:
                id_col = col_name
                break
        
        if id_col is None:
            id_col = 'building_id'
        
        # Get max existing ID
        if not existing_df.empty and id_col in existing_df.columns:
            max_id = existing_df[id_col].max()
        else:
            max_id = -1
        
        # Renumber new building IDs to continue from max
        new_df = new_df.copy()
        new_df[id_col] = range(max_id + 1, max_id + 1 + len(new_df))
        
        # Concatenate
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        
        return combined_df
