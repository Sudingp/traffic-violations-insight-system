# Registers a Windows scheduled task that runs the live ingest every day.
# Usage (PowerShell):  .\scripts\register_daily_task.ps1            # 07:30 daily
#                      .\scripts\register_daily_task.ps1 -At "21:00"
#   Remove it later:   Unregister-ScheduledTask -TaskName "TrafficViolationsIngest"
param(
    [string]$At = "07:30",
    [string]$TaskName = "TrafficViolationsIngest"
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$bat = Join-Path $projectRoot "scripts\run_ingest.bat"

$action   = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $projectRoot
$trigger  = New-ScheduledTaskTrigger -Daily -At $At
# Run even if the laptop was asleep at the scheduled time; retry twice on failure.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 2 `
            -RestartInterval (New-TimeSpan -Minutes 15) `
            -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Incremental ingest of Montgomery County traffic violations" -Force

Write-Host "Registered '$TaskName' to run daily at $At. Logs: $projectRoot\logs\ingest.log"
