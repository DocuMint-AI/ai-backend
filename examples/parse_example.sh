#!/bin/bash

# DocAI Parse Example Script
# 
# This script demonstrates how to use the DocAI parsing API endpoint
# with various configuration options and document types.

set -e  # Exit on any error

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
GCS_BUCKET="${GCS_BUCKET:-your-bucket-name}"
DOCUMENT_PATH="${DOCUMENT_PATH:-documents/sample-contract.pdf}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    # Check if jq is available (optional, for pretty JSON output)
    if command -v jq &> /dev/null; then
        HAS_JQ=true
        log_success "jq found - will format JSON output"
    else
        HAS_JQ=false
        log_warning "jq not found - JSON output will not be formatted"
        log_info "Install jq for better output: apt-get install jq (Ubuntu) or brew install jq (Mac)"
    fi
}

check_api_health() {
    log_info "Checking API health..."
    
    response=$(curl -s -w "%{http_code}" -o /tmp/health_response.json "$API_BASE_URL/health" || echo "000")
    
    if [ "$response" = "200" ]; then
        log_success "API is healthy"
        if [ "$HAS_JQ" = true ]; then
            echo "Health status:"
            cat /tmp/health_response.json | jq '.'
        fi
    else
        log_error "API health check failed (HTTP $response)"
        if [ -f /tmp/health_response.json ]; then
            cat /tmp/health_response.json
        fi
        exit 1
    fi
    
    echo ""
}

# Example 1: Basic document parsing
example_basic_parse() {
    log_info "Example 1: Basic document parsing"
    
    GCS_URI="gs://${GCS_BUCKET}/${DOCUMENT_PATH}"
    
    # Create request payload
    cat > /tmp/parse_request.json << EOF
{
    "gcs_uri": "$GCS_URI",
    "confidence_threshold": 0.7
}
EOF

    log_info "Parsing document: $GCS_URI"
    log_info "Request payload:"
    if [ "$HAS_JQ" = true ]; then
        cat /tmp/parse_request.json | jq '.'
    else
        cat /tmp/parse_request.json
    fi
    
    # Make API request
    response_code=$(curl -s -w "%{http_code}" -o /tmp/parse_response.json \
        -X POST "$API_BASE_URL/api/docai/parse" \
        -H "Content-Type: application/json" \
        -d @/tmp/parse_request.json)
    
    if [ "$response_code" = "200" ]; then
        log_success "Document parsed successfully"
        
        if [ "$HAS_JQ" = true ]; then
            # Extract key information
            success=$(cat /tmp/parse_response.json | jq -r '.success')
            if [ "$success" = "true" ]; then
                processing_time=$(cat /tmp/parse_response.json | jq -r '.processing_time_seconds')
                entities_count=$(cat /tmp/parse_response.json | jq -r '.document.named_entities | length')
                clauses_count=$(cat /tmp/parse_response.json | jq -r '.document.clauses | length')
                
                echo "Processing time: ${processing_time}s"
                echo "Named entities found: $entities_count"
                echo "Clauses found: $clauses_count"
                
                echo ""
                echo "Sample entities:"
                cat /tmp/parse_response.json | jq -r '.document.named_entities[:3] | .[] | "- \(.type): \(.text_span.text) (confidence: \(.confidence))"'
                
                echo ""
                echo "Sample clauses:"
                cat /tmp/parse_response.json | jq -r '.document.clauses[:2] | .[] | "- \(.type): \(.text_span.text[:100])... (confidence: \(.confidence))"'
            else
                log_error "Processing failed:"
                cat /tmp/parse_response.json | jq -r '.error_message'
            fi
        else
            echo "Response:"
            cat /tmp/parse_response.json
        fi
    else
        log_error "API request failed (HTTP $response_code)"
        cat /tmp/parse_response.json
    fi
    
    echo ""
}

