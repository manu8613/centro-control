<#
  Centro de Control — copias, inventario y configuración desde Windows.
  Creado por manu8613 · https://github.com/manu8613/centro-control

  Uso (en PowerShell, en la carpeta donde está este fichero):

    powershell -ExecutionPolicy Bypass -File .\centro-control.ps1 exportar
    powershell -ExecutionPolicy Bypass -File .\centro-control.ps1 aplicar  .\plan.json
    powershell -ExecutionPolicy Bypass -File .\centro-control.ps1 restaurar .\CentroControl\config_actual_AAAAMMDD_HHMMSS.json
    powershell -ExecutionPolicy Bypass -File .\centro-control.ps1 comprobar

  Pide la dirección de Home Assistant y un token de larga duración de un
  administrador (Perfil → Seguridad → Tokens de acceso de larga duración).
  El token NO se guarda en ningún sitio.

  · exportar   Solo lee: guarda el inventario (entidades, paneles, panel de
               Energía…) y la configuración actual de Centro de Control.
  · aplicar    Copia de seguridad completa de Home Assistant + copia de la
               configuración actual, simula el plan, pide confirmación, lo
               aplica y comprueba que todo responde.
  · restaurar  Igual que aplicar, pero con una copia guardada.
  · comprobar  Estado de las entidades de Centro de Control y problemas.
