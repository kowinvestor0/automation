Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\auto make money"
WshShell.Run """C:\Users\H\AppData\Local\Programs\Python\Python312\pythonw.exe"" ""D:\auto make money\core\background_worker.py""", 0, False
