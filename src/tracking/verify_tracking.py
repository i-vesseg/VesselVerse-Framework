import sys, subprocess
import pandas as pd

from pathlib import Path
from typing import Dict
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent))
from model_config.model_config import registry

class TrackingVerifier:
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        # Use model registry instead of hardcoded dirs
        self.expected_dirs = {model.name for model in registry.models.values()}
        self.tracked_dirs = self.expected_dirs - {'IXI_TOT'}

    def get_directory_stats(self) -> Dict:
        stats = {}
        for model_config in registry.models.values():
            dir_path = self.base_path / model_config.name
            if dir_path.exists():
                files = list(dir_path.rglob("*.nii.gz"))
                stats[model_config.name] = {
                    'exists': True,
                    'file_count': len(files),
                    'example_files': sorted([f.name for f in files])[:5]
                }
            else:
                stats[model_config.name] = {
                    'exists': False,
                    'file_count': 0,
                    'example_files': []
                }
        return stats

    def analyze_case_distribution(self) -> pd.DataFrame:
        case_dict = defaultdict(lambda: {
            model.name: False for model in registry.models.values()
        })
        
        for model_config in registry.models.values():
            dir_path = self.base_path / model_config.name
            if dir_path.exists():
                for file_path in dir_path.rglob("*.nii.gz"):
                    case_id = file_path.stem.split('_')[0]
                    case_dict[case_id][model_config.name] = True
        
        return pd.DataFrame.from_dict(case_dict, orient='index')
    
    def verify_all(self) -> Dict:
        """Run all verifications and return detailed results."""
        print("🔍 Starting verification process...\n")
        
        # Get directory statistics
        dir_stats = self.get_directory_stats()
        print("📁 Directory Statistics:")
        print("-" * 50)
        for dir_name, stats in dir_stats.items():
            status = "✓" if stats['exists'] else "❌"
            print(f"{status} {dir_name}:")
            if stats['exists']:
                print(f"   Files: {stats['file_count']}")
                if stats['example_files']:
                    print(f"   Examples: {', '.join(stats['example_files'])}")
                print()
        
        # Analyze case distribution
        case_df = self.analyze_case_distribution()
        print("\n📊 Case Distribution Analysis:")
        print("-" * 50)
        for dir_name in self.expected_dirs:
            case_count = case_df[dir_name].sum()
            total_cases = len(case_df)
            print(f"{dir_name}:")
            print(f"   Cases present: {case_count}/{total_cases} ({(case_count/total_cases)*100:.1f}%)")
        
        # Check DVC status
        print("\n🔄 DVC Status:")
        print("-" * 50)
        try:
            result = subprocess.run(['dvc', 'status'], capture_output=True, text=True)
            print(result.stdout if result.stdout else "Data and pipelines are up to date")
        except subprocess.CalledProcessError as e:
            print(f"Error checking DVC status: {e}")

        return {
            "directory_stats": dir_stats,
            "case_distribution": case_df
        }

    def generate_missing_cases_report(self, output_file: str = "missing_cases_report.csv"):
        """Generate a detailed report of missing cases."""
        case_df = self.analyze_case_distribution()
        
        # Add a column for total presence
        case_df['presence_count'] = case_df.sum(axis=1)
        
        # Save the report
        case_df.to_csv(output_file)
        print(f"\n📝 Missing cases report generated: {output_file}")
        
        # Print summary statistics
        print("\nSummary of case presence:")
        presence_stats = case_df['presence_count'].value_counts().sort_index()
        for count, freq in presence_stats.items():
            print(f"Cases present in {count} directories: {freq}")

if __name__ == "__main__":
    verifier = TrackingVerifier()
    results = verifier.verify_all()
    verifier.generate_missing_cases_report()