param(
    [Parameter(Mandatory)][string]$Pptx,
    [Parameter(Mandatory)][int]$Page,
    [Parameter(Mandatory)][string]$Png,
    [int]$Width = 1600
)
$ErrorActionPreference = 'Stop'
$path = (Resolve-Path -LiteralPath $Pptx).Path
$output = [IO.Path]::GetFullPath($Png)
$app = New-Object -ComObject PowerPoint.Application
$active = @($app.Presentations | Where-Object { $_.FullName -eq $path })
if ($active.Count) {
    $deck = $active[0]
} else {
    $deck = $app.Presentations.Open($path, -1, 0, 0)
}
try {
    if ($Page -lt 1 -or $Page -gt $deck.Slides.Count) {
        throw "Page $Page is outside the deck's $($deck.Slides.Count) slides"
    }
    $height = [int][math]::Round($Width * $deck.PageSetup.SlideHeight / $deck.PageSetup.SlideWidth)
    $deck.Slides.Item($Page).Export($output, 'PNG', $Width, $height)
    Write-Output $output
} finally {
    if (!$active.Count) { $deck.Close() }
}
