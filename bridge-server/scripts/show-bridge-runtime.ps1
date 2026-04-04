$bridgePorts = @(8000)

Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $bridgePorts -contains $_.LocalPort } |
    Sort-Object LocalPort |
    ForEach-Object {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($_.OwningProcess)"
        [PSCustomObject]@{
            Port = $_.LocalPort
            PID = $_.OwningProcess
            Executable = $process.ExecutablePath
            CommandLine = $process.CommandLine
        }
    } | Format-List
