# Build cadler's usd-brep wheel for Windows (x64): this checkout, built and packed by NVIDIA's own
# tooling (prebuild, repo build, repo py_package), then given the version in cadler\version.
#
#   powershell -ExecutionPolicy Bypass -File cadler\build-windows.ps1 [-Out <dir>]
#
# The wheel goes to dist\ by default; its path is the last line printed.
# Needs Visual Studio 2019, or 2022 with the "MSVC v142 - VS 2019 C++ x64/x86 build tools"
# component: usd-brep pins msbuild.vs_version to vs2019. The script checks that before it starts.
# OpenUSD and Python come from NVIDIA's Packman.
param([string]$Out = "")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Version = (Get-Content (Join-Path $Root "cadler\version") -Raw).Trim()
if (-not $Out) { $Out = Join-Path $Root "dist" }
$Out = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Out)
$Log = Join-Path $Root "_build\cadler-build.log"

$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw "Visual Studio is missing: install VS 2022 (or its Build Tools) with 'Desktop development with C++' and the 'MSVC v142 - VS 2019 C++ x64/x86 build tools' component" }
$vs2019 = & $vswhere -products * -version "[16.0,17.0)" -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
# VS 2022 names the v142 toolset by its version (14.29), older installers by v142
$v142 = foreach ($id in "Microsoft.VisualStudio.Component.VC.14.29.16.11.x86.x64", "Microsoft.VisualStudio.Component.VC.v142.x86.x64") {
    & $vswhere -products * -version "[17.0,18.0)" -requires $id -property installationPath
}
if (-not ($vs2019 -or $v142)) {
    throw "no MSVC v142 toolset found: in the Visual Studio Installer, Modify -> Individual components -> 'MSVC v142 - VS 2019 C++ x64/x86 build tools' (VS 2022), or install VS 2019 with 'Desktop development with C++'"
}

Write-Host "==> building usd-brep $Version for Windows x64"
# repo.toml pins vs2019. Without VS 2019, VS 2022 builds with its v142 toolset (repo_build's
# msvc_version), the same compiler and ABI; repo.toml is changed for this build only.
$RepoToml = Join-Path $Root "repo.toml"
$RepoTomlText = Get-Content $RepoToml -Raw
if (-not $vs2019) {
    Write-Host "    VS 2022 with the MSVC v142 toolset"
    $text = $RepoTomlText -replace 'msbuild\.vs_version = "vs2019"', "msbuild.vs_version = `"vs2022`"`nmsbuild.msvc_version = `"v142`""
    if ($text -eq $RepoTomlText) { throw "repo.toml has no msbuild.vs_version = `"vs2019`" to change" }
    [IO.File]::WriteAllText($RepoToml, $text)
}
New-Item -ItemType Directory -Force -Path $Out, (Join-Path $Root "_build") | Out-Null
Remove-Item -Recurse -Force (Join-Path $Root "_build\py_package") -ErrorAction SilentlyContinue
Remove-Item -Force $Log -ErrorAction SilentlyContinue
Push-Location $Root
try {
    # through cmd: Windows PowerShell turns a redirected stderr line into an error under "Stop"
    foreach ($step in ".\prebuild.bat", ".\repo.bat build -r", ".\repo.bat py_package -c release") {
        cmd /c "$step >> `"$Log`" 2>&1"
        if ($LASTEXITCODE -ne 0) {
            Get-Content $Log -Tail 60
            throw "usd-brep build failed at '$step', see _build\cadler-build.log"
        }
    }
} finally {
    Pop-Location
    [IO.File]::WriteAllText($RepoToml, $RepoTomlText)
}

$built = Get-ChildItem (Join-Path $Root "_build\py_package\wheels\usd_brep-*-win_amd64.whl") | Select-Object -First 1
$python = Join-Path $Root "_build\target-deps\python\python.exe"
$wheel = (& $python (Join-Path $Root "cadler\wheel-version.py") $built.FullName $Version | Select-Object -Last 1)
if ($LASTEXITCODE -ne 0) { throw "wheel-version.py failed" }
$dest = Join-Path $Out (Split-Path -Leaf $wheel)
Move-Item -Force $wheel $dest
Write-Host ("    {0:N0} MB" -f ((Get-Item $dest).Length / 1MB))
Write-Output $dest
