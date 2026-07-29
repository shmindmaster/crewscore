param(
    [string]$ScriptPath = (Join-Path $PSScriptRoot '..\..\demo\release-demo\release-demo-script.json'),
    [string]$OutDir = (Join-Path $PSScriptRoot '..\..\_production\demo-work\narration\release-demo'),
    [string]$VoiceName = 'Microsoft Zira Desktop'
)

$ErrorActionPreference = 'Stop'

function Invoke-Native {
    param([string]$Command, [string[]]$Arguments)
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Command failed with exit code $LASTEXITCODE" }
}

function Get-AudioDuration {
    param([string]$Path)
    $value = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $Path
    if ($LASTEXITCODE -ne 0) { throw "ffprobe failed for $Path" }
    return [Math]::Round([double]::Parse($value.Trim(), [Globalization.CultureInfo]::InvariantCulture), 3)
}

Add-Type -AssemblyName System.Speech
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw 'ffmpeg and ffprobe must be on PATH for narration packaging.'
}

$script = Get-Content -LiteralPath $ScriptPath -Raw | ConvertFrom-Json
$enabledVoices = (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | Where-Object Enabled | ForEach-Object { $_.VoiceInfo.Name }
if ($enabledVoices -notcontains $VoiceName) {
    throw "Required local voice '$VoiceName' is not installed. Available voices: $($enabledVoices -join ', ')"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$segmentDir = Join-Path $OutDir 'segments'
New-Item -ItemType Directory -Force -Path $segmentDir | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($VoiceName)
$synth.Rate = -1
$timing = @()
$concatEntries = New-Object System.Collections.Generic.List[string]
$cursor = 0.0

try {
    foreach ($segment in $script.segments) {
        $segmentPath = Join-Path $segmentDir "$($segment.id).wav"
        $synth.SetOutputToWaveFile($segmentPath)
        $synth.Speak([string]$segment.text)
        $synth.SetOutputToNull()
        $duration = Get-AudioDuration $segmentPath
        $gap = [double]$segment.gapAfterSeconds
        $timing += [ordered]@{
            id = [string]$segment.id
            text = [string]$segment.text
            startSeconds = [Math]::Round($cursor, 3)
            endSeconds = [Math]::Round($cursor + $duration, 3)
            durationSeconds = $duration
            gapAfterSeconds = $gap
            path = $segmentPath
        }
        $cursor += $duration
        $concatEntries.Add("file '$($segmentPath.Replace('\', '/').Replace("'", "'\\''"))'")
        if ($gap -gt 0) {
            $silencePath = Join-Path $segmentDir ("silence-{0}.wav" -f $segment.id)
            Invoke-Native ffmpeg @('-y', '-f', 'lavfi', '-i', 'anullsrc=r=22050:cl=mono', '-t', $gap.ToString([Globalization.CultureInfo]::InvariantCulture), '-c:a', 'pcm_s16le', $silencePath)
            $concatEntries.Add("file '$($silencePath.Replace('\', '/').Replace("'", "'\\''"))'")
            $cursor += $gap
        }
    }
}
finally {
    $synth.Dispose()
}

$concatPath = Join-Path $OutDir 'concat.txt'
[IO.File]::WriteAllLines($concatPath, $concatEntries, [Text.UTF8Encoding]::new($false))
$narrationPath = Join-Path $OutDir 'narration.wav'
Invoke-Native ffmpeg @('-y', '-f', 'concat', '-safe', '0', '-i', $concatPath, '-c:a', 'pcm_s16le', $narrationPath)

$srtLines = New-Object System.Collections.Generic.List[string]
$vttLines = New-Object System.Collections.Generic.List[string]
$vttLines.Add('WEBVTT')
$vttLines.Add('')
function Format-SubtitleTime([double]$Seconds, [bool]$Vtt) {
    $span = [TimeSpan]::FromSeconds($Seconds)
    $separator = if ($Vtt) { '.' } else { ',' }
    return ('{0:00}:{1:00}:{2:00}{3}{4:000}' -f [int][Math]::Floor($span.TotalHours), $span.Minutes, $span.Seconds, $separator, $span.Milliseconds)
}
for ($index = 0; $index -lt $timing.Count; $index++) {
    $entry = $timing[$index]
    $srtLines.Add([string]($index + 1))
    $srtLines.Add("$(Format-SubtitleTime $entry.startSeconds $false) --> $(Format-SubtitleTime $entry.endSeconds $false)")
    $srtLines.Add($entry.text)
    $srtLines.Add('')
    $vttLines.Add("$(Format-SubtitleTime $entry.startSeconds $true) --> $(Format-SubtitleTime $entry.endSeconds $true)")
    $vttLines.Add($entry.text)
    $vttLines.Add('')
}
[IO.File]::WriteAllLines((Join-Path $OutDir 'captions.srt'), $srtLines, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllLines((Join-Path $OutDir 'captions.vtt'), $vttLines, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $OutDir 'transcript.txt'), (($timing | ForEach-Object { $_.text }) -join [Environment]::NewLine) + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))

$timingDocument = [ordered]@{
    version = 1
    voice = [ordered]@{
        provider = 'Windows System.Speech'
        voice = $VoiceName
        rate = -1
        network = 'none'
        disclosure = 'Synthetic local narration generated with a Windows system voice.'
    }
    totalDurationSeconds = [Math]::Round($cursor, 3)
    segments = $timing
    narrationPath = $narrationPath
}
$timingDocument | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutDir 'narration-timing.json') -Encoding utf8

[pscustomobject]@{
    narration = $narrationPath
    timing = Join-Path $OutDir 'narration-timing.json'
    durationSeconds = $timingDocument.totalDurationSeconds
    voice = $VoiceName
} | ConvertTo-Json
