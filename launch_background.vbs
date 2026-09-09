Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\auto make money"
WshShell.Run "C:\Users\H\AppData\Local\Programs\Python\Python312\python.exe core\launch_daemon.py", 0, False
