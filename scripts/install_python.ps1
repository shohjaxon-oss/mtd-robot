$ErrorActionPreference = "Stop"
$installerUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$installerPath = Join-Path $env:TEMP "python-3.11.9-installer.exe"

Write-Host "Downloading Python 3.11.9 installer..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing

$targetDir = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311"
Write-Host "Target directory: $targetDir"
Write-Host "Starting silent installation..."

$installProcess = Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=0", "Include_pip=1", "PrependPath=1", "TargetDir=`"$targetDir`"" -Wait -PassThru

Write-Host "Process exit code: $($installProcess.ExitCode)"

$pythonExe = Join-Path $targetDir "python.exe"
if (Test-Path $pythonExe) {
    Write-Host "SUCCESS: Python 3.11 installed at $pythonExe"
    & $pythonExe --version
} else {
    Write-Host "FAILURE: python.exe not found at $pythonExe"
}
