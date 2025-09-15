#!/usr/bin/env python3
import sys, yaml, json, argparse
from pathlib import Path
from datetime import datetime

# Add the project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.dataset import MedicalImageDataset
from src.core.staple import create_staple_consensus
from src.model_config.model_config import dataset_registry

def validate_dataset(dataset_name: str) -> bool:
    """Validate that the dataset exists in the registry"""
    print(f"Validating dataset: {dataset_name}")
    print("Available datasets:", list(dataset_registry.datasets.keys()))
    if dataset_name not in dataset_registry.datasets:
        print(f"Error: Dataset '{dataset_name}' not found in registry.")
        print("Available datasets:", list(dataset_registry.datasets.keys()))
        return False
    print(f"Dataset '{dataset_name}' PRESENT in registry.")
    return True

def load_staple_params(dataset_name: str) -> dict:
    """Load and merge STAPLE parameters for specific dataset"""
    yaml_file = Path(__file__).parent / "staple_params.yaml"
    assert yaml_file.exists(), f"File not found: {yaml_file}"
    
    with open(yaml_file, 'r') as f:
        params = yaml.safe_load(f)
    
    # Get dataset configuration
    dataset_config = dataset_registry.get_dataset(dataset_name)
    
    # Check for modality-specific parameters first
    modality_params = params.get('modalities', {}).get(dataset_config.modality, {})
    
    # Then check for year-specific parameters (for TOPCOW)
    year_params = {}
    if dataset_config.year:
        year_params = params.get('years', {}).get(dataset_config.year, {})
    
    # Finally, check for dataset-specific parameters
    dataset_params = params.get('datasets', {}).get(dataset_name, {})
    
    # Merge parameters in order of specificity
    base_params = params.get('staple', {})
    final_params = {
        **base_params,
        **modality_params,
        **year_params,
        **dataset_params
    }
    
    return final_params

def initialize_dataset(base_path: str, dataset_name: str, dataset_unique_name: str, verbose: bool = True) -> MedicalImageDataset:
    """Initialize dataset using registry configuration"""
    print(f"Dataset name: {dataset_name}")
    dataset_config = dataset_registry.get_dataset_by_unique_name(dataset_unique_name)
    if not dataset_config:
        assert()
        raise ValueError(f"Dataset '{dataset_name}' not found in registry")
    
    # Update base path if provided
    if base_path:
        # For TOPCOW subdivisions, append the specific directory
        if dataset_name.startswith("30"):
            dataset_config.base_path = Path(base_path) / dataset_name
        else:
            dataset_config.base_path = Path(base_path)
    
    if verbose:
        print(f"\nInitializing dataset: {dataset_name}")
        print(f"Base path: {dataset_config.base_path}")
        print(f"Modality: {dataset_config.modality}")
        if dataset_config.year:
            print(f"Year: {dataset_config.year}")
        print(f"Supported models: {dataset_config.supported_models}\n")
    
    return MedicalImageDataset(
        base_path=dataset_config.base_path,
        dataset_config=dataset_config,
        supported_models=dataset_config.supported_models,
        verbose=verbose,
    )

def main(base_path: str, dataset_name: str, dataset_unique: str):
    """Main function to compute STAPLE consensus"""
    # Validate dataset exists in registry
    if not validate_dataset(dataset_unique):
        return
    # Load parameters
    staple_params = load_staple_params(dataset_unique)
    
    # Initialize dataset
    dataset = initialize_dataset(base_path, dataset_name, dataset_unique)
    
    # Compute STAPLE
    dataset.compute_staple(
        create_staple_consensus_fn=create_staple_consensus,
        force_recompute=staple_params.get('force_recompute', False),
        confidence_threshold=staple_params.get('confidence_threshold', 0.8),
    )
    
    # Verify results
    missing_cases = dataset.verify_staple_existence()
    
    # Save metrics
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'dataset': dataset_name,
        'modality': dataset.config.modality,
        'year': dataset.config.year,
        'total_cases': len(dataset),
        'missing_cases': len(missing_cases),
        'success_rate': (len(dataset) - len(missing_cases)) / len(dataset) * 100,
        'parameters': staple_params
    }
    
    # Create metrics directory if it doesn't exist
    metrics_dir = Path('metrics')
    metrics_dir.mkdir(exist_ok=True)
    
    # Save metrics with dataset-specific filename
    metrics_file = metrics_dir / f"staple_computation_{dataset_name.lower()}.json"
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    # Print summary
    print("\nSTAPLE Computation Summary:")
    print(f"Dataset: {dataset_name}")
    print(f"Modality: {dataset.config.modality}")
    if dataset.config.year:
        print(f"Year: {dataset.config.year}")
    print(f"Total cases: {len(dataset)}")
    print(f"Successfully processed: {len(dataset) - len(missing_cases)}")
    print(f"Success rate: {metrics['success_rate']:.2f}%")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Compute STAPLE consensus for medical image dataset')
    parser.add_argument('--base_path', type=str, help='Base path to dataset directory')
    parser.add_argument('--dataset', type=str, required=True,
                      help='Dataset name (e.g., IXI, COW, etc.)')

    args = parser.parse_args()
    # Remove trailing "/" from base path if present
    if args.base_path and args.base_path.endswith("/"):
        args.base_path = args.base_path[:-1]
    dataset_unique = args.base_path.split("/")[-1]
    if 'IXI' in dataset_unique:
        dataset_unique = 'IXI'
    print(f"Dataset unique name: {dataset_unique}")
    main(args.base_path, args.dataset, dataset_unique)
    

#python scripts_py/compute_staple.py --dataset COW --base_path ../VESSELVERSE_DATA_COW/302_MR23/
#python scripts_py/compute_staple.py --dataset IXI --base_path ../VESSELVERSE_DATA_IXI/
