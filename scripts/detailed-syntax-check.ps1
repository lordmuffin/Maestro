$scriptPath = 'c:\Users\andre\Github\Maestro\scripts\provision-telegram-bot.ps1'
$parseErrors = @()
$tokens = @()

try {
    $ast = [System.Management.Automation.Language.Parser]::ParseFile(
        $scriptPath,
        [ref]$tokens,
        [ref]$parseErrors
    )

    if ($parseErrors.Count -eq 0) {
        Write-Host "✅ No syntax errors found!" -ForegroundColor Green
    } else {
        Write-Host "❌ Found $($parseErrors.Count) syntax error(s):" -ForegroundColor Red
        Write-Host ""

        foreach ($err in $parseErrors | Sort-Object { $_.Extent.StartLineNumber }) {
            Write-Host "Line $($err.Extent.StartLineNumber): $($err.Message)" -ForegroundColor Yellow
            Write-Host "  Context: $($err.Extent.Text -replace '\r?\n', ' ')" -ForegroundColor Gray
            Write-Host ""
        }
    }
} catch {
    Write-Host "❌ Fatal error parsing script:" -ForegroundColor Red
    Write-Host $_.Exception.Message
}
