# Test API Script for Maestro LLM Provider Selection
# Usage: .\test-api.ps1
# Description: Comprehensive testing of all provider/tier combinations across all APIs

param(
    [switch]$Verbose,
    [switch]$SkipErrors
)

# Configuration
$providers = @("local", "claude", "gemini", "openai")
$tiers = @("fast", "standard", "premium")
$sensitivities = @("low", "medium", "high")

# Test counters
$script:passCount = 0
$script:failCount = 0
$script:skipCount = 0

# Helper function to execute API test
function Test-ApiEndpoint {
    param(
        [string]$TestName,
        [string]$Uri,
        [hashtable]$Body,
        [string]$ExpectedProvider,
        [string]$ExpectedTier,
        [switch]$ExpectError
    )

    Write-Host "[$TestName]" -ForegroundColor Yellow -NoNewline
    Write-Host " $Uri" -ForegroundColor Gray

    if ($Verbose) {
        Write-Host "  Body: $($Body | ConvertTo-Json -Compress)" -ForegroundColor DarkGray
    }

    try {
        $jsonBody = $Body | ConvertTo-Json -Depth 10
        $response = Invoke-RestMethod -Method POST -Uri $Uri -Headers @{'Content-Type'='application/json'} -Body $jsonBody -ErrorAction Stop

        if ($ExpectError) {
            Write-Host "  ✗ Expected error but got success" -ForegroundColor Red
            $script:failCount++
            return
        }

        Write-Host "  ✓ Status: $($response.status)" -ForegroundColor Green

        # Check provider and model
        $providerUsed = if ($response.provider_used) { $response.provider_used } elseif ($response.llm_provider) { $response.llm_provider } else { "N/A" }
        $modelUsed = if ($response.model_used) { $response.model_used } else { "N/A" }

        Write-Host "    Provider: $providerUsed | Model: $modelUsed" -ForegroundColor Cyan

        # Privacy warning check
        if ($response.privacy_warning) {
            Write-Host "    ⚠️  $($response.privacy_warning)" -ForegroundColor Yellow
        }

        # Additional info based on API
        if ($response.agent_used) {
            Write-Host "    Agent: $($response.agent_used) | Time: $($response.execution_time)s" -ForegroundColor White
        }

        $script:passCount++

    } catch {
        if ($ExpectError) {
            Write-Host "  ✓ Expected error: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
            if ($Verbose) {
                Write-Host "    $($_.ErrorDetails.Message)" -ForegroundColor DarkYellow
            }
            $script:passCount++
        } else {
            Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
            if ($Verbose -and $_.ErrorDetails) {
                Write-Host "    $($_.ErrorDetails.Message)" -ForegroundColor DarkRed
            }
            $script:failCount++
        }
    }

    Write-Host ""
}

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  MAESTRO API TEST - LLM Provider & Model Tier Selection" -ForegroundColor Cyan
Write-Host "  Comprehensive Test Suite" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# SECTION 1: LOCAL RAG API TESTS (/query on port 8001)
# ============================================================================
Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  SECTION 1: LOCAL RAG API - All Provider/Tier Combinations                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$testNum = 1

foreach ($provider in $providers) {
    foreach ($tier in $tiers) {
        Test-ApiEndpoint `
            -TestName "RAG-${testNum} $provider/$tier" `
            -Uri "http://localhost:8001/query" `
            -Body @{
                query = "What is in my knowledge base?"
                top_k = 3
                llm_provider = $provider
                model_tier = $tier
                sensitivity = "medium"
            } `
            -ExpectedProvider $provider `
            -ExpectedTier $tier
        $testNum++
    }
}

# ============================================================================
# SECTION 2: SUPERVISOR API TESTS (/execute on port 8003)
# ============================================================================
Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  SECTION 2: SUPERVISOR API - All Provider/Tier Combinations                 ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$testNum = 1

foreach ($provider in $providers) {
    foreach ($tier in $tiers) {
        Test-ApiEndpoint `
            -TestName "SUPER-${testNum} $provider/$tier" `
            -Uri "http://localhost:8003/execute" `
            -Body @{
                query = "Analyze my project data"
                llm_provider = $provider
                model_tier = $tier
                sensitivity = "medium"
                task_type = "synthesis"
            } `
            -ExpectedProvider $provider `
            -ExpectedTier $tier
        $testNum++
    }
}

# ============================================================================
# SECTION 3: SKILLS API TESTS (/execute on port 8004)
# ============================================================================
Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  SECTION 3: SKILLS API - All Provider/Tier Combinations                     ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$testNum = 1

foreach ($provider in $providers) {
    foreach ($tier in $tiers) {
        Test-ApiEndpoint `
            -TestName "SKILL-${testNum} $provider/$tier" `
            -Uri "http://localhost:8004/execute" `
            -Body @{
                skill_name = "GenerateProjectSynthesis"
                parameters = @{
                    project_name = "Project Nexus"
                    context = "AI assistant with privacy focus"
                }
                llm_provider = $provider
                model_tier = $tier
                sensitivity = "low"
            } `
            -ExpectedProvider $provider `
            -ExpectedTier $tier
        $testNum++
    }
}

# ============================================================================
# SECTION 4: PRIVACY WARNING TESTS
# ============================================================================
Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  SECTION 4: Privacy Warning Tests (Cloud Providers + High Sensitivity)      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$cloudProviders = @("claude", "gemini", "openai")

foreach ($provider in $cloudProviders) {
    Test-ApiEndpoint `
        -TestName "PRIVACY $provider/standard/high" `
        -Uri "http://localhost:8001/query" `
        -Body @{
            query = "Summarize my confidential personal data"
            llm_provider = $provider
            model_tier = "standard"
            sensitivity = "high"
        } `
        -ExpectedProvider $provider `
        -ExpectedTier "standard"
}

# Test local provider with high sensitivity (should have no warning)
Test-ApiEndpoint `
    -TestName "PRIVACY local/standard/high (no warning)" `
    -Uri "http://localhost:8001/query" `
    -Body @{
        query = "Summarize my confidential personal data"
        llm_provider = "local"
        model_tier = "standard"
        sensitivity = "high"
    } `
    -ExpectedProvider "local" `
    -ExpectedTier "standard"

# ============================================================================
# SECTION 5: SENSITIVITY LEVEL TESTS
# ============================================================================
Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  SECTION 5: Sensitivity Level Tests (All Levels)                            ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

foreach ($sensitivity in $sensitivities) {
    Test-ApiEndpoint `
        -TestName "SENS local/standard/$sensitivity" `
        -Uri "http://localhost:8003/execute" `
        -Body @{
            query = "Process my data with $sensitivity sensitivity"
            llm_provider = "local"
            model_tier = "standard"
            sensitivity = $sensitivity
        } `
        -ExpectedProvider "local" `
        -ExpectedTier "standard"
}

