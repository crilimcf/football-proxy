# ==========================================================
# Get-FootballStatus.ps1
# Consulta API-FOOTBALL: estado, próximos jogos e ligas
# ==========================================================

$ApiKey = $env:APISPORTS_KEY
if (-not $ApiKey) {
    Write-Host "API key não encontrada. Executa: setx APISPORTS_KEY \"tua_chave_aqui\"" -ForegroundColor Yellow
    exit
}

$baseUrl = "https://v3.football.api-sports.io"

# ----------------------------------------------------------
function Get-ApiStatus {
# ----------------------------------------------------------
    Write-Host "`n[STATUS] Testando estado da API..." -ForegroundColor Cyan
    try {
        $status = Invoke-RestMethod -Uri "$baseUrl/status" -Headers @{ "x-apisports-key" = $ApiKey }
        $acc = $status.response.account
        $sub = $status.response.subscription
        Write-Host ("Conta: {0} {1} ({2})" -f $acc.firstname, $acc.lastname, $acc.email)
        Write-Host ("Plano: {0}" -f $sub.plan)
        Write-Host ("Limite diário: {0}" -f $status.response.requests.limit_day)
        Write-Host ("Expira em: {0}" -f $sub.end)
    }
    catch {
        Write-Host ("Erro ao obter status: {0}" -f $_.Exception.Message) -ForegroundColor Red
    }
}

# ----------------------------------------------------------
function Get-LeaguesNext3Days {
# ----------------------------------------------------------
    Write-Host "`n[LIGAS] Hoje, Amanhã e Depois..." -ForegroundColor Cyan

    $dates = @(
        (Get-Date).ToString("yyyy-MM-dd"),
        (Get-Date).AddDays(1).ToString("yyyy-MM-dd"),
        (Get-Date).AddDays(2).ToString("yyyy-MM-dd")
    )

    foreach ($date in $dates) {
        Write-Host ("`n=== {0} ===" -f $date) -ForegroundColor Yellow
        try {
            $fixtures = Invoke-RestMethod -Uri "$baseUrl/fixtures?date=$date" -Headers @{ "x-apisports-key" = $ApiKey }
            if ($fixtures.response.Count -eq 0) {
                Write-Host "Sem jogos nesta data." -ForegroundColor DarkGray
                continue
            }

            $grouped = $fixtures.response | Group-Object -Property { $_.league.name }
            foreach ($group in $grouped) {
                $league = $group.Group[0].league
                Write-Host ("{0} ({1}) - {2} jogos" -f $league.name, $league.country, $group.Count) -ForegroundColor Green
            }
        }
        catch {
            Write-Host ("Erro ao obter {0}: {1}" -f $date, $_.Exception.Message) -ForegroundColor Red
        }
    }
}

# ----------------------------------------------------------
# Execução principal
# ----------------------------------------------------------
Get-ApiStatus
Get-LeaguesNext3Days
