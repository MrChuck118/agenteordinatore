$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Agent Ordinatore.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\Agent Ordinatore.bat"
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.IconLocation = "$PSScriptRoot\icon.ico,0"
$Shortcut.Description = "Agent Ordinatore - Organizza i tuoi file con AI"
$Shortcut.Save()
Write-Host "Collegamento creato sul Desktop!"