# Example 2: Advanced parsing with metadata
example_advanced_parse() {
    log_info "Example 2: Advanced parsing with custom metadata and settings"
    
    GCS_URI="gs://${GCS_BUCKET}/${DOCUMENT_PATH}"
    
    # Create advanced request payload
    cat > /tmp/advanced_request.json << EOF
{
    "gcs_uri": "$GCS_URI",
    "confidence_threshold": 0.8,
    "enable_native_pdf_parsing": true,
    "include_raw_response": false,
    "metadata": {
        "customer_id": "CUST-12345",
        "document_type": "contract",
        "department": "legal",
        "processed_by": "api-example"
    }
}
EOF

    log_info "Parsing document with advanced settings: $GCS_URI"
    log_info "Request payload:"
    if [ "$HAS_JQ" = true ]; then
        cat /tmp/advanced_request.json | jq '.'
    else
        cat /tmp/advanced_request.json
    fi
    
    # Make API request
    response_code=$(curl -s -w "%{http_code}" -o /tmp/advanced_response.json \
        -X POST "$API_BASE_URL/api/docai/parse" \
        -H "Content-Type: application/json" \
        -d @/tmp/advanced_request.json)
    
    if [ "$response_code" = "200" ]; then
        log_success "Advanced parsing completed"
        
        if [ "$HAS_JQ" = true ]; then
            success=$(cat /tmp/advanced_response.json | jq -r '.success')
            if [ "$success" = "true" ]; then
                document_id=$(cat /tmp/advanced_response.json | jq -r '.document.metadata.document_id')
                custom_metadata=$(cat /tmp/advanced_response.json | jq -r '.document.metadata.custom_metadata')
                
                echo "Document ID: $document_id"
                echo "Custom metadata: $custom_metadata"
            else
                log_error "Processing failed:"
                cat /tmp/advanced_response.json | jq -r '.error_message'
            fi
        else
            echo "Response:"
            cat /tmp/advanced_response.json
        fi
    else
        log_error "Advanced parsing failed (HTTP $response_code)"
        cat /tmp/advanced_response.json
    fi
    
    echo ""
}

# Example 3: Batch processing
example_batch_processing() {
    log_info "Example 3: Batch document processing"
    
    # Create batch request with multiple documents
    cat > /tmp/batch_request.json << EOF
[
    "gs://${GCS_BUCKET}/documents/contract1.pdf",
    "gs://${GCS_BUCKET}/documents/contract2.pdf",
    "gs://${GCS_BUCKET}/documents/invoice.pdf"
]
EOF

    log_info "Processing multiple documents in batch"
    log_info "Request payload:"
    if [ "$HAS_JQ" = true ]; then
        cat /tmp/batch_request.json | jq '.'
    else
        cat /tmp/batch_request.json
    fi
    
    # Make batch API request
    response_code=$(curl -s -w "%{http_code}" -o /tmp/batch_response.json \
        -X POST "$API_BASE_URL/api/docai/parse/batch" \
        -H "Content-Type: application/json" \
        -d @/tmp/batch_request.json)
    
    if [ "$response_code" = "200" ]; then
        log_success "Batch processing completed"
        
        if [ "$HAS_JQ" = true ]; then
            total_docs=$(cat /tmp/batch_response.json | jq -r '.total_documents')
            successful_docs=$(cat /tmp/batch_response.json | jq -r '.successful_documents')
            failed_docs=$(cat /tmp/batch_response.json | jq -r '.failed_documents')
            
            echo "Total documents: $total_docs"
            echo "Successful: $successful_docs"
            echo "Failed: $failed_docs"
            
            echo ""
            echo "Results summary:"
            cat /tmp/batch_response.json | jq -r '.results[] | "- \(.gcs_uri): \(if .success then "SUCCESS" else "FAILED (\(.error_message))" end)"'
        else
            echo "Response:"
            cat /tmp/batch_response.json
        fi
    else
        log_error "Batch processing failed (HTTP $response_code)"
        cat /tmp/batch_response.json
    fi
    
    echo ""
}

