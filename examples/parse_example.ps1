# DocAI Parse Example Script - PowerShell Version
# 
# This script demonstrates how to use the DocAI parsing API endpoint
# with various configuration options and document types on Windows.

param(
    [string]$Example = "basic",
    [string]$ApiBaseUrl = "http://localhost:8000",
    [string]$GcsBucket = "your-bucket-name", 
    [string]$DocumentPath = "documents/sample-contract.pdf"
)

# Configuration
$ErrorActionPreference = "Stop"

# Helper functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-ApiHealth {
    Write-Info "Checking API health..."
    
    try {
        $response = Invoke-RestMethod -Uri "$ApiBaseUrl/health" -Method Get
        Write-Success "API is healthy"
        Write-Host "Health status:" -ForegroundColor Cyan
        $response | ConvertTo-Json -Depth 10 | Write-Host
        return $true
    }
    catch {
        Write-Error "API health check failed: $($_.Exception.Message)"
        return $false
    }
}

function Invoke-BasicParse {
    Write-Info "Example 1: Basic document parsing"
    
    $gcsUri = "gs://$GcsBucket/$DocumentPath"
    
    $requestBody = @{
        gcs_uri = $gcsUri
        confidence_threshold = 0.7
    } | ConvertTo-Json
    
    Write-Info "Parsing document: $gcsUri"
    Write-Host "Request payload:" -ForegroundColor Cyan
    $requestBody | Write-Host
    
    try {
        $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/docai/parse" -Method Post -Body $requestBody -ContentType "application/json"
        
        if ($response.success) {
            Write-Success "Document parsed successfully"
            
            $processingTime = $response.processing_time_seconds
            $entitiesCount = $response.document.named_entities.Count
            $clausesCount = $response.document.clauses.Count
            
            Write-Host "Processing time: ${processingTime}s"
            Write-Host "Named entities found: $entitiesCount"
            Write-Host "Clauses found: $clausesCount"
            
            if ($entitiesCount -gt 0) {
                Write-Host "`nSample entities:" -ForegroundColor Cyan
                $response.document.named_entities | Select-Object -First 3 | ForEach-Object {
                    Write-Host "- $($_.type): $($_.text_span.text) (confidence: $($_.confidence))"
                }
            }
            
            if ($clausesCount -gt 0) {
                Write-Host "`nSample clauses:" -ForegroundColor Cyan
                $response.document.clauses | Select-Object -First 2 | ForEach-Object {
                    $truncatedText = if ($_.text_span.text.Length -gt 100) { 
                        $_.text_span.text.Substring(0, 100) + "..." 
                    } else { 
                        $_.text_span.text 
                    }
                    Write-Host "- $($_.type): $truncatedText (confidence: $($_.confidence))"
                }
            }
        }
        else {
            Write-Error "Processing failed: $($response.error_message)"
        }
    }
    catch {
        Write-Error "API request failed: $($_.Exception.Message)"
        if ($_.Exception.Response) {
            $statusCode = $_.Exception.Response.StatusCode
            Write-Error "HTTP Status: $statusCode"
        }
    }
}

function Invoke-AdvancedParse {
    Write-Info "Example 2: Advanced parsing with custom metadata and settings"
    
    $gcsUri = "gs://$GcsBucket/$DocumentPath"
    
    $requestBody = @{
        gcs_uri = $gcsUri
        confidence_threshold = 0.8
        enable_native_pdf_parsing = $true
        include_raw_response = $false
        metadata = @{
            customer_id = "CUST-12345"
            document_type = "contract"
            department = "legal"
            processed_by = "powershell-example"
        }
    } | ConvertTo-Json -Depth 10
    
    Write-Info "Parsing document with advanced settings: $gcsUri"
    Write-Host "Request payload:" -ForegroundColor Cyan
    $requestBody | Write-Host
    
    try {
        $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/docai/parse" -Method Post -Body $requestBody -ContentType "application/json"
        
        if ($response.success) {
            Write-Success "Advanced parsing completed"
            
            $documentId = $response.document.metadata.document_id
            $customMetadata = $response.document.metadata.custom_metadata | ConvertTo-Json -Compress
            
            Write-Host "Document ID: $documentId"
            Write-Host "Custom metadata: $customMetadata"
        }
        else {
            Write-Error "Processing failed: $($response.error_message)"
        }
    }
    catch {
        Write-Error "Advanced parsing failed: $($_.Exception.Message)"
    }
}

