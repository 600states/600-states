# 600 STATES - hamta GDELT 2.0 Events for pilotdygnen
# Kors i PowerShell PA DIN MASKIN, utanfor Claude-sandladan (som blockerar gdeltproject.org).
#
#   powershell -ExecutionPolicy Bypass -File hamta_events.ps1
#
# Resultat: en zip per dygn, samma nastlade struktur som Mentions-arkiven,
# sa att pipelinens laddare kan lasa dem utan andring.

$ErrorActionPreference = "Stop"
$DataRoot = "%STATES_DATA%\01_RAW_GDELT_2026_001_010"
$Days = 1..10 | ForEach-Object { "202601{0:D2}" -f $_ }

if (-not (Test-Path $DataRoot)) { throw "Hittar inte datamappen: $DataRoot" }

foreach ($day in $Days) {
    $outZip = Join-Path $DataRoot "600_STATES_${day}_GDELT2_EVENTS.zip"
    if (Test-Path $outZip) { Write-Host "$day  hoppar over (finns redan)"; continue }

    $tmp = Join-Path $env:TEMP "gdelt_events_$day"
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    New-Item -ItemType Directory -Path $tmp | Out-Null

    $ok = 0; $fail = 0
    foreach ($h in 0..23) {
        foreach ($m in 0,15,30,45) {
            $stamp = "{0}{1:D2}{2:D2}00" -f $day, $h, $m
            $url   = "http://data.gdeltproject.org/gdeltv2/$stamp.export.CSV.zip"
            $dest  = Join-Path $tmp "$stamp.export.CSV.zip"
            try {
                Invoke-WebRequest -Uri $url -OutFile $dest -TimeoutSec 60 -UseBasicParsing
                $ok++
            } catch {
                $fail++
            }
        }
    }
    Write-Host ("{0}  hamtade {1}/96  (misslyckade {2})" -f $day, $ok, $fail)

    if ($ok -gt 0) {
        Compress-Archive -Path (Join-Path $tmp "*.zip") -DestinationPath $outZip -CompressionLevel Optimal
        Write-Host "        -> $outZip"
    }
    Remove-Item $tmp -Recurse -Force
}
Write-Host ""
Write-Host "Klart. Sag till i chatten sa fortsatter jag."
