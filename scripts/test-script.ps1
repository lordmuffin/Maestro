Write-Host "Testing script loading..."
try {
    . 'c:\Users\andre\Github\Maestro\scripts\provision-telegram-bot.ps1'
    Write-Host "Script loaded successfully!" -ForegroundColor Green
} catch {
    Write-Host "Error loading script:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host $_.ScriptStackTrace
}
