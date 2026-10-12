$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$runtime = if ($env:NMS_COMPANION_RUNTIME) { $env:NMS_COMPANION_RUNTIME } else { Join-Path $root '.venv' }
$pythonExe = Join-Path $runtime 'Scripts\python.exe'
$tempRoot = Join-Path $runtime 'tmp'
New-Item -ItemType Directory -Force $tempRoot | Out-Null
$env:TEMP = $tempRoot
$env:TMP = $tempRoot
if (-not (Test-Path $pythonExe)) {
    New-Item -ItemType Directory -Force $runtime | Out-Null
    python -m venv $runtime
}
$needsInstall = $false
if (-not (Test-Path $pythonExe)) { $needsInstall = $true }
else {
    $sitePackages = Join-Path $runtime 'Lib\site-packages'
    foreach ($pattern in @('Flask-*.dist-info', 'faster*whisper-*.dist-info', 'keyring-*.dist-info', 'av-*.dist-info')) {
        if (-not (Get-ChildItem $sitePackages -Directory -Filter $pattern -ErrorAction SilentlyContinue | Select-Object -First 1)) { $needsInstall = $true }
    }
    $avInfo = Get-ChildItem $sitePackages -Directory -Filter 'av-*.dist-info' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($avInfo -and $avInfo.Name -match '^av-(\d+(?:\.\d+)*)\.dist-info$') {
        if ([version]$Matches[1] -ge [version]'19.0') { $needsInstall = $true }
    }
}
if ($needsInstall) {
    & $pythonExe -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare pip in the local Python environment.' }
    & $pythonExe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the internet connection and available disk space, then retry.' }
}
if ($env:NMS_COMPANION_RUNTIME -and -not $env:NMS_COMPANION_DATA) { $env:NMS_COMPANION_DATA = Join-Path $runtime 'userdata' }
Start-Sleep -Milliseconds 800
Start-Process 'http://127.0.0.1:8765'
& $pythonExe -m companion.app
