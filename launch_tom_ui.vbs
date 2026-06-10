Set fso = CreateObject("Scripting.FileSystemObject")
Set wsh = CreateObject("WScript.Shell")

' Determine current directory (where this VBS lives)
cwd = wsh.CurrentDirectory

venvPythonw = cwd & "\venv\Scripts\pythonw.exe"
If fso.FileExists(venvPythonw) Then
    pythonw = venvPythonw
Else
    pythonw = "pythonw"
End If

script = cwd & "\tom_desktop_app.py"

' Build a safe command line quoting paths using Chr(34) for '"'
cmd = Chr(34) & pythonw & Chr(34) & " " & Chr(34) & script & Chr(34)

' Run without showing a console window (window style 0)
wsh.Run cmd, 0, False
