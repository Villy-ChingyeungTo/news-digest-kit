$ErrorActionPreference = 'Stop'
function Find-DigestPython {
    $candidates = @()
    if ($env:NEWS_DIGEST_PYTHON) { $candidates += $env:NEWS_DIGEST_PYTHON }
    $remembered = Join-Path $PSScriptRoot 'private\python-path.txt'
    if (Test-Path -LiteralPath $remembered) { $candidates += ([IO.File]::ReadAllText($remembered)).Trim() }
    $candidates += @(Get-Command python.exe -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
    $candidates += @((Join-Path $env:USERPROFILE 'anaconda3\python.exe'),(Join-Path $env:USERPROFILE 'miniconda3\python.exe'))
    foreach ($root in @('HKCU:\Software\Python\PythonCore','HKLM:\Software\Python\PythonCore')) {
        if (Test-Path $root) {
            foreach ($key in (Get-ChildItem $root)) {
                $entry = Get-ItemProperty ($key.PSPath + '\InstallPath') -ErrorAction SilentlyContinue
                if ($entry.ExecutablePath) { $candidates += $entry.ExecutablePath }
            }
        }
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not $candidate -or $candidate -like '*\WindowsApps\*' -or -not (Test-Path -LiteralPath $candidate)) { continue }
        try {
            $probe = & $candidate -c "import sys; print('DIGEST_OK' if sys.version_info >= (3,10) else 'OLD')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $probe -contains 'DIGEST_OK') { Save-PythonPath $candidate;return $candidate }
        } catch { continue }
    }
    $manual = Read-Host 'Python 3.10+ not found. Paste the full path to python.exe (or press Enter to stop)'
    $manual = $manual.Trim().Trim('"')
    if (-not $manual -or -not (Test-Path -LiteralPath $manual)) { throw 'Install Python 3.10+ from python.org, then run setup again.' }
    $probe = & $manual -c "import sys; print('DIGEST_OK' if sys.version_info >= (3,10) else 'OLD')"
    if ($LASTEXITCODE -ne 0 -or $probe -notcontains 'DIGEST_OK') { throw 'This interpreter is not Python 3.10+.' }
    Save-PythonPath $manual
    return $manual
}
function Save-PythonPath($path) {
    $directory=Join-Path $PSScriptRoot 'private'
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    [IO.File]::WriteAllText((Join-Path $directory 'python-path.txt'),$path,[Text.UTF8Encoding]::new($false))
}
function Save-DigestConfig($cfg,$path) {
    [IO.File]::WriteAllText($path,($cfg | ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
}
function Ask-Default($label,$default) {
    $value = Read-Host "$label [$default]"
    if ([string]::IsNullOrWhiteSpace($value)) { return $default }
    return $value.Trim()
}
