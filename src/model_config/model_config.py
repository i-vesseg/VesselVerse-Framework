from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Dict, List

@dataclass
class ModelConfig:
    """Configuration for a segmentation model"""
    name: str  # Full name (directory name)
    prefix: str  # Short prefix for unique keys
    owner: str  # Default owner
    filename_processor: Optional[Callable[[Path], Path]] = None

@dataclass
class DatasetConfig:
    """Configuration for a specific dataset"""
    name: str  # Dataset name (e.g., 'IXI', 'COW')
    unique_name: str  # Unique identifier for dataset (e.g., 'IXI_TOT', '301_CT23', '302_MR23', etc.)
    base_path: Path  # Base path for dataset
    image_dir: str  # Directory name for original images
    image_suffix: str  # File suffix for images (e.g., 'MRA', 'CTA')
    supported_models: List[str]  # List of supported model names
    modality: str  # Modality of images (e.g., 'MR', 'CT')
    year: Optional[str] = None  # Year of TOPCOW dataset (e.g., '23', '24')
    file_pattern: str = "*.nii.gz"  # File pattern for image files
    base_model_name: str = "TOT"  # Base model for STAPLE
    
    def get_image_path(self, case_id: str) -> Path:
        """Get path to original image for a case"""
        return self.base_path / self.image_dir / f"{case_id}.{self.image_suffix}"

class DatasetRegistry:
    """Registry of supported datasets"""
    def __init__(self):
        self.datasets: Dict[str, DatasetConfig] = {}
        self._register_default_datasets()
    
    def register_dataset(self, config: DatasetConfig):
        """Register a new dataset configuration"""
        #print("Registering dataset:", config.unique_name)
        self.datasets[config.unique_name] = config
    
    def get_dataset(self, name: str) -> Optional[DatasetConfig]:
        """Get dataset configuration by unique name"""
        return self.datasets.get(name)
    
    def get_dataset_by_unique_name(self, unique_name: str) -> Optional[DatasetConfig]:
        """Get dataset configuration by unique name"""
        for dataset in self.datasets.values():
            if dataset.unique_name == unique_name:
                return dataset
        return None
    
    def _register_default_datasets(self):
        """Register default supported datasets"""
        ################################### ADD HERE THE DATASETS THAT YOU WANT TO SUPPORT ###################################################
        ######################################################################################################################################
        ######################################################################################################################################
        ixi_config = DatasetConfig(
            name="IXI",
            unique_name="IXI",
            base_path=Path("../VESSELVERSE_DATA_IXI/data"),
            image_dir="IXI_TOT",
            image_suffix="nii.gz",
            modality="MR",
            supported_models=[
                "IXI_TOT",
                "STAPLE", "STAPLE_base",
                "StochasticAL", 
                "nnUNet",
                "A2V",
                "Filtering", 
                "ExpertAnnotations", "ExpertVAL"
            ]
        )
        
        topcow_config_23_CT = DatasetConfig(
            name="COW",
            unique_name="301_CT23",
            base_path=Path("../VESSELVERSE_DATA_COW/data/301_CT23"),
            image_dir="COW_TOT",
            image_suffix="nii.gz",
            modality="CT",
            year="23",
            supported_models=[
                "COW_TOT",
                "STAPLE", "STAPLE_base",
                "A2V",
                "COW_SEG",
                "JOB-VS",
                "ExpertAnnotations", "ExpertVAL"
            ]
        )
        
        topcow_config_23_MR = DatasetConfig(
            name="COW",
            unique_name="302_MR23",
            base_path=Path("../VESSELVERSE_DATA_COW/302_MR23/data"),
            image_dir="COW_TOT",
            image_suffix="nii.gz",
            modality="MR",
            year="23",
            supported_models=[
                "COW_TOT",
                "STAPLE", "STAPLE_base",
                "A2V",
                "StochasticAL",
                "nnUNet",
                "COW_SEG",
                "JOB-VS",
                "JOB-VS-SHINY-1", 
                "JOB-VS-SHINY-2",
                "ExpertAnnotations", 
                "ExpertVAL"
            ]
        )
        
        topcow_config_24_CT = DatasetConfig(
            name="COW",
            unique_name="303_CT24",
            base_path=Path("data/TOPCOW/303_CT24"),
            image_dir="COW_TOT",
            image_suffix="nii.gz",
            modality="CT",
            year="24",
            supported_models=[
                "COW_TOT",
                "STAPLE", "STAPLE_base",
                #"A2V",
                "COW_SEG",
                "JOB-VS",
                "ExpertAnnotations", "ExpertVAL"
            ]
        )
        
        topcow_config_24_MR = DatasetConfig(
            name="COW",
            unique_name="304_MR24",
            base_path=Path("data/TOPCOW/304_MR24"),
            image_dir="COW_TOT",
            image_suffix="nii.gz",
            modality="MR",
            year="24",
            supported_models=[
                "COW_TOT",
                "STAPLE", "STAPLE_base",
                #"A2V",
                "COW_SEG",
                "JOB-VS",
                "JOB-VS-SHINY-1",
                "ExpertAnnotations", "ExpertVAL"
            ]
        )
        
        ixi_costa_config = DatasetConfig(
            name="IXI",
            unique_name="IXI_COSTA",
            base_path=Path("../VESSELVERSE_DATA_IXI/IXI_ANNOT"),
            image_dir="IXI_TOT",
            image_suffix="nii.gz",
            modality="MR",
            supported_models=[
                "IXI_TOT",
                "IXI_EXP", 
                "COSTA",
                "ExpertAnnotations", "ExpertVAL"
            ]
        )

        
        self.register_dataset(ixi_config)
        self.register_dataset(topcow_config_23_CT)
        self.register_dataset(topcow_config_23_MR)
        self.register_dataset(topcow_config_24_CT)
        self.register_dataset(topcow_config_24_MR)
        
        self.register_dataset(ixi_costa_config)
        ################################################################################################################################
        ################################################################################################################################
        ################################################################################################################################
