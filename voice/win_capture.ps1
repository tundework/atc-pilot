# Run this in a Windows PowerShell window (NOT inside WSL) — WSLg mic passthrough
# doesn't work on this machine, so recording has to happen on the Windows side.
#
# Requires ffmpeg. If you don't have it: winget install ffmpeg
#
# Usage:
#   .\win_capture.ps1
#
# One 8-second capture per invocation, saved with a timestamped filename so
# it can never collide with a previous recording (live.py's watcher tracks
# files by path — a reused name like "sample_1.wav" would silently mask a
# fresh recording as an already-seen one). Run it again for the next
# transmission.

$outDir = "C:\atc_voice_samples"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $outDir "tx_$stamp.wav"

Write-Host "Recording starts in..."
Write-Host "3..."; Start-Sleep -Seconds 1
Write-Host "2..."; Start-Sleep -Seconds 1
Write-Host "1..."; Start-Sleep -Seconds 1
Write-Host "GO" -ForegroundColor Green

ffmpeg -y -f dshow -i audio="Microphone (USB Audio Device)" -t 8 -ar 16000 -ac 1 $out 2>$null

Write-Host "Saved $out"
Write-Host "From WSL: /mnt/c/atc_voice_samples/tx_$stamp.wav" -ForegroundColor Cyan
