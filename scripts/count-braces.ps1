$content = Get-Content 'c:\Users\andre\Github\Maestro\scripts\provision-telegram-bot.ps1' -Raw
$openBraces = ([regex]::Matches($content, '\{')).Count
$closeBraces = ([regex]::Matches($content, '\}')).Count
Write-Host "Open braces: $openBraces"
Write-Host "Close braces: $closeBraces"
Write-Host "Difference: $($openBraces - $closeBraces)"
