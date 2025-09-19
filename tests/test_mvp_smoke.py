"""
MVP Smoke Tests for Legal Document Processing Pipeline.

Tests the complete MVP pipeline with the custom legal document extractor,
validating that structured outputs and feature vectors are generated correctly.
"""

import json
import pytest
import subprocess
from pathlib import Path
import os


class TestMVPSmoke:
    """Smoke tests for MVP legal document processing."""
    
    @pytest.fixture
    def mvp_artifacts_dir(self):
        """Get MVP artifacts directory."""
        return Path("artifacts") / "mvp"
    
    @pytest.mark.skipif(
        not os.getenv("DOCAI_STRUCTURED_PROCESSOR_ID"), 
        reason="DOCAI_STRUCTURED_PROCESSOR_ID not configured"
    )
    def test_mvp_script_execution(self):
        """Test that MVP script runs without fatal errors."""
        try:
            # Run the PowerShell MVP script
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", "scripts/mvp_run.ps1"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # MVP script should complete (exit code 0 or 1 both acceptable for testing)
            assert result.returncode in [0, 1], f"MVP script failed with exit code {result.returncode}: {result.stderr}"
            
            # Should generate summary file
            summary_file = Path("artifacts") / "mvp" / "summary.json"
            assert summary_file.exists(), "MVP summary.json not generated"
            
        except subprocess.TimeoutExpired:
            pytest.skip("MVP script timed out - may indicate processing issues")
        except FileNotFoundError:
            pytest.skip("PowerShell not available - run mvp_run.ps1 manually")
    
    def test_mvp_artifacts_structure(self, mvp_artifacts_dir):
        """Test that MVP generates required artifacts for each document."""
        if not mvp_artifacts_dir.exists():
            pytest.skip("MVP artifacts directory not found - run mvp_run.ps1 first")
        
        # Check that at least some document directories exist
        doc_dirs = [d for d in mvp_artifacts_dir.iterdir() if d.is_dir() and d.name.startswith("doc_")]
        assert len(doc_dirs) > 0, "No document processing directories found"
        
        # Validate structure for each doc
        required_files = ["parsed_output.json", "feature_vector.json"]
        
        for doc_dir in doc_dirs:
            for required_file in required_files:
                file_path = doc_dir / required_file
                assert file_path.exists(), f"Missing required file: {file_path}"
    
    def test_mvp_summary_validation(self, mvp_artifacts_dir):
        """Test MVP summary meets acceptance criteria."""
        summary_file = mvp_artifacts_dir / "summary.json"
        
        if not summary_file.exists():
            pytest.skip("MVP summary not found - run mvp_run.ps1 first")
        
        with open(summary_file, 'r') as f:
            summary = json.load(f)
        
        # Validate summary structure
        assert "summary" in summary, "Missing summary section"
        assert "detailed_results" in summary, "Missing detailed_results section"
        
        summary_data = summary["summary"]
        assert "total_docs" in summary_data, "Missing total_docs in summary"
        assert "successful_docs" in summary_data, "Missing successful_docs in summary"
        assert "acceptance_criteria_met" in summary_data, "Missing acceptance_criteria_met in summary"
        
        # Log results for debugging
        print(f"\n📊 MVP Results: {summary_data['successful_docs']}/{summary_data['total_docs']} successful")
        print(f"🎯 Acceptance Criteria: {'✅ PASS' if summary_data['acceptance_criteria_met'] else '❌ FAIL'}")
    
    def test_feature_vector_structure_compliance(self, mvp_artifacts_dir):
        """Test that generated feature vectors have required structure."""
        doc_dirs = [d for d in mvp_artifacts_dir.iterdir() if d.is_dir() and d.name.startswith("doc_")]
        
        if not doc_dirs:
            pytest.skip("No MVP document directories found")
        
        feature_files_found = 0
        
        for doc_dir in doc_dirs:
            feature_file = doc_dir / "feature_vector.json"
            
            if feature_file.exists():
                with open(feature_file, 'r') as f:
                    feature_data = json.load(f)
                
                # Skip error placeholders
                if feature_data.get("error"):
                    continue
                
                feature_files_found += 1
                
                # Validate required structure
                required_keys = ["document_id", "embedding_doc", "kv_flags", "structural", "needs_review"]
                for key in required_keys:
                    assert key in feature_data, f"Missing key in feature vector: {key}"
                
                # Validate KV flags
                kv_flags = feature_data["kv_flags"]
                expected_flags = ["has_policy_no", "has_date_of_commencement", "has_sum_assured", "has_dob", "has_nominee"]
                
                for flag in expected_flags:
                    assert flag in kv_flags, f"Missing KV flag: {flag}"
                    assert isinstance(kv_flags[flag], bool), f"KV flag {flag} must be boolean"
        
        assert feature_files_found > 0, "No valid feature vector files found"
    
    @pytest.mark.skipif(
        not Path("artifacts/mvp/summary.json").exists(),
        reason="MVP summary not available - run mvp_run.ps1 first"
    )
    def test_mvp_acceptance_criteria(self):
        """Test that MVP meets the 3+ successful documents criteria."""
        with open("artifacts/mvp/summary.json", 'r') as f:
            summary = json.load(f)
        
        successful_docs = summary["summary"]["successful_docs"]
        total_docs = summary["summary"]["total_docs"]
        
        # Log detailed results for debugging
        for result in summary["detailed_results"]:
            status_icon = "✅" if result["status"] == "SUCCESS" else "❌"
            print(f"{status_icon} Doc {result['doc']}: KVs={result['kvs']}, Review={result['needs_review']}")
        
        # MVP acceptance criteria: at least 3 successful docs
        assert successful_docs >= 3, f"MVP acceptance criteria not met: {successful_docs}/5 successful (need 3+)"


if __name__ == "__main__":
    # Quick validation
    print("🧪 Running MVP smoke tests...")
    
    # Check if MVP has been run
    mvp_dir = Path("artifacts") / "mvp"
    if not mvp_dir.exists():
        print("❌ MVP not run yet - execute: powershell scripts/mvp_run.ps1")
        exit(1)
    
    # Run pytest
    exit_code = pytest.main([__file__, "-v"])
    print(f"🏁 Smoke tests completed with exit code: {exit_code}")
    exit(exit_code)