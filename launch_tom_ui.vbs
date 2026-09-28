Set fileSystem = CreateObject("Scripting.FileSystemObject")
Set shellApp = CreateObject("WScript.Shell")

' Always launch relative to this file, not the directory of a shortcut or shell.
projectDir = fileSystem.GetParentFolderName(WScript.ScriptFullName)

' TOM's supported environment is .venv311. Keep venv as a legacy fallback.
pythonw = projectDir & "\.venv311\Scripts\pythonw.exe"
If Not fileSystem.FileExists(pythonw) Then
    pythonw = projectDir & "\venv\Scripts\pythonw.exe"
End If
If Not fileSystem.FileExists(pythonw) Then
    pythonw = "pythonw.exe"
End If

appScript = projectDir & "\tom_desktop_app.py"
commandLine = Chr(34) & pythonw & Chr(34) & " " & Chr(34) & appScript & Chr(34)

' Run TOM without a console window.
shellApp.Run commandLine, 0, False
