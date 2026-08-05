# Cleanup script - Remove non-required components from MediAI
$ErrorActionPreference = "Continue"

$dirsToRemove = @(
    "core\ai\mcp",
    "core\ai\agents",
    "core\ai\orchestration",
    "core\ai\conversation",
    "domains\medai\ai\mcp",
    "infrastructure\docker",
    "infrastructure\nginx",
    ".github",
    "docs",
    "tests",
    "apps\api\middleware"
)

$filesToRemove = @(
    "core\models\audit_log.py"
)

foreach ($dir in $dirsToRemove) {
    $fullPath = Join-Path $PSScriptRoot $dir
    if (Test-Path $fullPath) {
        Remove-Item -Recurse -Force $fullPath
        Write-Host "Removed: $dir" -ForegroundColor Green
    } else {
        Write-Host "Not found: $dir" -ForegroundColor Yellow
    }
}

foreach ($file in $filesToRemove) {
    $fullPath = Join-Path $PSScriptRoot $file
    if (Test-Path $fullPath) {
        Remove-Item -Force $fullPath
        Write-Host "Removed: $file" -ForegroundColor Green
    } else {
        Write-Host "Not found: $file" -ForegroundColor Yellow
    }
}

# Self-delete
Remove-Item -Force $MyInvocation.MyCommand.Path
Write-Host "`nCleanup complete!" -ForegroundColor Cyan
