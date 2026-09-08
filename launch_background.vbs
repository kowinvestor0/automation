Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\auto make money"
WshShell.Run "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command ""Start-Process python.exe -ArgumentList 'core\background_worker.py' -WorkingDirectory 'D:\auto make money'""", 0, False
