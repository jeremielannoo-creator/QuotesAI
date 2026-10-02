# ============================================================
# setup_schedule_windows.ps1
# Crée les deux tâches planifiées Windows pour pipeline_book.py
#
# Exécuter UNE FOIS en PowerShell Admin :
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\setup_schedule_windows.ps1
# ============================================================

$scriptDir  = "C:\Claude Agents\QuotesAI"
$batFile    = "$scriptDir\run_book_pipeline.bat"
$logDir     = "$scriptDir\logs"
$taskName1  = "QuotesAI-Book-Mercredi"
$taskName2  = "QuotesAI-Book-Dimanche"

# Créer le dossier logs si absent
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
    Write-Host "Dossier logs créé."
}

# Action commune
$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$batFile`""

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# ── Tâche 1 : Mercredi 19h00 ──────────────────────────────
$trigger1 = New-ScheduledTaskTrigger `
    -Weekly -DaysOfWeek Wednesday -At "19:00"

Register-ScheduledTask `
    -TaskName  $taskName1 `
    -Action    $action `
    -Trigger   $trigger1 `
    -Settings  $settings `
    -RunLevel  Highest `
    -Force | Out-Null

Write-Host "Tâche créée : $taskName1 (mercredi 19h00)"

# ── Tâche 2 : Dimanche 10h30 ──────────────────────────────
$trigger2 = New-ScheduledTaskTrigger `
    -Weekly -DaysOfWeek Sunday -At "10:30"

Register-ScheduledTask `
    -TaskName  $taskName2 `
    -Action    $action `
    -Trigger   $trigger2 `
    -Settings  $settings `
    -RunLevel  Highest `
    -Force | Out-Null

Write-Host "Tâche créée : $taskName2 (dimanche 10h30)"

Write-Host ""
Write-Host "Pipeline planifié 2x/semaine."
Write-Host "Pour vérifier : Get-ScheduledTask -TaskName 'QuotesAI*'"
Write-Host "Pour tester   : Start-ScheduledTask -TaskName '$taskName1'"
