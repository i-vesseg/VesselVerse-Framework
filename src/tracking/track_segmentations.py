#!/usr/bin/env python3
import sys, json, argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.append(str(Path(__file__).parent.parent))
from model_config.model_config import registry

class SegmentationTracker:
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path).resolve()
        self.model_metadata_path = self.base_path / "model_metadata"
        self.expert_metadata_path = self.base_path / "metadata"
        self.model_metadata = self._load_model_metadata()
        self.expert_metadata = self._load_expert_metadata()
        self.path_mapping = {}

    def _load_model_metadata(self) -> Dict:
        metadata = {}
        for model_config in registry.models.values():
            json_file = self.model_metadata_path / f"{model_config.name}_metadata.json"
            if json_file.exists():
                with open(json_file) as f:
                    metadata[model_config.name] = json.load(f)
        return metadata

    def _load_expert_metadata(self) -> Dict:
        metadata = {}
        for json_file in self.expert_metadata_path.glob("*_expert_metadata.json"):
            with open(json_file) as f:
                metadata[json_file.stem.split('_')[0]] = json.load(f)
        return metadata

    def _normalize_path(self, path: Path) -> Path:
        try:
            return path.resolve() if path.is_absolute() else (self.base_path / path).resolve()
        except Exception:
            return path

    def list_all_segmentations(self) -> List[Tuple[int, str, str]]:
        all_paths = []
        
        # Add paths from registered models
        for model_name, model_data in self.model_metadata.items():
            model_config = registry.get_model(model_name)
            if not model_config:
                continue
                
            for entry in model_data.values():
                try:
                    path = self._normalize_path(Path(entry['relative_path']))
                    if path.exists():
                        all_paths.append((str(path), model_config.name))
                except Exception as e:
                    print(f"Error processing path for {model_name}: {e}")

        # Add expert annotations
        for model_name, model_data in self.expert_metadata.items():
            for entry in model_data.values():
                try:
                    path = self._normalize_path(Path(entry['relative_path']))
                    if path.exists():
                        all_paths.append((str(path), "ExpertAnnotations"))
                except Exception as e:
                    print(f"Error processing expert path: {e}")

        unique_paths = sorted(set(all_paths))
        numbered_paths = [(i+1, path, model) for i, (path, model) in enumerate(unique_paths)]
        self.path_mapping = {i: path for i, path, _ in numbered_paths}
        return numbered_paths

    def _find_metadata_entry(self, seg_path: Path) -> Optional[tuple]:
        try:
            rel_path = str(seg_path.relative_to(self.base_path))
        except ValueError:
            rel_path = str(seg_path)

        # Check expert metadata first
        for model_name, model_data in self.expert_metadata.items():
            for key, entry in model_data.items():
                if entry['relative_path'] == rel_path or entry['path'] == str(seg_path):
                    return ('expert', model_name, key, entry)

        # Then check model metadata
        for model_config in registry.models.values():
            model_data = self.model_metadata.get(model_config.name, {})
            for key, entry in model_data.items():
                if (entry['relative_path'] == rel_path or 
                    entry['path'] == str(seg_path) or
                    entry['filename'] == seg_path.name):
                    return ('model', model_config.name, key, entry)

        return None

    def _find_complete_metadata_entry(self, seg_path: Path) -> Optional[Dict]:
        for model_name, model_data in self.expert_metadata.items():
            for key, entry in model_data.items():
                if entry['relative_path'] == str(seg_path.relative_to(self.base_path)) or entry['path'] == str(seg_path):
                    print(f"Found expert metadata for {seg_path}")
                    return entry
                
    def track_history(self, seg_path: str) -> List[Dict]:
        history = []
        current_path = self._normalize_path(Path(seg_path))
        visited_paths = set()

        while str(current_path) not in visited_paths and current_path.exists():
            visited_paths.add(str(current_path))
            entry_info = self._find_metadata_entry(current_path)

            if not entry_info:
                # Try to infer model from path
                for model_config in registry.models.values():
                    if model_config.name.lower() in str(current_path).lower():
                        model_data = self.model_metadata.get(model_config.name, {})
                        for key, entry in model_data.items():
                            if any(part in str(current_path) for part in entry['filename'].split('-')):
                                entry_info = ('model', model_config.name, key, entry)
                                break
                if not entry_info:
                    break

            entry_type, model_name, key, entry = entry_info
            history_entry = {
                'path': str(current_path),
                'type': entry_type,
                'model': model_name,
                'owner': entry.get('owner', 'Unknown'),
                'creation_date': entry.get('creation_date', 'Unknown'),
                'notes': entry.get('notes', '')
            }
            history.append(history_entry)

            orig_path = entry.get('original_segmentation_path')
            if not orig_path:
                break

            current_path = self._normalize_path(Path(orig_path))
            if str(current_path) in visited_paths:
                break

        return history

    def print_history(self, seg_path: str):
        history = self.track_history(seg_path)
        if not history:
            print(f"No history found for {seg_path}")
            return

        print("\nSegmentation History:")
        print("=" * 80)

        for i, entry in enumerate(history, 1):
            print(f"\nVersion {len(history) - i + 1}:")
            print(f"  Path: {entry['path']}")
            print(f"  Type: {entry['type']}")
            print(f"  Model: {entry['model']}")
            print(f"  Owner: {entry['owner']}")
            print(f"  Created: {entry['creation_date']}")
            if entry['notes']:
                print(f"  Notes: {entry['notes']}")
                
            if i < len(history):
                print("\n  ↓ (Modified from...) ↓")
    
    def print_metadata(self, seg_path: str):
        """Print metadata for a segmentation."""
        seg_path = self._normalize_path(Path(seg_path))
        entry_info = self._find_metadata_entry(seg_path)
        
        if not entry_info:
            print(f"No metadata found for {seg_path}")
            return
        
        entry_type, model_name, key, entry = entry_info
        print("\nSegmentation Metadata:")
        print("=" * 80)
        print(f"  Path: {seg_path}")
        print(f"  Type: {entry_type}")
        print(f"  Model: {model_name}")
        print(f"  Owner: {entry.get('owner', 'Unknown')}")
        print(f"  Created: {entry.get('creation_date', 'Unknown')}")
        print(f"  Notes: {entry.get('notes', '')}")
        
    def print_metadata_complete(self, seg_path: str):
        """Print complete metadata for a segmentation."""
        seg_path = self._normalize_path(Path(seg_path))
        entry_info = self._find_complete_metadata_entry(seg_path)
        
        if not entry_info:
            print(f"No metadata found for {seg_path}")
            return
        
        print("\nComplete Segmentation Metadata:")
        print("=" * 80)
        for key, value in entry_info.items():
            print(f"  {key}: {value}")
    
    def track_by_id(self, seg_id: int):
        """Track history of a segmentation by its ID."""
        if seg_id not in self.path_mapping:
            print(f"Error: Invalid ID {seg_id} provided: Max ID is {len(self.path_mapping)}")
            return -1
        
        self.print_history(self.path_mapping[seg_id])

