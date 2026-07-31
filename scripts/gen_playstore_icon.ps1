# Genera playstore-icon.png 512x512 para Google Play Console.
# No se empaqueta en el APK: es solo para subir a Play Store.
# Uso: pwsh scripts/gen_playstore_icon.ps1
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$root = (Resolve-Path "$PSScriptRoot\..").Path
$outPath = Join-Path $root "mobile-kotlin\app\src\main\playstore-icon.png"

$bmp = New-Object System.Drawing.Bitmap(512, 512)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

$red = [System.Drawing.Color]::FromArgb(229, 9, 20)
$white = [System.Drawing.Color]::White

$g.FillRectangle((New-Object System.Drawing.SolidBrush($red)), 0, 0, 512, 512)

$whiteBrush = New-Object System.Drawing.SolidBrush($white)
$g.FillEllipse($whiteBrush, 156, 156, 200, 200)

$redPen = New-Object System.Drawing.Pen($red, 14)
$redPen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
$redPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
$g.DrawLine($redPen, 256, 256, 256, 200)
$g.DrawLine($redPen, 256, 256, 310, 256)

$g.FillEllipse((New-Object System.Drawing.SolidBrush($red)), 176, 132, 36, 28)
$g.FillEllipse((New-Object System.Drawing.SolidBrush($red)), 300, 132, 36, 28)

$bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()

Write-Output "Play Store icon generated: $outPath (512x512)"