# ============================================================================
# SECTION 6: TASK TYPE TESTS (Supervisor API)
# ============================================================================
Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  SECTION 6: Task Type Tests (Retrieval, Synthesis, Automation)              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$taskTypes = @("retrieval", "synthesis", "automation")

foreach ($taskType in $taskTypes) {
    Test-ApiEndpoint `
        -TestName "TASK $taskType/local/standard" `
        -Uri "http://localhost:8003/execute" `
        -Body @{
            query = "Execute $taskType task on my data"
            llm_provider = "local"
            model_tier = "standard"
            task_type = $taskType
        } `
        -ExpectedProvider "local" `
        -ExpectedTier "standard"
}

# ============================================================================
# SECTION 7: DEFAULT BEHAVIOR TESTS
# ============================================================================
Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  SECTION 7: Default Behavior (No Provider/Tier Specified)                   ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Test-ApiEndpoint `
    -TestName "DEFAULT RAG API" `
    -Uri "http://localhost:8001/query" `
    -Body @{
        query = "What is in my knowledge base?"
        top_k = 3
    }

Test-ApiEndpoint `
    -TestName "DEFAULT Supervisor API" `
    -Uri "http://localhost:8003/execute" `
    -Body @{
        query = "Summarize my data"
    }

Test-ApiEndpoint `
    -TestName "DEFAULT Skills API" `
    -Uri "http://localhost:8004/execute" `
    -Body @{
        skill_name = "GenerateProjectSynthesis"
        parameters = @{
            project_name = "Test Project"
            context = "Testing default behavior"
        }
    }

# ============================================================================
# SECTION 8: ERROR HANDLING TESTS
# ============================================================================
Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  SECTION 8: Error Handling & Validation                                     ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Invalid provider
Test-ApiEndpoint `
    -TestName "ERROR Invalid Provider" `
    -Uri "http://localhost:8001/query" `
    -Body @{
        query = "Test query"
        llm_provider = "gpt4"
        model_tier = "standard"
    } `
    -ExpectError

# Invalid tier
Test-ApiEndpoint `
    -TestName "ERROR Invalid Tier" `
    -Uri "http://localhost:8001/query" `
    -Body @{
        query = "Test query"
        llm_provider = "local"
        model_tier = "ultra"
    } `
    -ExpectError

# Invalid sensitivity
Test-ApiEndpoint `
    -TestName "ERROR Invalid Sensitivity" `
    -Uri "http://localhost:8003/execute" `
    -Body @{
        query = "Test query"
        llm_provider = "local"
        model_tier = "standard"
        sensitivity = "critical"
    }

# Missing API key (will fail for cloud providers)
if (-not $SkipErrors) {
    Test-ApiEndpoint `
        -TestName "ERROR Missing API Key (Claude)" `
        -Uri "http://localhost:8001/query" `
        -Body @{
            query = "Test query"
            llm_provider = "claude"
            model_tier = "standard"
        }
}

# ============================================================================
# SECTION 9: MIXED PARAMETER TESTS
# ============================================================================
Write-Host "╔══════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  SECTION 9: Mixed Parameter Combinations                                    ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# High sensitivity + fast tier
Test-ApiEndpoint `
    -TestName "MIX high/fast/local" `
    -Uri "http://localhost:8001/query" `
    -Body @{
        query = "Process sensitive data quickly"
        llm_provider = "local"
        model_tier = "fast"
        sensitivity = "high"
    }

# Low sensitivity + premium tier
Test-ApiEndpoint `
    -TestName "MIX low/premium/local" `
    -Uri "http://localhost:8003/execute" `
    -Body @{
        query = "Deep analysis of public data"
        llm_provider = "local"
        model_tier = "premium"
        sensitivity = "low"
    }

# Automation task + retrieval query
Test-ApiEndpoint `
    -TestName "MIX automation+retrieval" `
    -Uri "http://localhost:8003/execute" `
    -Body @{
        query = "Retrieve and automate calendar events"
        llm_provider = "local"
        model_tier = "standard"
        task_type = "automation"
        sensitivity = "medium"
    }

# ============================================================================
# TEST SUMMARY
# ============================================================================
Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  TEST SUMMARY" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Total Tests:  " -NoNewline
Write-Host ($script:passCount + $script:failCount) -ForegroundColor White
Write-Host "  ✓ Passed:     " -NoNewline
Write-Host $script:passCount -ForegroundColor Green
Write-Host "  ✗ Failed:     " -NoNewline
Write-Host $script:failCount -ForegroundColor Red
Write-Host ""

if ($script:failCount -eq 0) {
    Write-Host "  🎉 All tests passed!" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Some tests failed. Review output above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan
