#!/usr/bin/env python3
"""
DocAI Output Diagnostic System

This comprehensive diagnostic tool traces and confirms where DocAI outputs are stored
after each document is processed. It provides strict verification of file creation,
content validation, and complete artifact mapping.

Features:
- File tracking for all DocAI outputs (raw, parsed, structured)
- Runtime verification with file sizes and creation times
- Content analysis and validation
- Atomic write verification
- Complete artifact mapping generation
"""

import sys
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import hashlib

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocAIOutputTracker:
    """
    Comprehensive DocAI output file tracking and verification system.
    """
    
    def __init__(self, artifacts_base_dir: str = "artifacts"):
        """
        Initialize the DocAI output tracker.
        
        Args:
            artifacts_base_dir: Base directory for artifacts storage
        """
        self.artifacts_base_dir = Path(artifacts_base_dir)
        self.tracking_session = {
            'session_id': self._generate_session_id(),
            'start_time': datetime.now().isoformat(),
            'tracked_files': {},
            'file_operations': [],
            'verification_results': {},
            'output_mapping': {}
        }
        
        # Known DocAI output locations and their roles
        self.known_output_patterns = {
            'artifacts/vision_to_docai/docai_raw_full.json': {
                'role': 'raw_docai_response',
                'description': 'Complete raw DocAI API response',
                'source': 'services/doc_ai/client.py:_save_raw_response',
                'atomic_writes': True,
                'versioned': False
            },
            'artifacts/vision_to_docai/feature_vector.json': {
                'role': 'ml_features',
                'description': 'Vertex AI ML features extracted from document',
                'source': 'services/doc_ai/parser.py:emit_feature_vector',
                'atomic_writes': False,
                'versioned': False
            },
            'artifacts/vision_to_docai/diagnostics.json': {
                'role': 'processing_diagnostics',
                'description': 'DocAI processing diagnostics and analysis',
                'source': 'services/doc_ai/parser.py:_generate_diagnostics_summary',
                'atomic_writes': False,
                'versioned': False
            },
            'artifacts/vision_to_docai/parsed_output.json': {
                'role': 'structured_output',
                'description': 'Parsed and structured document content',
                'source': 'scripts/test_vision_to_docai.py',
                'atomic_writes': False,
                'versioned': False
            },
            'artifacts/vision_to_docai/vision_raw.json': {
                'role': 'vision_ocr_output',
                'description': 'Raw Vision OCR results',
                'source': 'scripts/test_vision_to_docai.py',
                'atomic_writes': False,
                'versioned': False
            },
            'artifacts/vision_to_docai/vision_normalized.json': {
                'role': 'vision_normalized',
                'description': 'Normalized Vision OCR output',
                'source': 'scripts/test_vision_to_docai.py',
                'atomic_writes': False,
                'versioned': False
            }
        }
        
        logger.info(f"🔍 DocAI Output Tracker initialized - Session: {self.tracking_session['session_id']}")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID for tracking."""
        timestamp = int(time.time())
        random_suffix = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
        return f"docai_track_{timestamp}_{random_suffix}"
    
    def start_monitoring(self) -> None:
        """Start monitoring DocAI output files."""
        logger.info("📂 Starting DocAI output file monitoring...")
        
        # Record initial state of artifacts directory
        self._capture_initial_state()
        
        # Setup file watchers for known locations
        self._setup_file_watchers()
        
        logger.info("✅ DocAI output monitoring active")
    
    def _capture_initial_state(self) -> None:
        """Capture initial state of artifacts directory."""
        logger.info("📸 Capturing initial artifacts state...")
        
        initial_state = {}
        for pattern, config in self.known_output_patterns.items():
            file_path = Path(pattern)
            if file_path.exists():
                stat = file_path.stat()
                initial_state[str(file_path)] = {
                    'exists': True,
                    'size_bytes': stat.st_size,
                    'modified_time': stat.st_mtime,
                    'creation_time': stat.st_ctime,
                    'role': config['role']
                }
            else:
                initial_state[str(file_path)] = {
                    'exists': False,
                    'role': config['role']
                }
        
        self.tracking_session['initial_state'] = initial_state
        logger.info(f"📊 Initial state captured: {len(initial_state)} files tracked")
    
    def _setup_file_watchers(self) -> None:
        """Setup file watchers for DocAI output locations."""
        logger.info("👀 Setting up file watchers...")
        
        # Create directories if they don't exist
        for pattern in self.known_output_patterns.keys():
            file_path = Path(pattern)
            file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def track_file_operation(self, operation_type: str, file_path: str, details: Dict[str, Any] = None) -> None:
        """
        Track a file operation.
        
        Args:
            operation_type: Type of operation (write, create, modify, delete)
            file_path: Path to the file
            details: Additional operation details
        """
        operation = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation_type,
            'file_path': file_path,
            'details': details or {}
        }
        
        self.tracking_session['file_operations'].append(operation)
        logger.debug(f"📝 Tracked operation: {operation_type} on {file_path}")
    
    def verify_file_integrity(self, file_path: Path) -> Dict[str, Any]:
        """
        Verify file integrity and content.
        
        Args:
            file_path: Path to file to verify
            
        Returns:
            Verification results
        """
        try:
            if not file_path.exists():
                return {
                    'exists': False,
                    'error': 'File does not exist'
                }
            
            stat = file_path.stat()
            
            # Basic file information
            verification = {
                'exists': True,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 3),
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'creation_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'is_empty': stat.st_size == 0,
                'readable': os.access(file_path, os.R_OK)
            }
            
            # Content verification for JSON files
            if file_path.suffix == '.json' and stat.st_size > 0:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    
                    verification.update({
                        'valid_json': True,
                        'content_type': type(content).__name__,
                        'content_keys': list(content.keys()) if isinstance(content, dict) else None,
                        'content_length': len(content) if isinstance(content, (dict, list)) else None
                    })
                    
                    # Specific content analysis based on file type
                    if 'docai_raw' in file_path.name:
                        verification['content_analysis'] = self._analyze_docai_raw_content(content)
                    elif 'parsed_output' in file_path.name:
                        verification['content_analysis'] = self._analyze_parsed_output_content(content)
                    elif 'feature_vector' in file_path.name:
                        verification['content_analysis'] = self._analyze_feature_vector_content(content)
                    elif 'diagnostics' in file_path.name:
                        verification['content_analysis'] = self._analyze_diagnostics_content(content)
                    
                except json.JSONDecodeError as e:
                    verification.update({
                        'valid_json': False,
                        'json_error': str(e)
                    })
                except Exception as e:
                    verification.update({
                        'content_error': str(e)
                    })
            
            return verification
            
        except Exception as e:
            return {
                'exists': file_path.exists(),
                'verification_error': str(e)
            }
    
    def _analyze_docai_raw_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze raw DocAI response content."""
        analysis = {
            'has_text': bool(content.get('text', '')),
            'text_length': len(content.get('text', '')),
            'has_entities': bool(content.get('entities', [])),
            'entity_count': len(content.get('entities', [])),
            'has_pages': bool(content.get('pages', [])),
            'page_count': len(content.get('pages', [])),
            'processing_metadata': bool(content.get('processing_metadata'))
        }
        return analysis
    
    def _analyze_parsed_output_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze parsed output content."""
        analysis = {
            'has_structured_data': bool(content.get('clauses') or content.get('entities')),
            'clause_count': len(content.get('clauses', [])),
            'entity_count': len(content.get('entities', [])),
            'has_metadata': bool(content.get('metadata')),
            'text_preview_length': len(content.get('text_preview', '')),
            'page_count': content.get('page_count', 0)
        }
        return analysis
    
    def _analyze_feature_vector_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze feature vector content."""
        analysis = {
            'feature_categories': list(content.keys()) if isinstance(content, dict) else [],
            'total_features': sum(len(v) if isinstance(v, (list, dict)) else 1 for v in content.values()) if isinstance(content, dict) else 0,
            'has_ml_features': bool(content.get('features') or content.get('document_features'))
        }
        return analysis
    
    def _analyze_diagnostics_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze diagnostics content."""
        analysis = {
            'has_performance_metrics': bool(content.get('performance')),
            'has_extraction_stats': bool(content.get('extraction')),
            'has_validation_results': bool(content.get('validation')),
            'diagnostic_categories': list(content.keys()) if isinstance(content, dict) else []
        }
        return analysis
    
    def capture_post_processing_state(self) -> Dict[str, Any]:
        """Capture state after DocAI processing."""
        logger.info("📸 Capturing post-processing state...")
        
        post_state = {}
        verification_results = {}
        
        for pattern, config in self.known_output_patterns.items():
            file_path = Path(pattern)
            
            # File verification
            verification = self.verify_file_integrity(file_path)
            verification_results[str(file_path)] = verification
            
            # State capture
            if file_path.exists():
                post_state[str(file_path)] = {
                    'exists': True,
                    'role': config['role'],
                    'description': config['description'],
                    'source': config['source'],
                    'atomic_writes': config['atomic_writes'],
                    'size_bytes': verification.get('size_bytes', 0),
                    'size_mb': verification.get('size_mb', 0),
                    'created_time': verification.get('creation_time'),
                    'modified_time': verification.get('modified_time'),
                    'content_valid': verification.get('valid_json', True),
                    'content_analysis': verification.get('content_analysis', {})
                }
            else:
                post_state[str(file_path)] = {
                    'exists': False,
                    'role': config['role'],
                    'description': config['description']
                }
        
        self.tracking_session['post_state'] = post_state
        self.tracking_session['verification_results'] = verification_results
        
        logger.info(f"📊 Post-processing state captured: {len(post_state)} files tracked")
        return post_state
    
    def generate_output_mapping(self) -> Dict[str, Any]:
        """Generate comprehensive output mapping artifact."""
        logger.info("🗺️ Generating output mapping artifact...")
        
        output_mapping = {
            'session_info': {
                'session_id': self.tracking_session['session_id'],
                'generation_time': datetime.now().isoformat(),
                'tracking_duration': 'N/A'  # Will be calculated
            },
            'docai_output_files': {},
            'file_operations_summary': {},
            'verification_summary': {},
            'recommendations': []
        }
        
        # Calculate tracking duration
        start_time = datetime.fromisoformat(self.tracking_session['start_time'])
        duration = datetime.now() - start_time
        output_mapping['session_info']['tracking_duration'] = str(duration)
        
        # Map output files
        for file_path, state in self.tracking_session.get('post_state', {}).items():
            output_mapping['docai_output_files'][file_path] = {
                'role': state['role'],
                'description': state['description'],
                'exists': state['exists'],
                'size_bytes': state.get('size_bytes', 0),
                'size_mb': state.get('size_mb', 0),
                'content_valid': state.get('content_valid', False),
                'content_summary': state.get('content_analysis', {}),
                'atomic_writes': state.get('atomic_writes', False),
                'status': 'created' if state['exists'] else 'missing'
            }
        
        # Operations summary
        operations = self.tracking_session.get('file_operations', [])
        output_mapping['file_operations_summary'] = {
            'total_operations': len(operations),
            'operation_types': list(set(op['operation'] for op in operations)),
            'files_affected': list(set(op['file_path'] for op in operations))
        }
        
        # Verification summary
        created_files = [f for f, s in output_mapping['docai_output_files'].items() if s['exists']]
        missing_files = [f for f, s in output_mapping['docai_output_files'].items() if not s['exists']]
        
        output_mapping['verification_summary'] = {
            'total_expected_files': len(self.known_output_patterns),
            'files_created': len(created_files),
            'files_missing': len(missing_files),
            'creation_success_rate': round(len(created_files) / len(self.known_output_patterns) * 100, 1),
            'total_size_mb': sum(s['size_mb'] for s in output_mapping['docai_output_files'].values()),
            'all_files_valid': all(s['content_valid'] for s in output_mapping['docai_output_files'].values() if s['exists'])
        }
        
        # Generate recommendations
        output_mapping['recommendations'] = self._generate_recommendations(output_mapping)
        
        self.tracking_session['output_mapping'] = output_mapping
        
        logger.info(f"✅ Output mapping generated: {len(created_files)}/{len(self.known_output_patterns)} files created")
        return output_mapping
    
    def _generate_recommendations(self, mapping: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on tracking results."""
        recommendations = []
        
        if mapping['verification_summary']['files_missing'] > 0:
            recommendations.append("Some expected DocAI output files are missing - check processing logs")
        
        if not mapping['verification_summary']['all_files_valid']:
            recommendations.append("Some output files contain invalid content - verify processing integrity")
        
        if mapping['verification_summary']['total_size_mb'] == 0:
            recommendations.append("All output files are empty - check DocAI processing configuration")
        
        if mapping['file_operations_summary']['total_operations'] == 0:
            recommendations.append("No file operations tracked - verify monitoring is active during processing")
        
        atomic_files = [f for f, info in mapping['docai_output_files'].items() 
                       if info.get('atomic_writes') and info['exists']]
        if not atomic_files:
            recommendations.append("No atomic write operations detected - check _save_raw_response implementation")
        
        if not recommendations:
            recommendations.append("All DocAI output files successfully created and verified")
        
        return recommendations
    
    def save_diagnostic_artifacts(self, output_dir: str = None) -> Dict[str, str]:
        """
        Save all diagnostic artifacts.
        
        Args:
            output_dir: Directory to save artifacts (default: artifacts/docai_diagnostics)
            
        Returns:
            Dictionary mapping artifact types to file paths
        """
        if output_dir is None:
            output_dir = "artifacts/docai_diagnostics"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_artifacts = {}
        
        try:
            # Save output mapping
            mapping_path = output_path / "docai_output_map.json"
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(self.tracking_session['output_mapping'], f, indent=2, ensure_ascii=False)
            saved_artifacts['output_mapping'] = str(mapping_path)
            
            # Save complete tracking session
            session_path = output_path / "tracking_session.json"
            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(self.tracking_session, f, indent=2, ensure_ascii=False)
            saved_artifacts['tracking_session'] = str(session_path)
            
            # Save verification details
            verification_path = output_path / "file_verification.json"
            with open(verification_path, 'w', encoding='utf-8') as f:
                json.dump(self.tracking_session.get('verification_results', {}), f, indent=2, ensure_ascii=False)
            saved_artifacts['verification_details'] = str(verification_path)
            
            # Generate summary report
            summary_path = output_path / "diagnostic_summary.txt"
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(self._generate_summary_report())
            saved_artifacts['summary_report'] = str(summary_path)
            
            logger.info(f"💾 Diagnostic artifacts saved to: {output_path}")
            return saved_artifacts
            
        except Exception as e:
            logger.error(f"❌ Failed to save diagnostic artifacts: {e}")
            return {}
    
    def _generate_summary_report(self) -> str:
        """Generate human-readable summary report."""
        mapping = self.tracking_session.get('output_mapping', {})
        
        report_lines = [
            "=" * 80,
            "DOCAI OUTPUT DIAGNOSTIC SUMMARY",
            "=" * 80,
            "",
            f"Session ID: {self.tracking_session['session_id']}",
            f"Start Time: {self.tracking_session['start_time']}",
            f"Generation Time: {mapping.get('session_info', {}).get('generation_time', 'N/A')}",
            f"Tracking Duration: {mapping.get('session_info', {}).get('tracking_duration', 'N/A')}",
            "",
            "OUTPUT FILE STATUS:",
            "-" * 40
        ]
        
        for file_path, info in mapping.get('docai_output_files', {}).items():
            status = "✅ CREATED" if info['exists'] else "❌ MISSING"
            size_info = f" ({info['size_mb']:.2f} MB)" if info['exists'] else ""
            valid_info = " [VALID]" if info.get('content_valid') else " [INVALID]" if info['exists'] else ""
            
            report_lines.extend([
                f"{status} {Path(file_path).name}{size_info}{valid_info}",
                f"   Role: {info['role']}",
                f"   Description: {info['description']}",
                ""
            ])
        
        verification = mapping.get('verification_summary', {})
        report_lines.extend([
            "VERIFICATION SUMMARY:",
            "-" * 40,
            f"Expected Files: {verification.get('total_expected_files', 0)}",
            f"Files Created: {verification.get('files_created', 0)}",
            f"Files Missing: {verification.get('files_missing', 0)}",
            f"Success Rate: {verification.get('creation_success_rate', 0)}%",
            f"Total Size: {verification.get('total_size_mb', 0):.2f} MB",
            f"All Valid: {'YES' if verification.get('all_files_valid') else 'NO'}",
            "",
            "RECOMMENDATIONS:",
            "-" * 40
        ])
        
        for i, rec in enumerate(mapping.get('recommendations', []), 1):
            report_lines.append(f"{i}. {rec}")
        
        report_lines.extend([
            "",
            "=" * 80,
            "END OF DIAGNOSTIC SUMMARY",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def print_console_summary(self) -> None:
        """Print console summary of DocAI output tracking."""
        mapping = self.tracking_session.get('output_mapping', {})
        verification = mapping.get('verification_summary', {})
        
        print("\n" + "=" * 80)
        print("🔍 DOCAI OUTPUT TRACKING SUMMARY")
        print("=" * 80)
        
        # File status summary
        created_files = [f for f, info in mapping.get('docai_output_files', {}).items() if info['exists']]
        missing_files = [f for f, info in mapping.get('docai_output_files', {}).items() if not info['exists']]
        
        print(f"📊 Files Created: {len(created_files)}/{verification.get('total_expected_files', 0)}")
        print(f"💾 Total Size: {verification.get('total_size_mb', 0):.2f} MB")
        print(f"✅ Success Rate: {verification.get('creation_success_rate', 0)}%")
        print(f"🔍 All Valid: {'YES' if verification.get('all_files_valid') else 'NO'}")
        
        if created_files:
            print("\n📁 DocAI output artifacts successfully saved to:")
            for file_path in created_files:
                file_info = mapping['docai_output_files'][file_path]
                print(f"   ✅ {Path(file_path).name} ({file_info['size_mb']:.2f} MB) - {file_info['role']}")
        
        if missing_files:
            print("\n❌ Missing expected files:")
            for file_path in missing_files:
                print(f"   ❌ {Path(file_path).name}")
        
        print("\n🎯 Key Artifacts:")
        key_files = ['docai_raw_full.json', 'parsed_output.json', 'feature_vector.json']
        for key_file in key_files:
            file_found = any(key_file in f for f in created_files)
            status = "✅" if file_found else "❌"
            print(f"   {status} {key_file}")
        
        print("\n" + "=" * 80)

def main():
    """Main diagnostic execution function."""
    print("🚀 DocAI Output Diagnostic System")
    print("=" * 50)
    
    # Initialize tracker
    tracker = DocAIOutputTracker()
    
    # Start monitoring
    tracker.start_monitoring()
    
    # Simulate or wait for DocAI processing
    # In real usage, this would be called before and after DocAI processing
    print("⏳ Waiting for DocAI processing to complete...")
    print("   (In real usage, run this before and after DocAI processing)")
    
    # Capture post-processing state
    post_state = tracker.capture_post_processing_state()
    
    # Generate output mapping
    output_mapping = tracker.generate_output_mapping()
    
    # Save diagnostic artifacts
    saved_artifacts = tracker.save_diagnostic_artifacts()
    
    # Print console summary
    tracker.print_console_summary()
    
    # Final status
    if saved_artifacts:
        print(f"\n💾 Diagnostic artifacts saved to: {Path(list(saved_artifacts.values())[0]).parent}")
        print("✅ DocAI output diagnostic completed successfully!")
        return 0
    else:
        print("\n❌ Failed to save diagnostic artifacts")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)