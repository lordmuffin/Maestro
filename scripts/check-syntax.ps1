$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    'c:\Users\andre\Github\Maestro\scripts\provision-telegram-bot.ps1',
    [ref]$null,
    [ref]$errors
)

if ($errors) {
    Write-Host "Syntax errors found:" -ForegroundColor Red
    $errors | ForEach-Object {
        Write-Host "Line $($_.Extent.StartLineNumber): $($_.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "No syntax errors found!" -ForegroundColor Green
}
