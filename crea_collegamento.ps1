$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Agent Ordinatore.lnk")

$PortableExe = Join-Path $PSScriptRoot "dist\Agent Ordinatore\Agent Ordinatore.exe"
if (Test-Path -LiteralPath $PortableExe) {
    $Shortcut.TargetPath = $PortableExe
    $Shortcut.WorkingDirectory = Split-Path -Parent $PortableExe
    $Shortcut.IconLocation = "$PortableExe,0"
} else {
    $Shortcut.TargetPath = "$PSScriptRoot\Agent Ordinatore.bat"
    $Shortcut.WorkingDirectory = $PSScriptRoot
    $Shortcut.IconLocation = "$PSScriptRoot\icon.ico,0"
}

$Shortcut.Description = "Agent Ordinatore - Organizza i tuoi file con AI"
$Shortcut.Save()
Write-Host "Collegamento creato sul Desktop!"
