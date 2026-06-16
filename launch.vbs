' NEXUS AI – Silent launcher (no CMD window flash)
' Double-click this from File Manager to start the app.

Dim WshShell, ScriptDir, PythonExe, AppPy, LogFile, Cmd

Set WshShell = CreateObject("WScript.Shell")

' Get the folder where THIS .vbs file lives
ScriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' Remove trailing backslash
If Right(ScriptDir, 1) = "\" Then ScriptDir = Left(ScriptDir, Len(ScriptDir) - 1)

PythonExe = ScriptDir & "\.venv\Scripts\pythonw.exe"
AppPy     = ScriptDir & "\app.py"
LogFile   = ScriptDir & "\run.log"

' Check python exists
Dim FSO
Set FSO = CreateObject("Scripting.FileSystemObject")
If Not FSO.FileExists(PythonExe) Then
    MsgBox "Virtual environment not found!" & Chr(13) & Chr(10) & _
           "Expected: " & PythonExe & Chr(13) & Chr(10) & Chr(13) & Chr(10) & _
           "Please run setup first:" & Chr(13) & Chr(10) & _
           "  python -m venv .venv" & Chr(13) & Chr(10) & _
           "  .venv\Scripts\pip install -r requirements.txt", _
           48, "NEXUS AI - Setup Required"
    WScript.Quit 1
End If

' Set environment variables via WshShell
WshShell.Environment("Process")("KMP_DUPLICATE_LIB_OK")       = "TRUE"
WshShell.Environment("Process")("OPENCV_VIDEOIO_DEBUG")        = "0"
WshShell.Environment("Process")("OPENCV_VIDEOIO_PRIORITY_MSMF") = "0"
WshShell.Environment("Process")("PYTHONPATH")                  = ScriptDir
WshShell.Environment("Process")("PYTHONUNBUFFERED")            = "1"

' Change working directory
WshShell.CurrentDirectory = ScriptDir

' Launch pythonw (no console window) — append stderr to run.log
' Mode 0 = hidden window, False = don't wait
Cmd = Chr(34) & PythonExe & Chr(34) & " " & Chr(34) & AppPy & Chr(34)
WshShell.Run Cmd, 0, False

Set WshShell = Nothing
Set FSO      = Nothing
