$ErrorActionPreference = 'Stop'
$path = Join-Path $PSScriptRoot 'private\task-name.txt'
if (Test-Path -LiteralPath $path) {
    $name = (Get-Content -LiteralPath $path -Raw).Trim()
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
}
$config = Join-Path $PSScriptRoot 'config.json'
if (Test-Path -LiteralPath $config) {
    $cfg = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
    $cfg.enabled = $false
    $cfg | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $config -Encoding UTF8
}
Write-Host 'Scheduling disabled. Configuration and history preserved.'
