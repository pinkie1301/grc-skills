[CmdletBinding()]
param(
    [string]$RepositoryRoot,
    [string]$SkillSource,
    [string[]]$Targets = @("codex"),
    [string]$RadiocondaPath,
    [switch]$PersistEnv,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

function ConvertTo-PortablePath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return $Path.Replace('\', '/')
}

function Get-UserHome {
    if ($env:USERPROFILE) {
        return $env:USERPROFILE
    }
    return $HOME
}

function Get-SkillTargetPath {
    param([Parameter(Mandatory = $true)][string]$Target)

    $UserHome = Get-UserHome
    switch ($Target) {
        "codex" {
            return Join-Path $UserHome ".codex/skills/grc-block-query"
        }
        "copilot" {
            return Join-Path $UserHome ".copilot/skills/grc-block-query"
        }
        "claude-code" {
            return Join-Path $UserHome ".claude/skills/grc-block-query"
        }
    }
}

if (-not $RepositoryRoot) {
    $RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../../.."))
}

if (-not $SkillSource) {
    $SkillSource = Join-Path $RepositoryRoot "skills/grc-block-query"
}

if (-not (Test-Path -LiteralPath $SkillSource)) {
    throw "Skill source not found: $SkillSource"
}

$AllowedTargets = @("codex", "copilot", "claude-code")
$NormalizedTargets = foreach ($Target in $Targets) {
    $Target -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ }
}
$InvalidTargets = @($NormalizedTargets | Where-Object { $_ -notin $AllowedTargets })
if ($InvalidTargets.Count -gt 0) {
    throw "Invalid target(s): $($InvalidTargets -join ', '). Allowed targets: $($AllowedTargets -join ', ')"
}
$Targets = @($NormalizedTargets | Select-Object -Unique)
if ($Targets.Count -eq 0) {
    throw "At least one install target is required."
}

$SkillSourceFull = [System.IO.Path]::GetFullPath($SkillSource)
$ResolvedTargets = foreach ($Target in $Targets) {
    [pscustomobject]@{
        Name = $Target
        Path = [System.IO.Path]::GetFullPath((Get-SkillTargetPath -Target $Target))
    }
}

Write-Host "Skill source: $(ConvertTo-PortablePath $SkillSourceFull)" -ForegroundColor Cyan
Write-Host "Install targets:" -ForegroundColor Cyan
foreach ($ResolvedTarget in $ResolvedTargets) {
    Write-Host "  - $($ResolvedTarget.Name): $(ConvertTo-PortablePath $ResolvedTarget.Path)"
}

if ($RadiocondaPath) {
    $RadiocondaFull = [System.IO.Path]::GetFullPath($RadiocondaPath)
    Write-Host "GRC_RADIOCONDA_PATH: $(ConvertTo-PortablePath $RadiocondaFull)" -ForegroundColor Cyan
}

if ($WhatIf) {
    Write-Host "WhatIf: no files or environment variables were changed." -ForegroundColor Yellow
    exit 0
}

foreach ($ResolvedTarget in $ResolvedTargets) {
    New-Item -ItemType Directory -Path $ResolvedTarget.Path -Force | Out-Null
    Copy-Item -Path (Join-Path $SkillSourceFull "*") -Destination $ResolvedTarget.Path -Recurse -Force

    $pycache = Join-Path $ResolvedTarget.Path "scripts/__pycache__"
    if (Test-Path -LiteralPath $pycache) {
        Remove-Item -LiteralPath $pycache -Recurse -Force
    }
}

if ($RadiocondaPath) {
    $env:GRC_RADIOCONDA_PATH = $RadiocondaFull

    if ($PersistEnv) {
        setx GRC_RADIOCONDA_PATH $RadiocondaFull | Out-Null
        Write-Host "Persisted GRC_RADIOCONDA_PATH for future sessions." -ForegroundColor Green
    } else {
        Write-Host "Set GRC_RADIOCONDA_PATH for this PowerShell session only." -ForegroundColor Green
    }
}

Write-Host "Done." -ForegroundColor Green
