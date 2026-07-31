param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8080,

    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

$siteRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$indexFile = Join-Path $siteRoot 'index.html'
$previewUrl = "http://127.0.0.1:$Port/"

if (-not (Test-Path -LiteralPath $indexFile -PathType Leaf)) {
    throw "Chatbot entry file not found: $indexFile"
}

$mimeTypes = @{
    '.css'  = 'text/css; charset=utf-8'
    '.gif'  = 'image/gif'
    '.htm'  = 'text/html; charset=utf-8'
    '.html' = 'text/html; charset=utf-8'
    '.ico'  = 'image/x-icon'
    '.jpeg' = 'image/jpeg'
    '.jpg'  = 'image/jpeg'
    '.js'   = 'text/javascript; charset=utf-8'
    '.json' = 'application/json; charset=utf-8'
    '.png'  = 'image/png'
    '.svg'  = 'image/svg+xml'
    '.webp' = 'image/webp'
}

function Write-HttpResponse {
    param(
        [Parameter(Mandatory)]
        [System.IO.Stream]$Stream,

        [Parameter(Mandatory)]
        [int]$StatusCode,

        [Parameter(Mandatory)]
        [string]$StatusText,

        [Parameter(Mandatory)]
        [string]$ContentType,

        [Parameter(Mandatory)]
        [byte[]]$Body,

        [switch]$HeadOnly
    )

    $headers = @(
        "HTTP/1.1 $StatusCode $StatusText"
        "Content-Type: $ContentType"
        "Content-Length: $($Body.Length)"
        'Cache-Control: no-cache'
        'Connection: close'
        ''
        ''
    ) -join "`r`n"

    $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($headers)
    $Stream.Write($headerBytes, 0, $headerBytes.Length)

    if (-not $HeadOnly -and $Body.Length -gt 0) {
        $Stream.Write($Body, 0, $Body.Length)
    }
}

$listener = [System.Net.Sockets.TcpListener]::new(
    [System.Net.IPAddress]::Loopback,
    $Port
)

try {
    $listener.Start()

    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host ' AlumCraft Product Assistant Preview' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host "Serving: $siteRoot" -ForegroundColor Gray
    Write-Host "Preview: $previewUrl" -ForegroundColor Green
    Write-Host 'Press Ctrl+C to stop.' -ForegroundColor Yellow
    Write-Host ''

    if (-not $NoBrowser) {
        try {
            Start-Process $previewUrl
        }
        catch {
            Write-Warning "Could not open the browser automatically. Open $previewUrl manually."
        }
    }

    while ($true) {
        $client = $listener.AcceptTcpClient()

        try {
            $stream = $client.GetStream()
            $reader = [System.IO.StreamReader]::new(
                $stream,
                [System.Text.Encoding]::ASCII,
                $false,
                1024,
                $true
            )

            $requestLine = $reader.ReadLine()
            do {
                $headerLine = $reader.ReadLine()
            } while ($null -ne $headerLine -and $headerLine.Length -gt 0)

            if ([string]::IsNullOrWhiteSpace($requestLine)) {
                continue
            }

            $requestParts = $requestLine.Split(' ')
            $method = $requestParts[0].ToUpperInvariant()

            if ($requestParts.Length -lt 2 -or ($method -ne 'GET' -and $method -ne 'HEAD')) {
                $body = [System.Text.Encoding]::UTF8.GetBytes('Method Not Allowed')
                Write-HttpResponse -Stream $stream -StatusCode 405 -StatusText 'Method Not Allowed' -ContentType 'text/plain; charset=utf-8' -Body $body -HeadOnly:($method -eq 'HEAD')
                continue
            }

            $rawPath = $requestParts[1].Split('?')[0]
            $relativePath = [System.Uri]::UnescapeDataString($rawPath).TrimStart('/').Replace('/', [System.IO.Path]::DirectorySeparatorChar)

            if ([string]::IsNullOrWhiteSpace($relativePath)) {
                $relativePath = 'index.html'
            }

            $filePath = [System.IO.Path]::GetFullPath((Join-Path $siteRoot $relativePath))
            $rootPrefix = $siteRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

            if (-not $filePath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                $body = [System.Text.Encoding]::UTF8.GetBytes('Forbidden')
                Write-HttpResponse -Stream $stream -StatusCode 403 -StatusText 'Forbidden' -ContentType 'text/plain; charset=utf-8' -Body $body -HeadOnly:($method -eq 'HEAD')
                continue
            }

            if (Test-Path -LiteralPath $filePath -PathType Container) {
                $filePath = Join-Path $filePath 'index.html'
            }

            if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
                $body = [System.Text.Encoding]::UTF8.GetBytes('Not Found')
                Write-HttpResponse -Stream $stream -StatusCode 404 -StatusText 'Not Found' -ContentType 'text/plain; charset=utf-8' -Body $body -HeadOnly:($method -eq 'HEAD')
                continue
            }

            $extension = [System.IO.Path]::GetExtension($filePath).ToLowerInvariant()
            $contentType = if ($mimeTypes.ContainsKey($extension)) {
                $mimeTypes[$extension]
            }
            else {
                'application/octet-stream'
            }

            $body = [System.IO.File]::ReadAllBytes($filePath)
            Write-HttpResponse -Stream $stream -StatusCode 200 -StatusText 'OK' -ContentType $contentType -Body $body -HeadOnly:($method -eq 'HEAD')
        }
        catch {
            Write-Warning "Request failed: $($_.Exception.Message)"
        }
        finally {
            $client.Close()
        }
    }
}
catch [System.Net.Sockets.SocketException] {
    throw "Could not start the preview server on port $Port. The port may already be in use. Try: .\startup.ps1 -Port 8081"
}
finally {
    $listener.Stop()
}
