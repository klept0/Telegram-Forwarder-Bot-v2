# Registers (or removes) a per-user Windows scheduled task that starts Live Forward at logon.
#   .\scripts\install-startup-task.ps1                 Install or update the task
#   .\scripts\install-startup-task.ps1 -Uninstall      Remove the task

param(
    [switch]$Uninstall,
    [string]$TaskName = 'TelegramForwarderLive',
    [int]$DelaySeconds = 30
)

$ErrorActionPreference = 'Stop'

if ($Uninstall) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed scheduled task '$TaskName'."
    } else {
        Write-Host "Scheduled task '$TaskName' is not registered. Nothing to remove."
    }
    return
}

$runScript = (Resolve-Path (Join-Path $PSScriptRoot 'run-live.ps1')).Path
$root = Split-Path $PSScriptRoot -Parent
$user = "$env:USERDOMAIN\$env:USERNAME"

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$trigger.Delay = "PT${DelaySeconds}S"

$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runScript`""

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName $TaskName -Trigger $trigger -Principal $principal `
    -Action $action -Settings $settings -Force | Out-Null

Write-Host "Registered scheduled task '$TaskName' for $user."
Write-Host "  Runs at logon (after a $DelaySeconds second delay): $runScript"
Write-Host "  Log file: $(Join-Path $root 'logs\live.log')"
Write-Host "  Start it now:  Start-ScheduledTask -TaskName $TaskName"
Write-Host "  View the log:  Get-Content '$(Join-Path $root 'logs\live.log')' -Tail 50"
Write-Host "  Remove it:     .\scripts\install-startup-task.ps1 -Uninstall"
