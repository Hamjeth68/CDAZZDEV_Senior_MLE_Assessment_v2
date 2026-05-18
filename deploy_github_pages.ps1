$ErrorActionPreference = 'Stop'

Write-Host 'Publishing client folder to GitHub Pages branch gh-pages...'

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error 'GitHub CLI (gh) is required. Install it from https://cli.github.com/'
    exit 1
}

$branch = 'gh-pages'
$publishDir = 'client'

if (-not (Test-Path $publishDir)) {
    Write-Error "Publish directory '$publishDir' not found. Run this script from the repository root."
    exit 1
}

# Create a temporary branch copy and push the client folder to gh-pages
$workDir = Join-Path $env:TEMP "gh-pages-deploy-$(Get-Random)"
New-Item -ItemType Directory -Path $workDir | Out-Null
Write-Host "Using temporary deployment directory: $workDir"

git worktree add -f -B $branch $workDir
Copy-Item -Path "$publishDir\*" -Destination $workDir -Recurse -Force
Set-Location $workDir
git add --all
if ((git diff --cached --quiet) -ne $true) {
    git commit -m 'Deploy updated client to GitHub Pages'
    git push origin $branch
} else {
    Write-Host 'No changes to deploy.'
}

Set-Location -Path (Split-Path -Path $PSScriptRoot -Parent)
git worktree remove -f $workDir
Write-Host 'Deployment complete.'