function Invoke-ConfigInfo {
    Write-Info "Getting DocAI configuration and processor information"
    
    try {
        Write-Info "Getting DocAI configuration..."
        $config = Invoke-RestMethod -Uri "$ApiBaseUrl/api/docai/config" -Method Get
        Write-Success "Configuration retrieved"
        Write-Host "Current configuration:" -ForegroundColor Cyan
        $config | ConvertTo-Json -Depth 10 | Write-Host
        
        Write-Info "`nGetting available processors..."
        $processors = Invoke-RestMethod -Uri "$ApiBaseUrl/api/docai/processors" -Method Get
        Write-Success "Processors retrieved"
        Write-Host "Available processors:" -ForegroundColor Cyan
        $processors | ConvertTo-Json -Depth 10 | Write-Host
    }
    catch {
        Write-Error "Failed to get configuration/processors: $($_.Exception.Message)"
    }
}

function Invoke-ErrorHandling {
    Write-Info "Example: Error handling"
    
    Write-Info "Testing with invalid GCS URI..."
    
    $requestBody = @{
        gcs_uri = "invalid-uri-format"
        confidence_threshold = 0.7
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$ApiBaseUrl/api/docai/parse" -Method Post -Body $requestBody -ContentType "application/json"
        Write-Host "Unexpected success - should have failed with validation error"
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Info "Response code: $statusCode (expected: 422 for validation error)"
        
        if ($_.ErrorDetails.Message) {
            $errorResponse = $_.ErrorDetails.Message | ConvertFrom-Json
            $errorResponse | ConvertTo-Json -Depth 10 | Write-Host
        }
    }
}

# Main execution
function Main {
    Write-Host "======================================" -ForegroundColor Magenta
    Write-Host "  DocAI API Examples - PowerShell" -ForegroundColor Magenta
    Write-Host "======================================" -ForegroundColor Magenta
    Write-Host ""
    
    # Check API health first
    if (!(Test-ApiHealth)) {
        Write-Error "API is not healthy. Please check your configuration."
        return
    }
    
    Write-Host ""
    
    switch ($Example.ToLower()) {
        "basic" {
            Invoke-BasicParse
        }
        "advanced" {
            Invoke-AdvancedParse
        }
        "config" {
            Invoke-ConfigInfo
        }
        "errors" {
            Invoke-ErrorHandling
        }
        "all" {
            Write-Info "Running all examples..."
            Invoke-BasicParse
            Write-Host "`n" + "="*50 + "`n"
            Invoke-AdvancedParse
            Write-Host "`n" + "="*50 + "`n"
            Invoke-ConfigInfo
            Write-Host "`n" + "="*50 + "`n"
            Invoke-ErrorHandling
        }
        default {
            Write-Error "Invalid example type. Use: basic, advanced, config, errors, or all"
        }
    }
    
    Write-Host ""
    Write-Success "Examples completed!"
    Write-Host ""
    Write-Host "Usage: .\parse_example.ps1 [-Example <basic|advanced|config|errors|all>] [-ApiBaseUrl <url>] [-GcsBucket <bucket>] [-DocumentPath <path>]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -Example        - Example type to run (default: basic)"
    Write-Host "  -ApiBaseUrl     - API base URL (default: http://localhost:8000)"
    Write-Host "  -GcsBucket      - GCS bucket name (default: your-bucket-name)"
    Write-Host "  -DocumentPath   - Document path in bucket (default: documents/sample-contract.pdf)"
}

# Run the script
try {
    Main
}
catch {
    Write-Error "Script execution failed: $($_.Exception.Message)"
    exit 1
}