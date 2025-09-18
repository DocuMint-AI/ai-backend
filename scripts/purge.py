#!/usr/bin/env python3
"""
Data Purge Utility for AI Backend OCR System
============================================

This script provides options to clean up data files generated during OCR processing,
testing, and development. It includes safety features and interactive menus.

Usage:
    uv run purge.py                    # Interactive menu
    uv run purge.py --quick            # Quick purge (uploads + temp)
    uv run purge.py --full             # Full purge (all data except test files)
    uv run purge.py --nuclear          # Nuclear purge (everything including test files)
    uv run purge.py --setup            # Show setup menu
    uv run purge.py --dry-run          # Show what would be deleted without deleting

Safety Features:
- Dry-run mode to preview deletions
- Confirmation prompts for destructive operations
- Preserves essential files (.env, credentials)
- Backup option for important data
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Optional
import time

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from project_utils import get_project_root
    project_root = get_project_root()
except ImportError:
    project_root = PROJECT_ROOT

class DataPurger:
    """Handles data cleanup operations with safety features."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_root = project_root
        self.data_dir = self.project_root / "data"
        self.deleted_items = []
        self.preserved_items = []
        self.backup_dir = None
        
        # Define cleanup categories
        self.cleanup_categories = {
            "uploads": {
                "paths": ["data/uploads/*"],
                "description": "Uploaded PDF files",
                "safe": True
            },
            "processing_results": {
                "paths": ["data/testing-ocr-pdf-*", "data/*-*/"],
                "description": "OCR processing results and output folders",
                "safe": True
            },
            "temp_files": {
                "paths": ["data/temp/*", "data/*.tmp", "data/.temp*"],
                "description": "Temporary files and cache",
                "safe": True
            },
            "test_results": {
                "paths": ["data/test_*.json", "data/*test*.json"],
                "description": "Test output files",
                "safe": True
            },
            "logs": {
                "paths": ["data/logs/*", "data/*.log"],
                "description": "Log files",
                "safe": True
            },
            "test_files": {
                "paths": ["data/test-files/*"],
                "description": "Test input files (PDFs for testing)",
                "safe": False  # These are source files, more dangerous to delete
            },
            "credentials": {
                "paths": ["data/.cheetah/*", "data/*credentials*"],
                "description": "Credential files and authentication data",
                "safe": False  # Very dangerous to delete
            },
            "config": {
                "paths": ["data/.env*", "data/config*"],
                "description": "Configuration files",
                "safe": False  # Dangerous to delete
            }
        }
    
    def create_backup(self, categories: List[str]) -> Optional[Path]:
        """Create a backup of important data before deletion."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / f"backup_{timestamp}"
        
        try:
            backup_dir.mkdir(exist_ok=True)
            backup_count = 0
            
            for category in categories:
                if not self.cleanup_categories[category]["safe"]:
                    # Backup unsafe-to-delete items
                    for pattern in self.cleanup_categories[category]["paths"]:
                        files = list(self.project_root.glob(pattern))
                        for file_path in files:
                            if file_path.exists():
                                rel_path = file_path.relative_to(self.project_root)
                                backup_path = backup_dir / rel_path
                                backup_path.parent.mkdir(parents=True, exist_ok=True)
                                
                                if file_path.is_file():
                                    shutil.copy2(file_path, backup_path)
                                    backup_count += 1
                                elif file_path.is_dir():
                                    shutil.copytree(file_path, backup_path, dirs_exist_ok=True)
                                    backup_count += 1
            
            if backup_count > 0:
                self.backup_dir = backup_dir
                print(f"✅ Backup created: {backup_dir} ({backup_count} items)")
                return backup_dir
            else:
                # No backup needed, remove empty directory
                backup_dir.rmdir()
                return None
                
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return None
    
    def get_files_to_delete(self, categories: List[str]) -> List[Path]:
        """Get list of files that would be deleted for given categories."""
        files_to_delete = []
        
        for category in categories:
            if category not in self.cleanup_categories:
                print(f"⚠️  Unknown category: {category}")
                continue
                
            for pattern in self.cleanup_categories[category]["paths"]:
                matches = list(self.project_root.glob(pattern))
                files_to_delete.extend(matches)
        
        # Remove duplicates and sort
        files_to_delete = list(set(files_to_delete))
        files_to_delete.sort()
        
        return files_to_delete
    
    def calculate_size(self, file_path: Path) -> int:
        """Calculate total size of file or directory."""
        if file_path.is_file():
            return file_path.stat().st_size
        elif file_path.is_dir():
            total = 0
            try:
                for item in file_path.rglob("*"):
                    if item.is_file():
                        total += item.stat().st_size
            except (PermissionError, OSError):
                pass
            return total
        return 0
    
    def format_size(self, size_bytes: int) -> str:
        """Format bytes as human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def preview_deletion(self, categories: List[str]) -> Dict:
        """Preview what would be deleted without actually deleting."""
        files_to_delete = self.get_files_to_delete(categories)
        
        preview = {
            "categories": categories,
            "files": [],
            "total_files": 0,
            "total_size": 0
        }
        
        for file_path in files_to_delete:
            if file_path.exists():
                size = self.calculate_size(file_path)
                preview["files"].append({
                    "path": str(file_path.relative_to(self.project_root)),
                    "type": "file" if file_path.is_file() else "directory",
                    "size": size,
                    "size_formatted": self.format_size(size)
                })
                preview["total_files"] += 1
                preview["total_size"] += size
        
        preview["total_size_formatted"] = self.format_size(preview["total_size"])
        return preview
    
    def delete_files(self, categories: List[str], create_backup: bool = False) -> bool:
        """Delete files in specified categories."""
        files_to_delete = self.get_files_to_delete(categories)
        
        if not files_to_delete:
            print("🎉 No files found to delete.")
            return True
        
        # Create backup if requested
        if create_backup:
            self.create_backup(categories)
        
        success_count = 0
        error_count = 0
        total_size_deleted = 0
        
        print(f"\n{'🔍 DRY RUN - ' if self.dry_run else '🗑️  '}Deleting files...")
        
        for file_path in files_to_delete:
            if not file_path.exists():
                continue
                
            try:
                size = self.calculate_size(file_path)
                rel_path = file_path.relative_to(self.project_root)
                
                if self.dry_run:
                    print(f"  📁 Would delete: {rel_path} ({self.format_size(size)})")
                    self.deleted_items.append(str(rel_path))
                else:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                    
                    print(f"  ✅ Deleted: {rel_path} ({self.format_size(size)})")
                    self.deleted_items.append(str(rel_path))
                
                success_count += 1
                total_size_deleted += size
                
            except Exception as e:
                print(f"  ❌ Failed to delete {rel_path}: {e}")
                error_count += 1
        
        # Summary
        action = "Would delete" if self.dry_run else "Deleted"
        print(f"\n📊 Summary:")
        print(f"  {action}: {success_count} items")
        print(f"  Errors: {error_count}")
        print(f"  Total size: {self.format_size(total_size_deleted)}")
        
        if self.backup_dir and not self.dry_run:
            print(f"  Backup: {self.backup_dir}")
        
        return error_count == 0

