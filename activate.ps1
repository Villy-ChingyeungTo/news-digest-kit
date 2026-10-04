param([Parameter(Mandatory=$true)][string]$PythonPath)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime.ps1')
$configPath=Join-Path $PSScriptRoot 'config.json'
$cfg=Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
& $PythonPath (Join-Path $PSScriptRoot 'digest.py') test-email
if ($LASTEXITCODE -ne 0) { throw 'Email test failed. No scheduler installed. See README troubleshooting.' }
& $PythonPath (Join-Path $PSScriptRoot 'digest.py') preview
if ($LASTEXITCODE -ne 0) { throw 'Preview failed. Scheduling was not enabled.' }
Start-Process (Join-Path $PSScriptRoot 'preview.html')
Write-Host 'Check the inbox and source status. Public RSS is incomplete; some sections may be unavailable.'
if ((Read-Host 'Test email received and ready to enable scheduling? Type YES') -cne 'YES') { Write-Host 'Not activated.'; return }
$cfg.activated_at=[DateTimeOffset]::Now.ToOffset([TimeSpan]::FromHours(8)).ToString('yyyy-MM-ddTHH:mm:sszzz')
$cfg.enabled=$true
try {
    & (Join-Path $PSScriptRoot 'install-task.ps1') -PythonPath $PythonPath
    Save-DigestConfig $cfg $configPath
} catch { $cfg.enabled=$false;Save-DigestConfig $cfg $configPath;throw }
