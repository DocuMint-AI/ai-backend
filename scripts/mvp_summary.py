"""
MVP Summary Generator and Validator.

Analyzes the results of MVP processing and generates summary with acceptance criteria validation.
"""

import json
import sys
import os
from pathlib import Path


def main():
    """Generate MVP processing summary and validate acceptance criteria."""
    print("MVP Processing Summary")
    print("=" * 50)
    
    results = []
    total_docs = 5
    success_count = 0
    
    # Analyze each document's processing results
    for i in range(1, total_docs + 1):
        doc_dir = Path(f"artifacts/mvp/doc_{i}")
        parsed_file = doc_dir / "parsed_output.json"
        feature_file = doc_dir / "feature_vector.json"
        
        # Check if files exist
        parsed_exists = parsed_file.exists()
        feature_exists = feature_file.exists()
        
        # Load and analyze if exists
        parsed_summary = {}
        feature_summary = {}
        
        if parsed_exists:
            try:
                with open(parsed_file, 'r', encoding='utf-8') as f:
                    parsed_summary = json.load(f)
            except Exception as e:
                print(f"Failed to load parsed output for doc {i}: {e}")
        
        if feature_exists:
            try:
                with open(feature_file, 'r', encoding='utf-8') as f:
                    feature_summary = json.load(f)
            except Exception as e:
                print(f"Failed to load feature vector for doc {i}: {e}")
        
        # Extract metrics
        is_placeholder = parsed_summary.get("placeholder", False) or parsed_summary.get("error") is not None
        clauses_count = len(parsed_summary.get("clauses", []))
        entities_count = len(parsed_summary.get("named_entities", []))
        kvs_count = len(parsed_summary.get("key_value_pairs", []))
        kv_flags = feature_summary.get("kv_flags", {})
        needs_review = feature_summary.get("needs_review", True)
        
        # Count successful KV flags
        kv_success = sum(1 for flag, value in kv_flags.items() if value and "has_" in flag)
        
        # Determine success status
        # Success criteria: not a placeholder AND (has KVs OR doesn't need review)
        is_successful = not is_placeholder and (kvs_count >= 1 or not needs_review)
        
        doc_result = {
            "doc": i,
            "parsed_exists": parsed_exists,
            "feature_exists": feature_exists,
            "is_placeholder": is_placeholder,
            "clauses": clauses_count,
            "entities": entities_count,
            "kvs": kvs_count,
            "kv_flags": kv_flags,
            "kv_success_count": kv_success,
            "needs_review": needs_review,
            "status": "SUCCESS" if is_successful else "NEEDS_WORK"
        }
        
        results.append(doc_result)
        
        if doc_result["status"] == "SUCCESS":
            success_count += 1
        
        # Print individual doc summary
        status_icon = "PASS" if doc_result["status"] == "SUCCESS" else "FAIL"
        print(f"{status_icon} Doc {i}: {doc_result['status']} | KVs: {kvs_count} | KV Flags: {kv_success}/5 | Review: {needs_review}")
    
    # Overall results
    print("")
    print(f"MVP RESULTS: {success_count}/{total_docs} documents successful")
    acceptance_met = success_count >= 3
    print(f"Acceptance Criteria: {'PASS' if acceptance_met else 'FAIL'} (need 3+ successful)")
    
    # Save detailed results
    summary_data = {
        "summary": {
            "total_docs": total_docs,
            "successful_docs": success_count,
            "acceptance_criteria_met": acceptance_met,
            "processor_used": os.getenv("DOCAI_STRUCTURED_PROCESSOR_ID", os.getenv("DOCAI_PROCESSOR_ID", "unknown")),
            "timestamp": str(Path().absolute().as_posix())
        },
        "detailed_results": results
    }
    
    summary_file = Path("artifacts/mvp/summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    print(f"Detailed results saved to: {summary_file}")
    
    # Additional diagnostics
    if success_count < 3:
        print("")
        print("DIAGNOSTICS - Why MVP failed:")
        common_issues = []
        
        for result in results:
            if result["status"] == "NEEDS_WORK":
                if result["is_placeholder"]:
                    common_issues.append("placeholder_results")
                elif result["kvs"] == 0 and result["needs_review"]:
                    common_issues.append("no_kvs_extracted")
        
        issue_counts = {}
        for issue in common_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        for issue, count in issue_counts.items():
            if issue == "placeholder_results":
                print(f"- {count} docs have placeholder results (processing failed)")
            elif issue == "no_kvs_extracted":
                print(f"- {count} docs have no KVs extracted and need review")
    
    # Exit with appropriate code
    return 0 if acceptance_met else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)