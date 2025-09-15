import sys
import nibabel as nib
from pathlib import Path
from typing import Dict, List, Optional, Callable
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))
from model_config.model_config import model_registry as registry

class DatasetConfig:
    def __init__(
        self,
        name: str,
        file_pattern: str = "*.nii.gz",
        base_model_name: str = "TOT",
        excluded_models: List[str] = None,
        filename_processor: Optional[Callable] = None
    ):
        self.name = name
        self.file_pattern = file_pattern
        self.base_model_name = base_model_name
        self.excluded_models = excluded_models or [f"{name}_{base_model_name}"]
        self.filename_processor = filename_processor

class MedicalImageDataset:
    def __init__(
        self, 
        base_path: str, 
        dataset_config: DatasetConfig,
        supported_models: List[str] = None,
        verbose: bool = True
        
    ):
        self.base_path = Path(base_path)
        self.config = dataset_config
        self.supported_models = supported_models
        self.verbose = verbose
        
        if self.verbose:
            print(f"Initializing {self.config.name} Dataset from {self.base_path}")
            print(f"Absolute path: {self.base_path.resolve()}")
            
        self._setup_paths()
        self._validate_paths()
        self._scan_files()
        self._setup_models()

    def _setup_models(self):
        """Set up list of models excluding those specified in config"""
        self.models_list = [
            model.name for model in registry.models.values()
            if model.name != f'{self.config.name}_{self.config.base_model_name}'
            and model.name in self.config.supported_models
        ]

    def _setup_paths(self):
        """Set up paths for each model"""
        self.paths = {}
        for model in self.supported_models:
            print(f"Setting up paths for {model}")
            self.paths[model] = self.base_path / model

    def _scan_files(self):
        """Scan for dataset files using configured pattern"""
        if self.verbose:
            print(f"Scanning for {self.config.name} files...")
            
        base_model = f'{self.config.name}_{self.config.base_model_name}'
        print(base_model)
        self.files = list(self.paths[base_model].rglob(self.config.file_pattern))
        self.file_count = len(self.files)
        
        if self.verbose:
            print(f"Found {self.file_count} files in {base_model}")
            if self.files:
                print(f"First file: {sorted(self.files)[0].name}")
                print(f"Last file: {sorted(self.files)[-1].name}")

    def _validate_paths(self):
        """Validate and create directory structures"""
        if self.verbose:
            print("Validating directory structures...")
            
        for name, path in self.paths.items():
            if name not in ['STAPLE', 'STAPLE_base']:
                Path(path).mkdir(parents=True, exist_ok=True)
            if self.verbose:
                n_files = len(list(path.rglob(self.config.file_pattern)))
                print(f"  {name}: {path} ({n_files} files)")

    def get_model_path(
        self, 
        source_path: Path, 
        model_name: str, 
        do_not_verify: bool = False
    ) -> Path:
        """Get path for a specific model's output"""
        model_config = registry.get_model(model_name)
        if not model_config:
            raise ValueError(f'Unknown model: {model_name}')
            
        base_model = f'{self.config.name}_{self.config.base_model_name}'
        model_path = self.paths[model_name] / source_path.relative_to(self.paths[base_model])
        
        if model_config.filename_processor:
            model_path = model_config.filename_processor(model_path)
        if not do_not_verify:
            assert model_path.exists(), f'{model_name} segmentation not found: {model_path}'
        return model_path

    def load_case(self, idx: int) -> Dict:
        """
        Load a single case with all its corresponding segmentations.
        
        Returns:
            Dict containing:
                - 'image': Original image
                - 'staple': STAPLE segmentation
                - 'segmentations': Dict of model segmentations
                - 'paths': Dict of all paths
        """
        assert 0 <= idx < self.file_count, f'Index {idx} out of range [0, {self.file_count})'
        
        source_path = self.files[idx]
        if self.verbose:
            print(f"\nLoading case {idx}: {source_path.name}")
            print("  Loading original image...")
        
        result = {
            'image': nib.load(source_path),
            'paths': {'image': source_path}
        }
        
        if self.verbose:
            print("  Loading STAPLE segmentation...")
        staple_path = self.get_model_path(source_path, 'STAPLE')
        result['staple'] = nib.load(staple_path)
        result['paths']['staple'] = staple_path
        
        # Load all model segmentations
        result['segmentations'] = {}
        for model in self.models_list:
            if self.verbose:
                print(f"  Loading {model} segmentation...")
            try:
                model_path = self.get_model_path(source_path, model)
                result['segmentations'][model] = nib.load(model_path)
                result['paths'][model] = model_path
            except AssertionError as e:
                if self.verbose:
                    print(f"  Warning: {model} segmentation not found")
                continue
            
        if self.verbose:
            print("  Case loaded successfully")
        return result

    def compute_staple(
        self, 
        create_staple_consensus_fn: Callable, 
        force_recompute: bool = False,
        **kwargs
    ):
        """
        Compute STAPLE consensus for all cases if not already computed.
        
        Args:
            create_staple_consensus_fn: Function to create STAPLE consensus
            force_recompute: If True, recompute STAPLE even if it exists
            **kwargs: Additional arguments passed to create_staple_consensus_fn
        """
        import gc
        gc.collect()  
        if self.verbose:
            print("\nChecking/Computing STAPLE segmentations...")
        
        # Create STAPLE directories
        Path(self.paths['STAPLE']).mkdir(parents=True, exist_ok=True)
        Path(self.paths['STAPLE_base']).mkdir(parents=True, exist_ok=True)
        
        # Process each case
        for source_path in tqdm(sorted(self.files), desc="Computing STAPLE"):
            gc.collect()
            # Get paths
            patient = source_path.stem.split('.')[0]
            output_path = self.get_model_path(source_path, 'STAPLE', do_not_verify=True)
            
            # Skip if exists and not forcing recompute
            if output_path.exists() and not force_recompute:
                if self.verbose:
                    print(f"STAPLE exists for {patient}, skipping...")
                continue
            
            # Get segmentation paths for all models
            segmentation_paths = []
            for model in self.models_list:
                try:
                    #print(f"Getting segmentation path for {model} and {patient}")
                    seg_path = self.get_model_path(source_path, model)
                    segmentation_paths.append(str(seg_path))
                except AssertionError as e:
                    if self.verbose and model not in ['STAPLE', 'STAPLE_base']:
                        print(f"Warning: {model} segmentation not found for {patient}")
                    continue
            
            if len(segmentation_paths) < 2:
                print(f"Only {len(segmentation_paths)} segmentations found for {patient}, skipping...")
                continue
                
            # Create STAPLE consensus
            if self.verbose:
                print(f"Computing STAPLE for {patient} with paths:")
                for segmenation_path in segmentation_paths:
                    print(segmenation_path)
                print(f"\nOutput path: {output_path}\n\n")
            # Compute enhanced STAPLE
            consensus = create_staple_consensus_fn(
                str(source_path),
                segmentation_paths,
                str(output_path),
                **kwargs
            )
            
            # Compute base STAPLE without enhancements
            base_output_path = str(output_path).replace('/STAPLE/', '/STAPLE_base/')
            base_kwargs = {**kwargs}
            base_kwargs.update({
                'do_preprocessing': False,
                'do_adaptive_thresholding': False,
                'do_vessel_enhancement': False
            })
            
            consensus = create_staple_consensus_fn(
                str(source_path),
                segmentation_paths,
                base_output_path,
                **base_kwargs
            )
            
            if self.verbose:
                print(f"STAPLE computed for {patient}")

    def verify_staple_existence(self) -> List[str]:
        """
        Verify that STAPLE segmentations exist for all cases.
        
        Returns:
            List of cases missing STAPLE segmentation
        """
        missing_cases = []
        if self.verbose:
            print("\nVerifying STAPLE segmentations...")
        
        for source_path in tqdm(self.files, desc="Verifying STAPLE"):
            try:
                _ = self.get_model_path(source_path, 'STAPLE')
            except AssertionError:
                missing_cases.append(source_path.name)
        
        if self.verbose:
            print(f"\nFound {len(self.files) - len(missing_cases)} STAPLE segmentations")
            
            if missing_cases:
                print(f"\nMissing STAPLE segmentations for {len(missing_cases)} cases:")
                for case in missing_cases:
                    print(f"  {case}")
            else:
                print("\nSTAPLE segmentations exist for all cases")
            
        return missing_cases

    def visualize_case(
        self, 
        idx: int, 
        interactive_segmentation_viewer: Callable,
        mask_alpha: float = 0.9,
        base_width: int = 3,
        holoviews: bool = False,
        **kwargs
    ):
        """
        Visualize a case using the interactive segmentation viewer.
        
        Args:
            idx: Index of the case to visualize
            interactive_segmentation_viewer: Visualization function
            mask_alpha: Transparency of the segmentation masks (0-1)
            base_width: Base width for the visualization
            holoviews: If True, return layout instead of showing viewer
            **kwargs: Additional arguments passed to viewer
        """
        case = self.load_case(idx)
        source_path = case['paths']['image']
        
        # Get segmentation paths
        segmentation_paths = []
        for model in self.models_list:
            try:
                seg_path = str(case['paths'][model])
                segmentation_paths.append(seg_path)
            except KeyError:
                if self.verbose:
                    print(f"Warning: {model} segmentation not found")
                continue
        
        binary_consensus = nib.load(case['paths']['staple']).get_fdata()
        
        if self.verbose:
            print(f"\nVisualizing case {idx}: {source_path.name}")
            print(f"Number of segmentations: {len(segmentation_paths)}")
        
        viewer_args = {
            'mask_alpha': mask_alpha,
            'base_width': base_width,
            'raters': self.models_list,
            **kwargs
        }
        
        if holoviews:
            return interactive_segmentation_viewer(
                str(source_path),
                segmentation_paths,
                binary_consensus,
                **viewer_args
            )
        
        interactive_segmentation_viewer(
            str(source_path),
            segmentation_paths,
            binary_consensus,
            **viewer_args
        )

    def __len__(self) -> int:
        return self.file_count
    
    def __getitem__(self, idx: int) -> Dict:
        return self.load_case(idx)
    
    def print_case_info(self, case: Dict):
        """Print information about a loaded case."""
        print("\nCase Information:")
        print(f"Image path: {case['paths']['image']} (Shape: {case['image'].shape})")
        print(f"STAPLE path: {case['paths']['staple']}")
        print("Segmentation paths:")
        for model, path in case['paths'].items():
            if model not in ['image', 'staple']:
                print(f"  {model}: {path}")
        