class ModelRegistry:
    """Registry of all supported models across datasets"""
    
    def __init__(self):
        self.models = {}
        self.dataset_registry = DatasetRegistry()
        self._register_default_models()
    
    def register_model(self, model_config: ModelConfig):
        """Register a new model configuration"""
        self.models[model_config.name] = model_config
    
    def get_model(self, name: str) -> Optional[ModelConfig]:
        """Get model configuration by name"""
        return self.models.get(name)
    
    def get_models_for_dataset(self, dataset_name: str) -> List[ModelConfig]:
        """Get all models supported by a specific dataset"""
        dataset_config = self.dataset_registry.get_dataset(dataset_name)
        if not dataset_config:
            return []
        return [
            model for model_name, model in self.models.items()
            if model_name in dataset_config.supported_models
        ]
    
    ####################################### Add here the models that you want to support ###########################################
    ################################################################################################################################
    ################################################################################################################################
    def _register_default_models(self):
        """Register default supported models"""
        # Helper functions for filename processing
        def process_nnunet(path: Path) -> Path:
            """Remove suffix and last character"""
            base = path.stem
            for suffix in ['-MRA', '-CTA']:
                base = base.replace(suffix, '')
            base = base.replace('.nii', '')
            
            if not path.with_name(f"{base[:-1]}.nii.gz").exists():
                return path.with_name(f"{base}.nii.gz")
            else:    
                return path.with_name(f"{base[:-1]}.nii.gz") 
            
        def process_stochastic(path: Path) -> Path:
            """Add vessel_mask suffix and restored prefix"""
            base = path.stem.replace('.nii', '')
            if path.with_name(f"restored_{base}_vessel_mask.nii.gz").exists():
                return path.with_name(f"restored_{base}_vessel_mask.nii.gz")
            else:
                return path.with_name(f"{base}.nii.gz") 
            
        def process_a2v(path: Path) -> Path:
            """Add pred suffix"""
            base = path.stem.replace('.nii', '')
            a2v_path = path.with_name(f"{base}.nii.gz")
            if not a2v_path.exists():
                a2v_path = path.with_name(f"{base}_pred.nii.gz")
            return a2v_path
        
        def process_shiny(path: Path) -> Path:
            """Add shiny suffix _0000"""
            base = path.stem.replace('.nii', '')
            return path.with_name(f"{base}_0000.nii.gz")
        
        def process_costa(path: Path) -> Path:
            """Add costa suffix"""
            base = path.stem.replace('.nii', '')
            ID = base.split('-')[0]
            if path.with_name(f"translated_{ID}_vessel_mask_int8.nii.gz").exists():
                return path.with_name(f"translated_{ID}_vessel_mask_int8.nii.gz")
            
            return path.with_name(f"translated_{ID}_vessel_mask.nii.gz")
        
        # Register default models
        default_models = [
            ModelConfig("IXI_TOT", "IXI", "ORIGINAL_IMG"),
            ModelConfig("COW_TOT", "TOP", "ORIGINAL_IMG"),
            
            ModelConfig("STAPLE", "STP", "STAPLE"),
            ModelConfig("STAPLE_base", "STB", "STAPLE_base"),
            
            ModelConfig("StochasticAL", "SAL", "AI", process_stochastic),
            ModelConfig("nnUNet", "UNet", "AI", process_nnunet),
            ModelConfig("A2V", "A2V", "AI", process_a2v),
            ModelConfig("COW_SEG", "COW", "AI"),
            ModelConfig("JOB-VS", "JobVs", "AI"),
            ModelConfig("JOB-VS-SHINY-1", "JobVsShiny1", "AI", process_shiny),
            ModelConfig("JOB-VS-SHINY-2", "JobVsShiny2", "AI", process_shiny),
            
            ModelConfig("Filtering", "FIL", "AI"),
            
            ModelConfig("ExpertAnnotations", "EXP", "Unknown"),
            ModelConfig("ExpertVAL", "EXPVAL", "Unknown"),
            
            ModelConfig("COSTA", "COSTA", "COSTA", process_costa),
            ModelConfig("IXI_EXP", "IXI_EXP", "MANUAL_SEG")
        ]
        
        for model in default_models:
            self.register_model(model)
    ################################################################################################################################
    ################################################################################################################################
    ################################################################################################################################
            
    def get_file_processor(self, model_name: str, dataset_name: str) -> Optional[Callable]:
        """Get the appropriate file processor for a model-dataset combination"""
        model = self.get_model(model_name)
        if not model:
            return None
            
        dataset = self.dataset_registry.get_dataset(dataset_name)
        if not dataset:
            return None
            
        if model_name not in dataset.supported_models:
            return None
            
        return model.filename_processor

# Global registry instances
model_registry = ModelRegistry()
dataset_registry = DatasetRegistry()