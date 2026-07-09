# Run this in a Windows PowerShell window (NOT inside WSL) — WSLg mic passthrough
# doesn't work on this machine, so recording has to happen on the Windows side.
#
# Requires ffmpeg. If you don't have it: winget install ffmpeg
#
# Usage:
#   .\win_capture.ps1
#
# Records 5 clips, 7 seconds each, with a 3-2-1 countdown between them.
# Saves to C:\atc_voice_samples\sample_1.wav .. sample_5.wav (16kHz mono,
# what faster-whisper wants). That folder is visible from WSL at
# /mnt/c/atc_voice_samples/.

$outDir = "C:\atc_voice_samples"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$prompts = @(
    "Cessna one seven two alpha bravo, cleared for takeoff runway two seven",
    "Cessna one seven two alpha bravo, turn left heading two seven zero",
    "Cessna one seven two alpha bravo, climb and maintain three thousand",
    "Cessna one seven two alpha bravo, contact tower one one eight decimal three",
    "Cessna one seven two alpha bravo, go around"
)

for ($i = 0; $i -lt 5; $i++) {
    $n = $i + 1
    Write-Host ""
    Write-Host "=== Sample $n/5 ===" -ForegroundColor Cyan
    Write-Host "Say (in your own words is fine, just cover the content):"
    Write-Host "  `"$($prompts[$i])`"" -ForegroundColor Yellow
    Write-Host "Recording starts in..."
    Write-Host "3..."; Start-Sleep -Seconds 1
    Write-Host "2..."; Start-Sleep -Seconds 1
    Write-Host "1..."; Start-Sleep -Seconds 1
    Write-Host "GO" -ForegroundColor Green

    $out = Join-Path $outDir "sample_$n.wav"
    ffmpeg -y -f dshow -i audio="Microphone (USB Audio Device)" -t 7 -ar 16000 -ac 1 $out 2>$null

    Write-Host "Saved $out"
}

Write-Host ""
Write-Host "Done. From WSL, these are at /mnt/c/atc_voice_samples/" -ForegroundColor Cyan