#>
param(
  [Parameter(Position = 0)][ValidateSet("exportar", "aplicar", "restaurar", "comprobar")][string]$Accion = "exportar",
  [Parameter(Position = 1)][string]$Fichero = "",
  [string]$Url = "",
  [switch]$Inseguro,
  [switch]$SinCopiaCompleta
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
if ($Inseguro) { [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true } }

$Carpeta = Join-Path (Get-Location) "CentroControl"
New-Item -ItemType Directory -Force -Path $Carpeta | Out-Null
$Sello = Get-Date -Format "yyyyMMdd_HHmmss"

function Titulo($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Ok($t) { Write-Host "  [OK] $t" -ForegroundColor Green }
function Aviso($t) { Write-Host "  [!] $t" -ForegroundColor Yellow }
function Fallo($t) { Write-Host "  [X] $t" -ForegroundColor Red }

# ---------------------------------------------------------------- conexión
if (-not $Url) { $Url = Read-Host "Dirección de Home Assistant (Intro = http://homeassistant.local:8123)" }
if (-not $Url) { $Url = "http://homeassistant.local:8123" }
$Url = $Url.TrimEnd("/")
$Seguro = Read-Host "Token de larga duración (no se muestra ni se guarda)" -AsSecureString
$Token = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($Seguro))
$Cab = @{ Authorization = "Bearer $Token" }

function Pedir([string]$Metodo, [string]$Ruta, [string]$Cuerpo = $null, [int]$Espera = 120) {
  $p = @{ Method = $Metodo; Uri = "$Url$Ruta"; Headers = $Cab; TimeoutSec = $Espera; UseBasicParsing = $true }
  if ($Cuerpo) {
    $p.Body = [System.Text.Encoding]::UTF8.GetBytes($Cuerpo)
    $p.ContentType = "application/json; charset=utf-8"
  }
  $r = Invoke-WebRequest @p
  $bytes = $r.RawContentStream.ToArray()
  return [System.Text.Encoding]::UTF8.GetString($bytes)
}
function Guardar([string]$Nombre, [string]$Texto) {
  $ruta = Join-Path $Carpeta $Nombre
  [System.IO.File]::WriteAllText($ruta, $Texto, (New-Object System.Text.UTF8Encoding($false)))
  return $ruta
}

Titulo "Conexión"
try {
  $api = Pedir "GET" "/api/" | ConvertFrom-Json
  Ok "Home Assistant responde: $($api.message)"
} catch {
  Fallo "No puedo conectar con $Url : $($_.Exception.Message)"
  Write-Host "  Comprueba la dirección y el token. Si usas https con certificado propio, añade -Inseguro."
  exit 1
}
try {
  Pedir "GET" "/api/centro_control/configuracion" | Out-Null
} catch {
  Fallo "La API de Centro de Control no responde. Actualiza Centro de Control en HACS (2.1.0 o superior), reinicia y vuelve a probar. Debe ser el token de un administrador."
  exit 1
}

function CopiaCompleta {
  if ($SinCopiaCompleta) { Aviso "Sin copia completa (-SinCopiaCompleta)"; return }
  Titulo "Copia de seguridad completa de Home Assistant"
  Write-Host "  Puede tardar unos minutos..."
  $nombre = "Centro de Control - antes de cambios $Sello"
  try {
    Pedir "POST" "/api/services/hassio/backup_full" ('{"name":"' + $nombre + '"}') -Espera 3600 | Out-Null
    Ok "Copia completa creada: «$nombre» (Ajustes → Sistema → Copias de seguridad)"
    return
  } catch { Aviso "hassio.backup_full no disponible: $($_.Exception.Message)" }
  try {
    Pedir "POST" "/api/services/backup/create_automatic" "{}" -Espera 3600 | Out-Null
    Ok "Copia automática creada (Ajustes → Sistema → Copias de seguridad)"
    return
  } catch { Fallo "No se pudo crear la copia completa: $($_.Exception.Message)" }
  $r = Read-Host "¿Seguir SIN copia completa? (escribe SI)"
  if ($r -ne "SI") { exit 1 }
}

function CopiaConfig {
  $txt = Pedir "GET" "/api/centro_control/configuracion"
  $ruta = Guardar "config_actual_$Sello.json" $txt
  Ok "Configuración actual guardada en $ruta"
}

function Comprobar {
  Titulo "Comprobación"
  Start-Sleep -Seconds 15
  $est = Pedir "GET" "/api/centro_control/estado" -Espera 120 | ConvertFrom-Json
  Ok "Centro de Control $($est.version): $($est.entidades) entidades"
  foreach ($e in $est.entradas) {
    Ok "«$($e.titulo)» ($($e.estado)): $($e.elementos) strings/baterías/circuitos/zonas"
    Write-Host ("  Ahora: solar {0} W · red {1} W · consumo {2} W · batería {3} W · SOC {4} %" -f $e.solar_w, $e.red_w, $e.consumo_w, $e.bateria_w, $e.soc)
    if (@($e.problemas).Count) { Aviso "Problemas detectados:"; $e.problemas | ForEach-Object { Write-Host "     - $_" } }
    else { Ok "Sin problemas detectados" }
  }
  if (@($est.sin_dato).Count) {
    Aviso "$(@($est.sin_dato).Count) entidades sin dato todavía (normal en algunas hasta que pase un rato):"
    $est.sin_dato | Select-Object -First 20 | ForEach-Object { Write-Host "     - $_" }
  }
  Guardar "comprobacion_$Sello.json" ($est | ConvertTo-Json -Depth 10) | Out-Null
}

function Aplicar([string]$Ruta) {
  if (-not $Ruta -or -not (Test-Path $Ruta)) { Fallo "Indica el fichero: .\centro-control.ps1 $Accion .\plan.json"; exit 1 }
  $raw = [System.IO.File]::ReadAllText((Resolve-Path $Ruta), [System.Text.Encoding]::UTF8).Trim()
  try { $plan = $raw | ConvertFrom-Json } catch { Fallo "El fichero no es JSON válido: $($_.Exception.Message)"; exit 1 }
  if (-not $plan.entradas) { Fallo "El fichero no tiene «entradas»."; exit 1 }

  Titulo "Simulación"
  $sim = Pedir "POST" "/api/centro_control/configuracion" ('{"simular":true,' + $raw.Substring(1)) | ConvertFrom-Json
  foreach ($e in $plan.entradas) { Write-Host "  «$($e.titulo)»: $(@($e.elementos).Count) elementos" }
  if ($sim.avisos -and @($sim.avisos).Count) {
    Aviso "Entidades que no existen (se guardarán igual, pero no darán datos):"
    $sim.avisos | ForEach-Object { Write-Host "     - $_" }
  } else { Ok "Todas las entidades del plan existen" }
  $r = Read-Host "¿Aplicar? (escribe SI)"
  if ($r -ne "SI") { Write-Host "Cancelado. No se ha tocado nada."; exit 0 }

  CopiaCompleta
  Titulo "Copia de la configuración actual"
  CopiaConfig

  Titulo "Aplicando"
  $res = Pedir "POST" "/api/centro_control/configuracion" $raw -Espera 300 | ConvertFrom-Json
  if (-not $res.ok) { Fallo "Home Assistant no lo aceptó: $($res | ConvertTo-Json -Depth 5)"; exit 1 }
  Ok "Aplicado. Copia en Home Assistant: $($res.copia)"
  Comprobar
  Write-Host ""
  Write-Host "Para deshacer: .\centro-control.ps1 restaurar .\CentroControl\config_actual_$Sello.json" -ForegroundColor Cyan
}

switch ($Accion) {
  "exportar" {
    Titulo "Inventario (solo lectura)"
    $txt = Pedir "GET" "/api/centro_control/inventario" -Espera 300
    $ruta = Guardar "inventario_$Sello.json" $txt
    Ok "Inventario guardado en $ruta"
    CopiaConfig
    $zip = Join-Path $Carpeta "inventario_$Sello.zip"
    Compress-Archive -Path $ruta -DestinationPath $zip -Force
    Ok "Comprimido en $zip"
    Write-Host ""
    Write-Host "Sube $zip a Claude para preparar tu plan de configuración." -ForegroundColor Cyan
  }
  "aplicar" { Aplicar $Fichero }
  "restaurar" { Aplicar $Fichero }
  "comprobar" { Comprobar }
}
$Token = $null
