Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
app = folder & "\app.py"
sh.CurrentDirectory = folder
sh.Run "pythonw.exe """ & app & """", 0, False
