# Atalhos do kit para Windows (PowerShell). Requer Docker Desktop (WSL2) em execucao.
param([Parameter(Position=0)][string]$Cmd = "", [Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function C { docker compose @args; if ($LASTEXITCODE -ne 0) { throw "docker compose falhou ($LASTEXITCODE)" } }
function Rand { -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 24 | ForEach-Object {[char]$_}) }
if ($Cmd -and $Cmd -ne "setup" -and -not (Test-Path .env)) { & $PSCommandPath setup | Out-Null; Write-Host ".env criado automaticamente (a chave de API e opcional; o padrao e o provider files)" }
switch ($Cmd) {
  "setup" {
    if (-not (Test-Path .env)) { Copy-Item .env.example .env }
    $t = Get-Content .env -Raw
    if ($t -notmatch '(?m)^BROWSER_PASSWORD=.+') { $t = $t -replace '(?m)^BROWSER_PASSWORD=.*', "BROWSER_PASSWORD=$(Rand)"; Set-Content .env $t -NoNewline; Write-Host "senha do navegador gerada em .env" }
    New-Item -ItemType Directory -Force projects, models | Out-Null
    Write-Host "pronto. As vozes sao geradas por voce (provider files, em voices/). GEMINI_API_KEY e opcional, so para o provider gemini via API." }
  "doctor" {
    docker --version; docker compose version
    "arquitetura do daemon: " + (docker info --format '{{.OSType}}/{{.Architecture}}')
    if ((Test-Path .env) -and ((Get-Content .env -Raw) -match '(?m)^GEMINI_API_KEY=.+')) { "GEMINI_API_KEY: definida (opcional)" } else { "GEMINI_API_KEY: ausente (opcional; o padrao e o provider files)" } }
  "build" { C build forja }
  "new" {
    if ($Rest.Count -lt 2) { throw "uso: .\kit.ps1 new <nome> <video> [opcoes do init]" }
    if ($Rest[0] -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$' -or $Rest[0] -match '\.\.') { throw "nome do projeto invalido (use letras, numeros, ponto, hifen ou sublinhado; sem / nem ..)" }
    New-Item -ItemType Directory -Force projects | Out-Null
    Copy-Item -LiteralPath $Rest[1] "projects/.entrada-$($Rest[0]).mp4"
    $extra = @(); if ($Rest.Count -gt 2) { $extra = $Rest[2..($Rest.Count - 1)] }
    C run --rm forja init "/projects/$($Rest[0])" --source "/projects/.entrada-$($Rest[0]).mp4" @extra
    Remove-Item -LiteralPath "projects/.entrada-$($Rest[0]).mp4" -Force -ErrorAction SilentlyContinue }
  "run" { C run --rm forja @Rest }
  "shell" { C run --rm --entrypoint bash forja }
  "browser-up" { C --profile browser up -d browser cdp-proxy; "tela: https://localhost:3001 (aceite o certificado) | CDP: http://127.0.0.1:9222" }
  "browser-down" { C --profile browser stop browser cdp-proxy }
  "browser-reset" { C --profile browser down -v }
  default { "uso: .\kit.ps1 setup | doctor | build | new <nome> <video> | run <args> | shell | browser-up | browser-down | browser-reset" }
}
