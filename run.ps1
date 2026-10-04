param([ValidateSet('resume','check','preview','status','uninstall')][string]$Mode='check')
$ErrorActionPreference='Stop'
try {
    Set-Location -LiteralPath $PSScriptRoot
    . (Join-Path $PSScriptRoot 'runtime.ps1')
    if ($Mode -eq 'uninstall') { & (Join-Path $PSScriptRoot 'uninstall-task.ps1');exit }
    $python=Find-DigestPython
    if ($Mode -eq 'resume') { & (Join-Path $PSScriptRoot 'activate.ps1') -PythonPath $python;exit }
    & $python (Join-Path $PSScriptRoot 'digest.py') $Mode
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if ($Mode -eq 'preview') { Start-Process (Join-Path $PSScriptRoot 'preview.html') }
} catch { Write-Host ('STOPPED: '+$_.Exception.Message);exit 1 }
