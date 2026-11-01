# Runs `main.py --live` and restarts it after failures (for example, no network at boot).
# Exit codes from main.py: 0 (clean stop) and 2 (needs a human, e.g. not logged in)
# end the loop. Anything else is retried after a delay.

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = 'python'
}

# rich prints arrows and redirected Windows output would otherwise be cp1252.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$logDir = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'live.log'
$maxLogBytes = 10MB
$retrySeconds = 30

function Write-Log([string]$message) {
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Path $log -Value "$stamp $message" -Encoding UTF8
}

while ($true) {
    if ((Test-Path $log) -and ((Get-Item $log).Length -gt $maxLogBytes)) {
        Move-Item -Path $log -Destination "$log.1" -Force
    }

    Write-Log 'Starting main.py --live'
    try {
        & $python main.py --live *>> $log
        $exitCode = $LASTEXITCODE
    } catch {
        Write-Log "Could not start python: $_"
        $exitCode = 1
    }

    if ($exitCode -eq 0 -or $exitCode -eq 2) {
        Write-Log "main.py --live exited with code $exitCode. Not restarting."
        exit $exitCode
    }

    Write-Log "main.py --live exited with code $exitCode. Retrying in $retrySeconds seconds."
    Start-Sleep -Seconds $retrySeconds
}
