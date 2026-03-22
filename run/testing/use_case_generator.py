"""
Synthetic use case generator wrapper for testing.
"""

import sys
from pathlib import Path
from typing import List, Dict
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.use_case_generator.generator import UseCaseGenerator
import run.testing.config as test_config
from run.testing.logger import get_logger


class TestUseCaseGenerator:
    """Wrapper for generating multiple synthetic test use cases."""
    
    def __init__(self):
        self.generated_use_cases: List[Dict] = []
        self.logger = get_logger()

    def generate_test_instances(self, num_instances: int = None) -> List[Dict]:
        """Generate multiple synthetic test use cases (one instance per test)."""
        if num_instances is None:
            num_instances = test_config.NUM_TEST_INSTANCES

        self.logger.section(f"GENERATING {num_instances} TEST USE CASES")

        use_cases = []

        for i in range(num_instances):
            instance_id = i + 1
            seed = test_config.BASE_SEED + instance_id

            rng = random.Random(seed)
            num_buildings = rng.randint(
                test_config.NUM_BUILDINGS_RANGE["min"],
                test_config.NUM_BUILDINGS_RANGE["max"]
            )
            num_time_periods = rng.randint(
                test_config.NUM_TIME_PERIODS_RANGE["min"],
                test_config.NUM_TIME_PERIODS_RANGE["max"]
            )

            use_case_name = f"{test_config.USE_CASE_NAME_PREFIX}_{instance_id:03d}"

            metadata = {
                'use_case_name': use_case_name,
                'num_buildings': num_buildings,
                'num_time_periods': num_time_periods,
                'seed': seed,
                'instance_id': instance_id
            }

            self.logger.verbose(
                f"Generating [{instance_id}/{num_instances}] {use_case_name}: "
                f"{num_buildings} buildings, {num_time_periods} periods"
            )

            try:
                from data.use_case_generator.config import GENERATOR_CONFIG
                custom_config = GENERATOR_CONFIG.copy()

                if hasattr(test_config, 'NUM_FLATS_RANGE'):
                    custom_config['num_flats_range'] = test_config.NUM_FLATS_RANGE

                generator = UseCaseGenerator(config=custom_config, seed=seed)
                # Generate once - benders_decomp_name will be used when running tests
                generator.generate(use_case_name, num_buildings, num_time_periods)
                metadata['status'] = 'success'
                self.logger.debug(f"Successfully generated {use_case_name}")

            except Exception as e:
                metadata['status'] = 'failed'
                metadata['error'] = str(e)
                self.logger.error(f"Failed to generate {use_case_name}: {e}")

                if not test_config.CONTINUE_ON_ERROR:
                    raise

            use_cases.append(metadata)

        self.generated_use_cases = use_cases

        successful = sum(1 for uc in use_cases if uc['status'] == 'success')
        failed = sum(1 for uc in use_cases if uc['status'] == 'failed')

        self.logger.info(f"\nGeneration complete: {successful} successful, {failed} failed")

        if successful > 0:
            avg_buildings = sum(uc['num_buildings'] for uc in use_cases
                                if uc['status'] == 'success') / successful
            avg_periods = sum(uc['num_time_periods'] for uc in use_cases
                              if uc['status'] == 'success') / successful
            self.logger.verbose(f"Averages: {avg_buildings:.1f} buildings, {avg_periods:.1f} periods")

        return use_cases

    def get_successful_use_cases(self) -> List[Dict]:
        """Get only successfully generated use cases."""
        return [uc for uc in self.generated_use_cases if uc['status'] == 'success']
    
    def get_use_case_names(self) -> List[str]:
        """Get list of successfully generated use case names."""
        return [uc['use_case_name'] for uc in self.get_successful_use_cases()]


def main():
    """Test the use case generator."""
    generator = TestUseCaseGenerator()
    use_cases = generator.generate_test_instances()
    
    logger = get_logger()
    logger.info("\nGenerated use cases:")
    for uc in use_cases:
        status = "success" if uc['status'] == 'success' else "failed"
        logger.info(
            f"  [{status}] {uc['use_case_name']}: "
            f"{uc['num_buildings']} buildings, {uc['num_time_periods']} periods"
        )


if __name__ == "__main__":
    main()
