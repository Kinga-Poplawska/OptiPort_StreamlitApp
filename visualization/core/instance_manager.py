"""
Instance management for discovering and loading optimization instances
"""
import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

from .data_models import InstanceMetadata, OptimizationSolution
from .solution_parser import SolutionParser
from config.app_config import USE_CASES_PATH, INSTANCES_PATH, INSTANCE_CONFIG_FILES, SOLUTION_FILE_PATTERN

logger = logging.getLogger(__name__)

class InstanceManager:
    """Manages optimization instances and their metadata"""
    
    def __init__(self, use_case_name: str = None):
        self.solution_parser = SolutionParser()
        self.use_cases_path = USE_CASES_PATH
        self.instances_path = INSTANCES_PATH

    def discover_instances(self) -> List[InstanceMetadata]:
        """Discover all available instances in use_cases and data/instances"""
        instances = []
        
        # Check use_cases directory
        if self.use_cases_path.exists():
            instances.extend(self._scan_directory(self.use_cases_path, "use_case"))
            
        # Check data/instances directory  
        if self.instances_path.exists():
            instances.extend(self._scan_directory(self.instances_path, "data_instance"))
            
        logger.info(f"Discovered {len(instances)} instances")
        return instances
    
    def _scan_directory(self, directory: Path, instance_type: str) -> List[InstanceMetadata]:
        """Scan a directory for instances"""
        instances = []
        
        try:
            for item in directory.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    instance = self._create_instance_metadata(item, instance_type)
                    if instance:
                        instances.append(instance)
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
            
        return instances
    
    def _create_instance_metadata(self, instance_path: Path, instance_type: str) -> Optional[InstanceMetadata]:
        """Create instance metadata from a directory"""
        try:
            # Get basic info
            stat = instance_path.stat()
            created_date = datetime.fromtimestamp(stat.st_ctime)
            modified_date = datetime.fromtimestamp(stat.st_mtime)
            
            # Check for config files
            config_files = {}
            for config_file in INSTANCE_CONFIG_FILES:
                file_path = instance_path / config_file
                if file_path.exists():
                    config_files[config_file] = file_path
            
            # Look for solution file
            solution_path = None
            has_solution = False
            
            # Check in results subdirectory first
            results_dir = instance_path / "results"
            if results_dir.exists():
                for sol_file in results_dir.glob(SOLUTION_FILE_PATTERN):
                    solution_path = sol_file
                    has_solution = True
                    break
            
            # Check in main directory if not found in results
            if not has_solution:
                for sol_file in instance_path.glob(SOLUTION_FILE_PATTERN):
                    solution_path = sol_file
                    has_solution = True
                    break
            
            # Try to extract additional metadata from config files
            num_buildings = None
            num_time_periods = None
            description = None
            
            if "stock_properties.csv" in config_files:
                num_buildings = self._count_buildings_from_csv(config_files["stock_properties.csv"])
                
            if "general_finances.json" in config_files:
                description, num_time_periods = self._extract_from_json(config_files["general_finances.json"])
            
            return InstanceMetadata(
                name=instance_path.name,
                path=instance_path,
                description=description or f"{instance_type.replace('_', ' ').title()}: {instance_path.name}",
                created_date=created_date,
                modified_date=modified_date,
                num_buildings=num_buildings,
                num_time_periods=num_time_periods,
                has_solution=has_solution,
                solution_path=solution_path,
                config_files=config_files
            )
            
        except Exception as e:
            logger.error(f"Error creating metadata for {instance_path}: {e}")
            return None
    
    def _count_buildings_from_csv(self, csv_path: Path) -> Optional[int]:
        """Count buildings from stock properties CSV"""
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            return len(df)
        except Exception as e:
            logger.warning(f"Could not count buildings from {csv_path}: {e}")
            return None
    
    def _extract_from_json(self, json_path: Path) -> tuple[Optional[str], Optional[int]]:
        """Extract description and time periods from JSON config"""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            description = data.get("description", None)
            
            # Try to infer time periods from various possible keys
            time_periods = None
            for key in ["time_periods", "num_time_periods", "periods", "time_horizon"]:
                if key in data:
                    time_periods = data[key]
                    if isinstance(time_periods, list):
                        time_periods = len(time_periods)
                    break
            
            return description, time_periods
            
        except Exception as e:
            logger.warning(f"Could not extract metadata from {json_path}: {e}")
            return None, None
    
    def load_instance_solution(self, instance: InstanceMetadata) -> Optional[OptimizationSolution]:
        """Load the solution for an instance"""
        if not instance.has_solution or not instance.solution_path:
            logger.warning(f"No solution available for instance {instance.name}")
            return None
            
        try:
            return self.solution_parser.parse_solution_file(instance.solution_path)
        except Exception as e:
            logger.error(f"Error loading solution for {instance.name}: {e}")
            return None
    
    def get_instance_by_name(self, name: str) -> Optional[InstanceMetadata]:
        """Get a specific instance by name"""
        instances = self.discover_instances()
        for instance in instances:
            if instance.name == name:
                return instance
        return None
    
    def validate_instance(self, instance: InstanceMetadata) -> Dict[str, bool]:
        """Validate an instance's completeness"""
        validation = {
            "has_directory": instance.path.exists(),
            "has_config_files": len(instance.config_files) > 0,
            "has_solution": instance.has_solution,
            "is_complete": False
        }
        
        # Check for minimum required files
        required_files = ["stock_properties.csv", "financial_properties.csv"]
        has_required = all(file in instance.config_files for file in required_files)
        
        validation["has_required_files"] = has_required
        validation["is_complete"] = all([
            validation["has_directory"],
            validation["has_config_files"], 
            validation["has_required_files"]
        ])
        
        return validation

    def load_instance_from_pickle(self, use_case_name: str):
        """Load an instance from a pickle file in USE_CASES_PATH"""
        pkl_path = USE_CASES_PATH / use_case_name / f"{use_case_name}.pkl"
        if not pkl_path.exists():
            raise FileNotFoundError(f"Instance file not found: {pkl_path}")
        with open(pkl_path, "rb") as f:
            instance_data = pickle.load(f)
        return instance_data
