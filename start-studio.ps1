param([int]$Port = 8080, [string]$BindAddress = '127.0.0.1')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$studioPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $studioPython)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $studioPython = $pythonCommand.Source }
    elseif (Test-Path -LiteralPath 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe') {
        $studioPython = 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe'
    } else { throw 'Python 3.11 oder neuer installieren oder eine .venv anlegen (siehe WEBSTUDIO.md).' }
}
Write-Host "Lightshow Studio: http://localhost:$Port  (Beenden mit Strg+C)"
& $studioPython run_studio.py --host $BindAddress --port $Port
if ($LASTEXITCODE -ne 0) { throw 'Start fehlgeschlagen. Abhaengigkeiten gemaess WEBSTUDIO.md installieren.' }
