$ErrorActionPreference = 'Stop'
Push-Location "$PSScriptRoot\..\backend"
try { python -m pytest -q } finally { Pop-Location }
Push-Location "$PSScriptRoot\..\frontend"
try { npm run build } finally { Pop-Location }
