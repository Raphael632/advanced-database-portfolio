param(
    [ValidateSet('all','fetch','build','validate','test')][string]$Action = 'all',
    [string]$Workspace = (Join-Path (Split-Path $PSScriptRoot -Parent) '.local')
)
$ErrorActionPreference = 'Stop'
$prefix = 'Ezenduka_Chukwubuikem_301913360'
$phasePath = $PSScriptRoot
$candidatePaths = @(
    (Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'),
    'python'
)
$portfolioPython = $null
foreach ($candidatePath in $candidatePaths) {
    if (Get-Command $candidatePath -ErrorAction SilentlyContinue) {
        & $candidatePath -c "import sqlite3,openpyxl; assert sqlite3.sqlite_version_info >= (3,37,0)" 2>$null
        if ($LASTEXITCODE -eq 0) { $portfolioPython = $candidatePath; break }
    }
}
if (-not $portfolioPython) {
    throw 'Install Python 3.12+ with SQLite 3.37+ and openpyxl 3.1.5. See the project README.'
}
if ($Action -ne 'test') {
    $buildAction = $Action
    if ($Action -eq 'all' -and (Test-Path (Join-Path $Workspace ($prefix + '_Food_Prices.sqlite3')))) {
        $buildAction = 'validate'
    }
    & $portfolioPython -X utf8 (Join-Path $phasePath 'build.py') $buildAction --workspace $Workspace
    if ($LASTEXITCODE -ne 0) { throw 'Portfolio database operation failed; inspect the error above.' }
}
if ($Action -in @('all','test')) {
    & $portfolioPython -X utf8 (Join-Path $phasePath 'tests.py')
    if ($LASTEXITCODE -ne 0) { throw 'Portfolio tests failed.' }
}
