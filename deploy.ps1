# deploy.ps1 - Bulut Telegram botunu GitHub'a deploy eder (idempotent).
# On kosul: gh auth login (bir kere, PC tarayici). ASCII mesajlar (PS 5.1 BOM trap yok).
# Secret DEGERLERI ekrana yazilmaz; stdin ile gh secret set'e pipe edilir.
$ErrorActionPreference = 'Continue'
$env:PATH = 'C:\Program Files\GitHub CLI;' + $env:PATH
$root = $PSScriptRoot
$repo = if ($args[0]) { $args[0] } else { 'bil-telegram-bulut' }
$tgcfg = 'C:\Users\Viole\.config\opencode\telegram.json'

Write-Host '[1/6] gh auth kontrol...'
gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host 'ONCE gh auth login yap (PC tarayici, bir kere). Sonra tekrar calistir.'
  exit 1
}
$login = (gh api user --jq .login).Trim()
Write-Host "GitHub login: $login"

Write-Host '[2/6] repo olustur (public, sinirsiz dk)...'
gh repo view "$login/$repo" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  gh repo create $repo --public --description 'PC-independent Telegram assistant (Gemini free tier)' 2>&1 | Out-Null
  Write-Host "repo olusturuldu: $login/$repo"
} else {
  Write-Host 'repo zaten var.'
}

Write-Host '[3/6] git init + push...'
Push-Location $root
if (-not (Test-Path '.git')) { git init -b main 2>&1 | Out-Null }
git config user.name "BILDEK" 2>&1 | Out-Null
git config user.email "BILDEK@users.noreply.github.com" 2>&1 | Out-Null
git add -A 2>&1 | Out-Null
git commit -m 'bulut telegram bot' 2>&1 | Out-Null
git remote remove origin 2>&1 | Out-Null
git remote add origin "https://github.com/$login/$repo.git" 2>&1 | Out-Null
git push -u origin main 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host 'PUSH HATASI'; Pop-Location; exit 1 }
Pop-Location

Write-Host '[4/6] secret set (stdin, degerler gizli)...'
python -c "import json;print(json.load(open(r'$tgcfg',encoding='utf-8'))['token'])" | gh secret set TELEGRAM_TOKEN --repo "$login/$repo" 2>&1 | Out-Null
python -c "import json;print(json.load(open(r'$tgcfg',encoding='utf-8'))['chat_id'])" | gh secret set TELEGRAM_CHAT_ID --repo "$login/$repo" 2>&1 | Out-Null
[Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User') | gh secret set GEMINI_API_KEY --repo "$login/$repo" 2>&1 | Out-Null
gh secret list --repo "$login/$repo" 2>&1

Write-Host '[5/6] offset backlog otesine ayarla...'
Push-Location $root
python -c "import json,urllib.request; tok=json.load(open(r'$tgcfg',encoding='utf-8'))['token']; d=json.load(urllib.request.urlopen('https://api.telegram.org/bot%s/getUpdates?timeout=0'%tok,timeout=20)); ids=[u['update_id'] for u in d.get('result',[])]; off=(max(ids)+1) if ids else 0; json.dump({'offset':off},open('offset.json','w')); print('offset=',off)"
git add offset.json 2>&1 | Out-Null
git commit -m 'offset init' 2>&1 | Out-Null
git push 2>&1 | Out-Null
Pop-Location

Write-Host '[6/6] workflow tetikle (ilk test)...'
gh workflow run telegram.yml --repo "$login/$repo" 2>&1 | Out-Null
Write-Host "TAMAM. Repo: https://github.com/$login/$repo"
Write-Host 'Simdi PC koprusunde getUpdates kapat (cift yanit olmasin).'