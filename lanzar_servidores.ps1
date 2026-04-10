# Definir cuántos workers quieres levantar (cambia este número según el test)
$num_workers = 1

Write-Host "Levantando $num_workers servidores REST..." -ForegroundColor Cyan

1..$num_workers | ForEach-Object {
    $p = 5000 + $_
    # Abre una nueva ventana minimizada para cada servidor
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PORT=$p; python direct-communication/rest_server.py" -WindowStyle Minimized
}

Write-Host "¡Servidores listos en los puertos 5001 al $(5000 + $num_workers)!" -ForegroundColor Green