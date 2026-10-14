# Rebuild the repository's final Task 8 state. Run from any PowerShell terminal.
# Requires Docker Desktop (Linux containers), kind, kubectl and the local source tree.
param(
    [switch]$CreateCluster,
    [switch]$BuildImages
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$labContext = 'kind-cte412-02230135'
$labNamespace = 'nb-02230135'
function Invoke-LabCommand {
    param([string]$Program, [string[]]$Arguments)
    Write-Output ('> ' + $Program + ' ' + ($Arguments -join ' '))
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Program"
    }
}
if ($CreateCluster) {
    Invoke-LabCommand 'kind' @('create','cluster','--name','cte412-02230135','--config','cluster/kind-cluster.yaml')
}
Invoke-LabCommand 'kubectl' @('--context',$labContext,'apply','-f','manifests/base/00-namespace.yaml')
Invoke-LabCommand 'kubectl' @('--context',$labContext,'apply','-f','manifests/base/01-resourcequota.yaml')
Invoke-LabCommand 'kubectl' @('--context',$labContext,'apply','-f','manifests/base/02-limitrange.yaml')
Invoke-LabCommand 'kubectl' @('config','set-context',$labContext,"--namespace=$labNamespace")
if ($BuildImages) {
    foreach ($labVersion in @('1.0.0','1.1.0','1.2.0-broken')) {
        Invoke-LabCommand 'docker' @('build','--build-arg',"APP_VERSION=$labVersion",'--build-arg','STUDENT_ID=02230135','-t',"notice-board:02230135-$labVersion",'./app')
    }
}
Invoke-LabCommand 'kind' @('load','docker-image','notice-board:02230135-1.0.0','notice-board:02230135-1.1.0','notice-board:02230135-1.2.0-broken','--name','cte412-02230135')
foreach ($labManifest in @(
    'manifests/bluegreen/04-feature-flags.yaml',
    'manifests/bluegreen/00-blue-deployment.yaml',
    'manifests/bluegreen/01-green-deployment.yaml',
    'manifests/bluegreen/02-production-services.yaml',
    'manifests/bluegreen/03-preview-service.yaml'
)) {
    Invoke-LabCommand 'kubectl' @('--context',$labContext,'apply','-f',$labManifest)
}
foreach ($labDeployment in @('notice-board-blue','notice-board-green')) {
    Invoke-LabCommand 'kubectl' @('--context',$labContext,'-n',$labNamespace,'rollout','status',"deployment/$labDeployment",'--timeout=240s')
}
Invoke-LabCommand 'kubectl' @('--context',$labContext,'apply','-f','manifests/base/03-monitor-code.yaml')
Invoke-LabCommand 'kubectl' @('--context',$labContext,'apply','-f','manifests/base/04-monitor-pod.yaml')
Invoke-LabCommand 'kubectl' @('--context',$labContext,'-n',$labNamespace,'wait','--for=condition=Ready','pod/monitor','--timeout=120s')
Invoke-LabCommand 'kubectl' @('--context',$labContext,'-n',$labNamespace,'get','deployments,pods,services')
$labVersionReply = Invoke-RestMethod -Uri 'http://127.0.0.1:30090/version'
$labNoticeReply = Invoke-RestMethod -Uri 'http://127.0.0.1:30090/notices'
$labVersionReply | ConvertTo-Json -Depth 6
$labNoticeReply | ConvertTo-Json -Depth 6
if ($labVersionReply.student -ne '02230135' -or $labVersionReply.version -ne '1.1.0') {
    throw 'Production version or student identity is incorrect.'
}
if ($labNoticeReply.pinnedFirst -ne $true -or $labNoticeReply.notices[0].id -ne 2) {
    throw 'The final pinned-first feature flag did not take effect.'
}
Write-Output 'Student 02230135: final Task 8 state verified successfully.'
