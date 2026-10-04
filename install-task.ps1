param([Parameter(Mandatory=$true)][string]$PythonPath)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$pythonw = Join-Path (Split-Path $PythonPath) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw 'pythonw.exe is required for hidden background execution.' }
$bytes = [Text.Encoding]::UTF8.GetBytes($root)
$hash = [Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
$suffix = ([BitConverter]::ToString($hash)).Replace('-','').Substring(0,10)
$name = "PersonalNewsDigest-$suffix"
$action = New-ScheduledTaskAction -Execute $pythonw -Argument ('"' + (Join-Path $root 'digest.py') + '" tick') -WorkingDirectory $root
# Run every five minutes, aligned to a minute divisible by five.
$start = (Get-Date).Date.AddMinutes(([math]::Floor((Get-Date).TimeOfDay.TotalMinutes / 5) + 1) * 5)
$trigger = New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4)
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Collect official RSS every 5 minutes; deliver at configured Beijing-time slots.' -Force | Out-Null
$name | Set-Content -LiteralPath (Join-Path $root 'private\task-name.txt')
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State
Write-Host 'Installed. Keep this folder in place. Requires this Windows user to remain signed in; locking the screen is fine.'