# Example 4: Get configuration and processors
example_config_info() {
    log_info "Example 4: Getting DocAI configuration and processor information"
    
    # Get configuration
    log_info "Getting DocAI configuration..."
    config_response=$(curl -s -w "%{http_code}" -o /tmp/config_response.json "$API_BASE_URL/api/docai/config")
    
    if [ "$config_response" = "200" ]; then
        log_success "Configuration retrieved"
        if [ "$HAS_JQ" = true ]; then
            echo "Current configuration:"
            cat /tmp/config_response.json | jq '.'
        else
            cat /tmp/config_response.json
        fi
    else
        log_error "Failed to get configuration (HTTP $config_response)"
    fi
    
    echo ""
    
    # Get processors
    log_info "Getting available processors..."
    processors_response=$(curl -s -w "%{http_code}" -o /tmp/processors_response.json "$API_BASE_URL/api/docai/processors")
    
    if [ "$processors_response" = "200" ]; then
        log_success "Processors retrieved"
        if [ "$HAS_JQ" = true ]; then
            echo "Available processors:"
            cat /tmp/processors_response.json | jq '.'
        else
            cat /tmp/processors_response.json
        fi
    else
        log_error "Failed to get processors (HTTP $processors_response)"
    fi
    
    echo ""
}

# Example 5: Error handling
example_error_handling() {
    log_info "Example 5: Error handling examples"
    
    # Test with invalid GCS URI
    log_info "Testing with invalid GCS URI..."
    cat > /tmp/error_request.json << EOF
{
    "gcs_uri": "invalid-uri-format",
    "confidence_threshold": 0.7
}
EOF

    response_code=$(curl -s -w "%{http_code}" -o /tmp/error_response.json \
        -X POST "$API_BASE_URL/api/docai/parse" \
        -H "Content-Type: application/json" \
        -d @/tmp/error_request.json)
    
    log_info "Response code: $response_code (expected: 422 for validation error)"
    if [ "$HAS_JQ" = true ]; then
        cat /tmp/error_response.json | jq '.'
    else
        cat /tmp/error_response.json
    fi
    
    echo ""
}

# Main execution
main() {
    echo "======================================"
    echo "  DocAI API Examples"
    echo "======================================"
    echo ""
    
    # Parse command line arguments
    case "${1:-all}" in
        "basic")
            check_dependencies
            check_api_health
            example_basic_parse
            ;;
        "advanced")
            check_dependencies
            check_api_health
            example_advanced_parse
            ;;
        "batch")
            check_dependencies
            check_api_health
            example_batch_processing
            ;;
        "config")
            check_dependencies
            check_api_health
            example_config_info
            ;;
        "errors")
            check_dependencies
            check_api_health
            example_error_handling
            ;;
        "all"|*)
            log_info "Running all examples..."
            check_dependencies
            check_api_health
            example_basic_parse
            example_advanced_parse
            example_batch_processing
            example_config_info
            example_error_handling
            ;;
    esac
    
    # Cleanup
    rm -f /tmp/parse_request.json /tmp/parse_response.json
    rm -f /tmp/advanced_request.json /tmp/advanced_response.json
    rm -f /tmp/batch_request.json /tmp/batch_response.json
    rm -f /tmp/config_response.json /tmp/processors_response.json
    rm -f /tmp/error_request.json /tmp/error_response.json
    rm -f /tmp/health_response.json
    
    log_success "Examples completed!"
    echo ""
    echo "Usage: $0 [basic|advanced|batch|config|errors|all]"
    echo ""
    echo "Environment variables:"
    echo "  API_BASE_URL     - API base URL (default: http://localhost:8000)"
    echo "  GCS_BUCKET       - GCS bucket name (default: your-bucket-name)"
    echo "  DOCUMENT_PATH    - Document path in bucket (default: documents/sample-contract.pdf)"
}

# Run main function with all arguments
main "$@"