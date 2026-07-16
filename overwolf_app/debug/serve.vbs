Set oShell = CreateObject("WScript.Shell")
oShell.Run "cmd /c python -m http.server 8000", 0, False
WScript.Sleep 1500
oShell.Run """C:\Program Files\Google\Chrome\Application\chrome.exe"" --app=""http://localhost:8000/debug/desktop-debug.html"" --window-size=1000,950", 1, False