def execute_purge(operation: str, dry_run: bool = False, backup: bool = False) -> Dict:
    """Execute purge operation and return results."""
    purger = DataPurger(dry_run=dry_run)
    
    operation_categories = {
        "quick": ["uploads", "temp_files"],
        "standard": ["processing_results", "logs", "temp_files"],
        "full": ["uploads", "processing_results", "temp_files", "test_results", "logs"],
        "nuclear": list(purger.cleanup_categories.keys())
    }
    
    if operation not in operation_categories:
        return {"error": f"Invalid operation: {operation}"}
    
    categories = operation_categories[operation]
    
    # Get preview first
    preview = purger.preview_deletion(categories)
    
    if dry_run:
        return {
            "operation": operation,
            "dry_run": True,
            "categories": categories,
            "preview": preview,
            "success": True
        }
    
    # Execute deletion
    success = purger.delete_files(categories, create_backup=backup)
    
    return {
        "operation": operation,
        "dry_run": False,
        "categories": categories,
        "preview": preview,
        "deleted_items": purger.deleted_items,
        "backup_dir": str(purger.backup_dir) if purger.backup_dir else None,
        "success": success
    }

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="AI Backend Data Purge Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/purge.py --quick            # Quick cleanup
  python scripts/purge.py --full --dry-run   # Preview full cleanup
  python scripts/purge.py --nuclear --backup # Nuclear with backup
        """
    )
    
    parser.add_argument("--quick", action="store_true", 
                       help="Quick purge: uploads and temp files")
    parser.add_argument("--standard", action="store_true",
                       help="Standard purge: processing results, logs, temp files")
    parser.add_argument("--full", action="store_true",
                       help="Full purge: all safe data categories")
    parser.add_argument("--nuclear", action="store_true",
                       help="Nuclear purge: everything including test files")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview what would be deleted without deleting")
    parser.add_argument("--backup", action="store_true",
                       help="Create backup before deletion")
    parser.add_argument("--yes", action="store_true",
                       help="Skip confirmation prompts")
    parser.add_argument("--json", action="store_true",
                       help="Output results in JSON format")
    
    args = parser.parse_args()
    
    # Determine operation
    operation = None
    if args.quick:
        operation = "quick"
    elif args.standard:
        operation = "standard"
    elif args.full:
        operation = "full"
    elif args.nuclear:
        operation = "nuclear"
    else:
        parser.print_help()
        sys.exit(1)
    
    # Handle confirmation before execution (not for dry-run or if --yes is used)
    if not args.dry_run and not args.yes:
        if operation == "nuclear":
            print("\n⚠️  NUCLEAR cleanup will delete EVERYTHING including test files and credentials!")
            confirm = input("Type 'DELETE EVERYTHING' to confirm: ")
            if confirm != "DELETE EVERYTHING":
                print("❌ Operation cancelled.")
                sys.exit(1)
        else:
            preview = execute_purge(operation, dry_run=True, backup=False)
            if preview.get("success"):
                preview_data = preview["preview"]
                print(f"\n🗑️  {operation.title()} cleanup will delete {preview_data['total_files']} items ({preview_data['total_size_formatted']})")
                confirm = input("Continue? (y/N): ")
                if confirm.lower() != 'y':
                    print("❌ Operation cancelled.")
                    sys.exit(1)
    
    # Execute purge operation
    result = execute_purge(operation, dry_run=args.dry_run, backup=args.backup)
    
    if args.json:
        # Output JSON for API consumption
        print(json.dumps(result, indent=2, default=str))
        return
    
    # Human-readable output
    if result.get("error"):
        print(f"❌ Error: {result['error']}")
        sys.exit(1)
    
    preview = result["preview"]
    action = "Would delete" if args.dry_run else "Deleted"
    
    print(f"\n🗑️  {operation.title()} cleanup results:")
    print(f"  {action}: {preview['total_files']} items")
    print(f"  Total size: {preview['total_size_formatted']}")
    
    if result.get("backup_dir"):
        print(f"  Backup created: {result['backup_dir']}")
    
    if result["success"]:
        print("✅ Cleanup completed successfully!")
    else:
        print("❌ Cleanup completed with errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()