from pathlib import Path

import json, hashlib, datetime, sys
import numpy as np
import nibabel as nib

sys.path.append(str(Path(__file__).parent.parent))
from src.model_config.model_config import registry, ModelConfig

class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for NumPy types."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

class MetadataGenerator:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.metadata_dir = self.base_dir / "model_metadata"
    
    def generate_file_hash(self, file_path: Path) -> str:
        """Generate a hash for the file content."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()[:12]

    def determine_owner(self, file_path: Path, model_config: ModelConfig) -> str:
        """Determine the owner based on model config and filename patterns."""
        if model_config.name == "ExpertAnnotations":
            parts = file_path.stem.split('_')
            if len(parts) > 1:
                return parts[0]
        return model_config.owner

    def extract_file_prefix(self, filename: str) -> str:
        """Extract the IXI prefix from filename."""
        base_name = Path(filename).stem
        base_name = base_name.replace('.nii', '')
        return base_name[:6]

    def generate_metadata(self, file_path: Path, model_config: ModelConfig) -> dict:
        """Generate metadata for a NIfTI file."""
        img = nib.load(str(file_path))
        
        file_hash = self.generate_file_hash(file_path)
        timestamp = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
        file_prefix = self.extract_file_prefix(file_path.name)
        
        unique_key = f"{file_prefix}_{model_config.prefix}_{file_hash}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "unique_key": unique_key,
            "owner": self.determine_owner(file_path, model_config),
            "model": model_config.name,
            "filename": file_path.name,
            "path": str(file_path),
            "creation_date": datetime.datetime.fromtimestamp(
                file_path.stat().st_ctime
            ).isoformat(),
            "last_modified": datetime.datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat(),
            "size_bytes": file_path.stat().st_size,
            "file_hash": file_hash,
            "shape": tuple(int(x) for x in img.shape),
            "affine": img.affine.tolist(),
            "header": {
                "dim": [int(x) for x in img.header["dim"]],
                "pixdim": [float(x) for x in img.header["pixdim"]],
                "description": str(img.header.get("description", "")),
            }
        }

    def process_directory(self, model_config: ModelConfig):
        """Process all NIfTI files for a model and save metadata."""
        dir_path = self.base_dir / model_config.name
        if not dir_path.exists():
            print(f"Directory not found: {dir_path}")
            return
            
        metadata_dict = {}
        
        for file_path in dir_path.rglob("*.nii.gz"):
            try:
                relative_path = str(file_path.relative_to(dir_path))
                metadata = self.generate_metadata(file_path, model_config)
                metadata_dict[metadata["unique_key"]] = {
                    "relative_path": relative_path,
                    **metadata
                }
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        # Save metadata
        output_file = self.metadata_dir / f"{model_config.name}_metadata.json"
        with open(output_file, 'w') as f:
            json.dump(metadata_dict, f, indent=2, cls=NumpyJSONEncoder)
        
        print(f"Generated metadata for {model_config.name}")

    def generate_all(self):
        """Generate metadata for all registered models."""
        self.metadata_dir.mkdir(exist_ok=True)
        
        for model_config in registry.models.values():
            if model_config.name == 'ExpertAnnotations':
                continue
            self.process_directory(model_config)

def main():
    generator = MetadataGenerator(Path("data"))
    generator.generate_all()

if __name__ == "__main__":
    main()