# Serveur local minimal (Windows sans Python) : sert ce dossier sur http://localhost:<port>/
param([int]$Port = 8765)
$racine = Split-Path -Parent $MyInvocation.MyCommand.Path
$types = @{ ".html" = "text/html; charset=utf-8"; ".json" = "application/json; charset=utf-8"; ".js" = "text/javascript; charset=utf-8";
            ".css" = "text/css; charset=utf-8"; ".svg" = "image/svg+xml"; ".png" = "image/png"; ".ico" = "image/x-icon"; ".txt" = "text/plain; charset=utf-8";
            ".csv" = "text/csv; charset=utf-8"; ".woff2" = "font/woff2" }
$ecoute = New-Object System.Net.HttpListener
$ecoute.Prefixes.Add("http://localhost:$Port/")
$ecoute.Start()
while ($ecoute.IsListening) {
  $ctx = $ecoute.GetContext()
  $chemin = [System.Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart("/"))
  if ($chemin -eq "") { $chemin = "index.html" }
  $fichier = Join-Path $racine $chemin
  if ((Test-Path $fichier -PathType Leaf) -and ((Resolve-Path $fichier).Path.StartsWith($racine))) {
    $octets = [System.IO.File]::ReadAllBytes($fichier)
    $ext = [System.IO.Path]::GetExtension($fichier).ToLower()
    $ctx.Response.ContentType = $(if ($types.ContainsKey($ext)) { $types[$ext] } else { "application/octet-stream" })
    $ctx.Response.ContentLength64 = $octets.Length
    $ctx.Response.OutputStream.Write($octets, 0, $octets.Length)
  } else { $ctx.Response.StatusCode = 404 }
  $ctx.Response.Close()
}
