param([switch]$Verify, [switch]$Stage)
$ErrorActionPreference = 'Stop'
$launcherApp = Split-Path -Parent $PSScriptRoot
$launcherFolder = Join-Path $launcherApp 'bootstrap'
$launcherCompiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if (-not (Test-Path -LiteralPath $launcherCompiler)) { throw 'Compilador C# .NET Framework 4 não encontrado. Nada foi instalado.' }
$launcherOutput = Join-Path $launcherFolder 'MegaBrain.exe'
if ($Stage) { $launcherOutput = Join-Path $launcherFolder 'MegaBrain.next.exe' }
$launcherSource = Join-Path $launcherFolder 'MegaBrainLauncher.cs'
$launcherIcon = Join-Path $launcherApp 'assets/megabrain-cerebro-rosa.ico'
& $launcherCompiler /nologo /target:winexe /platform:x64 /optimize+ /utf8output "/out:$launcherOutput" "/win32icon:$launcherIcon" /reference:System.Management.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll $launcherSource
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar o lançador.' }
if ($Verify) {
    $launcherCheck = Start-Process -FilePath $launcherOutput -ArgumentList '--verify' -WindowStyle Hidden -Wait -PassThru
    if ($launcherCheck.ExitCode -ne 0) { throw 'A verificação falhou. Consulte bootstrap/launcher.log.' }
}
Get-Item -LiteralPath $launcherOutput | Select-Object FullName, Length
