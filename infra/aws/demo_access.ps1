<#
.SYNOPSIS
Demo access helper for the CareerFlowOps EC2 host. Uses AWS Systems Manager only: no SSH key and no extra open ports.

.DESCRIPTION
  status   Show the instance, its Elastic IP, Systems Manager state and the public HTTPS address.
  tokens   Print the host-generated candidate token, admin token and Grafana password to THIS console only.
  tunnels  Open Grafana (localhost:13000), Prometheus (localhost:19090) and MLflow (localhost:5000) in new windows.
           Requires the AWS Session Manager plugin and a free local port 5000 (MLflow only accepts that host name).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File infra\aws\demo_access.ps1 status
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)][ValidateSet('status', 'tokens', 'tunnels')][string]$Action,
    [string]$Profile = $(if ($env:AWS_PROFILE) { $env:AWS_PROFILE } else { 'careerflow' }),
    [string]$Region = 'ap-south-1'
)
$ErrorActionPreference = 'Stop'

function Invoke-Aws {
    $output = & aws @args --profile $Profile --region $Region
    if ($LASTEXITCODE -ne 0) { throw "aws $($args[0]) $($args[1]) failed" }
    return $output
}

function Get-InstanceId {
    $id = Invoke-Aws ec2 describe-instances --filters 'Name=tag:Name,Values=CareerFlowOps' 'Name=instance-state-name,Values=running' `
        --query 'Reservations[0].Instances[0].InstanceId' --output text
    if (-not $id -or $id -eq 'None') { throw 'No running instance tagged Name=CareerFlowOps. Start it first: aws ec2 start-instances --instance-ids <id>' }
    return $id
}

$instance = Get-InstanceId

switch ($Action) {
    'status' {
        $row = Invoke-Aws ec2 describe-instances --instance-ids $instance `
            --query 'Reservations[0].Instances[0].[InstanceType,State.Name,PublicIpAddress]' --output text
        $type, $state, $ip = $row -split "\s+"
        $ping = Invoke-Aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$instance" `
            --query 'InstanceInformationList[0].PingStatus' --output text
        "Instance : $instance ($type, $state)"
        "Systems Manager : $ping"
        "Public URL : https://$($ip -replace '\.', '-').sslip.io"
    }
    'tokens' {
        $remote = "grep -E '^(CANDIDATE_API_TOKEN|ADMIN_API_TOKEN|GRAFANA_ADMIN_PASSWORD)=' /home/ubuntu/CareerFlowOps/.env"
        $file = Join-Path $env:TEMP 'careerflowops-ssm-tokens.json'
        @{ commands = @($remote) } | ConvertTo-Json | Set-Content -Path $file -Encoding ascii
        try {
            $command = Invoke-Aws ssm send-command --instance-ids $instance --document-name AWS-RunShellScript `
                --parameters "file://$file" --query Command.CommandId --output text
        } finally { Remove-Item $file -ErrorAction SilentlyContinue }
        do {
            Start-Sleep -Seconds 2
            $status = Invoke-Aws ssm get-command-invocation --command-id $command --instance-id $instance --query Status --output text
        } while ($status -in 'Pending', 'InProgress', 'Delayed')
        if ($status -ne 'Success') { throw "Systems Manager command ended with status $status" }
        Invoke-Aws ssm get-command-invocation --command-id $command --instance-id $instance --query StandardOutputContent --output text
        Write-Warning 'Shown on this console only. Systems Manager keeps command output for 30 days; regenerate the host .env secrets or tear the host down after the assessment.'
    }
    'tunnels' {
        if (-not (Get-Command session-manager-plugin -ErrorAction SilentlyContinue)) {
            throw 'Install the Session Manager plugin first (winget install Amazon.SessionManagerPlugin), then reopen this terminal.'
        }
        $forwards = @(
            @{ Name = 'Grafana'; Remote = 3000; Local = 13000 },
            @{ Name = 'Prometheus'; Remote = 9090; Local = 19090 },
            @{ Name = 'MLflow'; Remote = 5000; Local = 5000 }
        )
        foreach ($forward in $forwards) {
            $parameters = Join-Path $env:TEMP "careerflowops-tunnel-$($forward.Name).json"
            $launcher = Join-Path $env:TEMP "careerflowops-tunnel-$($forward.Name).ps1"
            @{ portNumber = @("$($forward.Remote)"); localPortNumber = @("$($forward.Local)") } | ConvertTo-Json | Set-Content -Path $parameters -Encoding ascii
            "aws ssm start-session --profile $Profile --region $Region --target $instance --document-name AWS-StartPortForwardingSession --parameters file://$parameters" |
                Set-Content -Path $launcher -Encoding ascii
            Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $launcher
            "$($forward.Name): http://localhost:$($forward.Local)"
        }
        'Keep the three new windows open while presenting. Grafana user is admin; use the password from the tokens action.'
    }
}
