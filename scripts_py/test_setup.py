#!/usr/bin/env python3
import sys, json, shutil, subprocess

from pathlib import Path
from typing import Tuple
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from src.model_config.model_config import registry

class SetupTester:
    def __init__(self):
        self.project_root = Path.cwd()
        self.test_results = []
        self.required_dirs = [model.name for model in registry.models.values()]

    def test_directory_structure(self) -> bool:
        missing_dirs = []
        for dir_name in self.required_dirs:
            if not (self.project_root / "data" /dir_name).exists():
                print(f"Directory not found: {dir_name} (expected at {self.project_root / 'data' / dir_name})")
                missing_dirs.append(dir_name)
        
        success = len(missing_dirs) == 0
        self.test_results.append(
            ("Directory Structure ==>", success, 
             "All required directories exist" if success else f"Missing directories: {missing_dirs}")
        )
        return success
        
    def _run_command(self, command: str) -> Tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, and stderr."""
        process = subprocess.Popen(
            command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr

    def test_dvc_installation(self) -> bool:
        """Test if DVC is properly installed."""
        try:
            returncode, stdout, stderr = self._run_command("dvc --version")
            success = returncode == 0
            self.test_results.append(("DVC Installation", success, stdout if success else stderr))
            return success
        except FileNotFoundError:
            self.test_results.append(("DVC Installation", False, "DVC not found. Please install DVC."))
            return False

    def test_service_account_file(self) -> bool:
        """Test if service account file exists and is valid JSON."""
        sa_path = self.project_root / "service-account.json"
        if not sa_path.exists():
            self.test_results.append(("Service Account File", False, "service-account.json not found"))
            return False
        
        try:
            with open(sa_path) as f:
                json.load(f)
            self.test_results.append(("Service Account File", True, "Valid service account file found"))
            return True
        except json.JSONDecodeError:
            self.test_results.append(("Service Account File", False, "Invalid JSON in service account file"))
            return False

    def test_dvc_remotes(self) -> bool:
        """Test if DVC remotes are properly configured."""
        returncode, stdout, stderr = self._run_command("dvc remote list")
        
        if returncode != 0:
            self.test_results.append(("DVC Remotes", False, "Failed to list remotes"))
            return False
        
        remotes = stdout.strip().split('\n')
        has_storage = any('storage' in r for r in remotes)
        has_uploads = any('uploads' in r for r in remotes)
        
        success = has_storage and has_uploads
        self.test_results.append(
            ("DVC Remotes", success, 
             "Both remotes configured correctly" if success else "Missing required remotes")
        )
        return success

    def test_read_access(self) -> bool:
        """Test if we can pull from storage remote."""
        # First, create a backup of existing data
        if Path('data').exists():
            backup_path = f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.move('data', backup_path)
        else:
            backup_path = None
            
        returncode, stdout, stderr = self._run_command("dvc pull -r storage")
        success = returncode == 0
        
        # Restore backup if it exists
        if Path(backup_path).exists():
            shutil.rmtree('data', ignore_errors=True)
            shutil.move(backup_path, 'data')
        
        self.test_results.append(
            ("Storage Read Access", success, 
             "Successfully pulled from storage" if success else f"Pull failed: {stderr}")
        )
        return success

    def test_write_access(self) -> bool:
        """Test if we can push to uploads remote."""
        # Create a test file
        test_file = Path("test_upload.txt")
        test_file.write_text("test content")
        
        try:
            subprocess.run(["dvc", "add", str(test_file)], check=True)
            returncode, stdout, stderr = self._run_command("dvc push -r uploads")
            success = returncode == 0
            
            # Cleanup
            test_file.unlink(missing_ok=True)
            dvc_file = Path("test_upload.txt.dvc")
            dvc_file.unlink(missing_ok=True)
            
            self.test_results.append(
                ("Uploads Write Access", success, 
                 "Successfully pushed to uploads" if success else f"Push failed: {stderr}")
            )
            return success
            
        except subprocess.CalledProcessError as e:
            self.test_results.append(("Uploads Write Access", False, f"Failed: {str(e)}"))
            return False

    def run_all_tests(self):
        """Run all setup tests and print results."""
        print("🔍 Starting VesselVerse Setup Tests\n")
        
        tests = [
            self.test_dvc_installation,
            self.test_service_account_file,
            self.test_dvc_remotes,
            self.test_directory_structure,
            self.test_read_access,
            self.test_write_access
        ]
        
        for test in tests:
            test()
        
        print("\n📊 Test Results:")
        print("-" * 60)
        
        all_passed = True
        for test_name, success, message in self.test_results:
            status = "✓" if success else "❌"
            print(f"{status} {test_name}: {message}")
            if not success:
                all_passed = False
        
        print("\n🎯 Final Status:", "✓ All tests passed!" if all_passed else "❌ Some tests failed")
        
        if not all_passed:
            print("\n⚠️ Troubleshooting Tips:")
            print("1. Ensure DVC is installed: pip install 'dvc[gdrive]'")
            print("2. Verify service-account.json is in the project root")
            print("3. Check DVC remote configuration: dvc remote list")
            print("4. Verify Google Drive folder permissions")
            print("5. Run 'dvc doctor' for additional diagnostics")

if __name__ == "__main__":
    tester = SetupTester()
    tester.run_all_tests()