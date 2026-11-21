# Draft voice-over with the Windows Russian voice, only to time a reel before Lucy records it.
# Usage: .\ads\audio\tts_placeholder.ps1 -Reel r03
param([Parameter(Mandatory = $true)][string]$Reel)

$ErrorActionPreference = "Stop"
$ads = Split-Path -Parent $PSScriptRoot
$python = Join-Path $ads ".venv\Scripts\python.exe"
# Without this Windows PowerShell reads the Cyrillic text in the console code page and the voice reads garbage.
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$text =& $python -c "import sys; sys.path.insert(0, r'$PSScriptRoot'); from script import vo_lines; print(' '.join(vo_lines('$Reel')))"

$outDir = Join-Path $ads "vo"
New-Item -ItemType Directory -Force $outDir | Out-Null
$out = Join-Path $outDir "$Reel-placeholder.wav"

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice("Microsoft Irina Desktop")
$synth.Rate = 3
$synth.SetOutputToWaveFile($out)
$synth.Speak($text)
$synth.Dispose()
Write-Output $out
