param([switch]$Desktop)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ($Desktop) { python launch.py --desktop } else { python launch.py }
