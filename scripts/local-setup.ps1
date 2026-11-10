# Instala o Forja direto no Windows (sem Docker). Requer Python 3.9+, ffmpeg e Node 20+.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { throw "Python 3.9+ nao encontrado (py/python)." }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "ffmpeg nao encontrado no PATH." }
if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) { throw "ffprobe nao encontrado no PATH." }
if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Node.js/npm 20+ nao encontrados no PATH." }

& $py.Source -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[test]"

Push-Location remotion-template
try {
  npm install --no-audit --no-fund
  npx remotion browser ensure
} finally {
  Pop-Location
}

& .\.venv\Scripts\python.exe -m forja --json doctor
