Add-Type -AssemblyName System.Windows.Forms
$procs = Get-Process | Where-Object { $_.MainWindowTitle -like '*Sleep Enforcer*' } |
    Select-Object Id, ProcessName, MainWindowTitle
$procs | Format-List