def print_segmentation_list(segmentations):
    """Print the list of segmentations with IDs."""
    print("\nAll Segmentations:")
    print("=" * 80)
    if not segmentations:
        print("No segmentations found!")
    else:
        print(f"[{'ID':>3}] {'Model':20} | {'File name':50} | {'Path'}")
        for id_num, path, model in segmentations:
            print(f"[{id_num:3d}] {model:20} | {Path(path).name:50} | | {Path(path).parent}")

def main():
    parser = argparse.ArgumentParser(description='Track segmentation history')
    parser.add_argument('--list', action='store_true', help='List all segmentation paths')
    parser.add_argument('--track', type=str, help='Track history of specific segmentation')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--base-path', type=str, default='data', 
                      help='Base path for data directory (default: data)')
    
    args = parser.parse_args()
    
    tracker = SegmentationTracker(base_path=args.base_path)
    segmentations = tracker.list_all_segmentations()
    
    if args.list or args.interactive:
        print_segmentation_list(segmentations)
    
    if args.interactive:
        print("\nCommands:")
        print("  - Enter a number to track history")
        print("  - 'l' to show the list again")
        print("  - 'q' to quit")
        print("  - 'm' to show metadata of last tracked segmentation")
        
        id_num = -1
        
        while True:
            try:
                choice = input("\nEnter command (q - quit | l - list | m - metadata): ")
                
                if choice == 'q':
                    break
                elif choice == 'l':
                    print_segmentation_list(segmentations)
                    id_num = -1
                    continue
                elif choice == 'm':
                    tracker.print_metadata_complete(tracker.path_mapping[id_num]) if id_num > 0 else print("No segmentation tracked yet")
                    continue
                
                try:
                    id_num = int(choice)
                    error = tracker.track_by_id(id_num)
                    if error == -1:
                        print("Invalid ID. Enter a number from the list.")
                        print_segmentation_list(segmentations)
                except ValueError:
                    print("Invalid command. Enter a number, 'l' for list, or 'q' to quit")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            
    elif args.track:
        tracker.print_history(args.track)
        
    if not args.list and not args.track and not args.interactive:
        parser.print_help()

if __name__ == "__main__":
    main()