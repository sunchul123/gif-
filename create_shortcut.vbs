Set sh = CreateObject("WScript.Shell")
desktop = sh.SpecialFolders("Desktop")
curDir = sh.CurrentDirectory

Set sc = sh.CreateShortcut(desktop & "\DesktopPet.lnk")
sc.TargetPath = curDir & "\run.bat"
sc.WorkingDirectory = curDir
sc.Description = "Desktop Pet - PySide6"
sc.IconLocation = curDir & "\pet\feibi\icon.ico, 0"
sc.Save

WScript.Echo "Shortcut created on Desktop!"
