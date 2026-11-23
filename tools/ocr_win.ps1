# 윈도우 내장 일본어 OCR(Windows.Media.Ocr) — work/ocr/lines/*.png → work/ocr/ocr.tsv (번호<TAB>줄1|줄2…)
#   powershell -ExecutionPolicy Bypass -File tools/ocr_win.ps1
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, $t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(); $task.Result }
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]
$lang = [Windows.Globalization.Language]::new('ja')
$eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$sub = if ($args.Count -gt 0) { $args[0] } else { 'ocr' }
$out = New-Object System.Collections.Generic.List[string]
Get-ChildItem (Join-Path $root ('work\' + $sub + '\lines')) -Filter *.png | Sort-Object Name | ForEach-Object {
  $f = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($_.FullName)) ([Windows.Storage.StorageFile])
  $s = Await ($f.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
  $dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($s)) ([Windows.Graphics.Imaging.BitmapDecoder])
  $bmp = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
  $r = Await ($eng.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
  $lines = ($r.Lines | ForEach-Object { ($_.Words | ForEach-Object { $_.Text }) -join '' }) -join '|'
  $out.Add($_.BaseName + "`t" + $lines)
  $s.Dispose()
}
[System.IO.File]::WriteAllLines((Join-Path $root ('work\' + $sub + '\ocr.tsv')), $out, (New-Object System.Text.UTF8Encoding $false))
"끝 " + $out.Count
