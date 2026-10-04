$ErrorActionPreference = 'Stop'
try {
    Set-Location -LiteralPath $PSScriptRoot
    . (Join-Path $PSScriptRoot 'runtime.ps1')
    $python = Find-DigestPython
    Write-Host "Using Python: $python"
    $configPath = Join-Path $PSScriptRoot 'config.json'
    $template = if (Test-Path -LiteralPath $configPath) { $configPath } else { Join-Path $PSScriptRoot 'config.example.json' }
    $cfg = Get-Content -LiteralPath $template -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($field in @('smtp_proxy','rss_proxy')) { if (-not $cfg.PSObject.Properties[$field]) { $cfg | Add-Member -NotePropertyName $field -NotePropertyValue $null } }
    $cfg.recipient = Ask-Default 'Recipient email' $cfg.recipient
    $cfg.sender = Ask-Default 'Sender email' $cfg.sender
    foreach ($address in @($cfg.recipient,$cfg.sender)) {
        if ([string]::IsNullOrWhiteSpace($address) -or $address -match '[\r\n]' -or $address -cmatch '[^\x00-\x7F]') { throw 'Enter one ASCII email address per field.' }
        $parsed = [Net.Mail.MailAddress]::new($address)
        if ($parsed.Address -cne $address) { throw 'Use a plain email address, without a display name.' }
    }
    $cfg.language = Ask-Default 'Email language: en / zh-Hans / zh-Hant' $cfg.language
    if ($cfg.language -notin @('en','zh-Hans','zh-Hant')) { throw 'Choose en, zh-Hans, or zh-Hant.' }
    Write-Host 'Source sections (some may be unavailable):'
    $cfg.sources | ForEach-Object { Write-Host ('  ' + $_.name) }
    $currentSections = if ($cfg.sections.Count) { $cfg.sections -join ',' } else { 'ALL' }
    $choice = Ask-Default 'Sections: ALL or exact names separated by commas' $currentSections
    $cfg.sections = if ($choice -eq 'ALL') { @() } else { @($choice.Split(',') | ForEach-Object { $_.Trim() } | Select-Object -Unique) }
    foreach ($section in $cfg.sections) { if ($section -cnotin @($cfg.sources.name)) { throw "Unknown section: $section" } }
    $cfg.smtp_host = Ask-Default 'SMTP SSL host (Gmail: smtp.gmail.com)' $cfg.smtp_host
    $cfg.smtp_port = [int](Ask-Default 'SMTP SSL port (465; STARTTLS 587 is not supported)' $cfg.smtp_port)
    if ($cfg.smtp_port -lt 1 -or $cfg.smtp_port -gt 65535 -or $cfg.smtp_port -eq 587) { throw 'Use an implicit TLS/SSL port, usually 465.' }
    $defaultProxy = if ($cfg.smtp_proxy) { "$($cfg.smtp_proxy.host):$($cfg.smtp_proxy.port)" } else { 'DIRECT' }
    $proxy = Ask-Default 'Proxy: DIRECT or HTTP mixed proxy host:port (FlClash often 127.0.0.1:7890; verify your port)' $defaultProxy
    if ($proxy -eq 'DIRECT') { $cfg.smtp_proxy=$null; $cfg.rss_proxy=$null }
    else {
        if ($proxy -notmatch '^([a-zA-Z0-9.-]+):(\d{1,5})$') { throw 'Use host:port for an unauthenticated HTTP CONNECT proxy.' }
        $proxyHost=$Matches[1];$proxyPort=[int]$Matches[2]
        if ($proxyPort -lt 1 -or $proxyPort -gt 65535) { throw 'Invalid proxy port.' }
        $cfg.smtp_proxy=@{host=$proxyHost;port=$proxyPort}
        $cfg.rss_proxy="http://${proxyHost}:$proxyPort"
    }
    $cfg.times=@((Ask-Default 'Send times in Beijing time (UTC+8)' ($cfg.times -join ',')).Split(',') | ForEach-Object { $_.Trim() } | Select-Object -Unique)
    foreach ($time in $cfg.times) { if ($time -notmatch '^([01][0-9]|2[0-3]):[0-5][0-9]$') { throw 'Use HH:mm, separated by commas.' } }
    # Require explicit reactivation after editing an existing installation.
    $cfg.enabled=$false
    New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot 'private') | Out-Null
    Save-DigestConfig $cfg $configPath
    Write-Host 'Checking network before asking for credentials...'
    & $python (Join-Path $PSScriptRoot 'digest.py') check
    if ($LASTEXITCODE -ne 0) { throw 'Connection check failed. Fix the network/proxy and run setup again. No credentials requested.' }
    do {
        Write-Host "App password must belong to: $($cfg.sender)"
        $secret = Read-Host 'SMTP app password (hidden; NOT your normal login password)' -AsSecureString
        $temporaryCredential = [PSCredential]::new($cfg.sender,$secret)
        $plain = $temporaryCredential.GetNetworkCredential().Password
        if ($cfg.smtp_host -ieq 'smtp.gmail.com') {
            $plain = $plain -replace '\s',''
            $valid = $plain -cmatch '^[a-zA-Z]{16}$'
            if (-not $valid) { Write-Host "Gmail expects 16 letters; received $($plain.Length) characters after removing spaces. Please re-enter." }
        } else { $valid = $plain.Length -gt 0 }
    } until ($valid)
    $normalized = ConvertTo-SecureString $plain -AsPlainText -Force
    $cred = [PSCredential]::new($cfg.sender,$normalized)
    $cred | Export-Clixml -LiteralPath (Join-Path $PSScriptRoot 'private\smtp.xml')
    $plain=$null;$temporaryCredential=$null;$cred=$null;$secret=$null;$normalized=$null
    & (Join-Path $PSScriptRoot 'activate.ps1') -PythonPath $python
} catch { Write-Host ('SETUP STOPPED: ' + $_.Exception.Message); exit 1 }
