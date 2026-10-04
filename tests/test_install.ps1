$ErrorActionPreference='Stop'
$project = Split-Path $PSScriptRoot
# Test discovery without writing private runtime state into the release tree.
. (Join-Path $project 'runtime.ps1')
function Save-PythonPath($path) { }
$python = Find-DigestPython
if (-not (Test-Path -LiteralPath $python)) { throw 'Runtime discovery failed' }
$version = & $python -c 'import sys; print(sys.version_info >= (3,10))'
if ($version -notcontains 'True') { throw 'Unsupported interpreter selected' }
# Same format rules as the setup prompt, with synthetic data only.
foreach ($case in @(
    @{Value='abcd efgh ijkl mnop';Expected=$true},
    @{Value='abcdefghijklmno';Expected=$false},
    @{Value='abcdefghijklmnop';Expected=$true},
    @{Value='1234567890123456';Expected=$false}
)) {
    $normalized = $case.Value -replace '\s',''
    if (($normalized -cmatch '^[a-zA-Z]{16}$') -ne $case.Expected) { throw 'Password format case failed' }
}
Write-Host 'Runtime discovery and synthetic password-format checks passed.'
