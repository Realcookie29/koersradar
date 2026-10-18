# De worker 24/7 laten draaien

De worker haalt elke 15 minuten koersen op, scant op signalen en houdt de paper trades bij. Staat hij uit, dan gebeurt er niets: geen verse koersen op de site, geen nieuwe signalen en geen paper trading. Voor een eerlijke vooruit-test van een paar weken moet hij dus ergens **altijd aan** staan.

## Welke plek?

| Plek | Kosten | Voordeel | Nadeel |
|---|---|---|---|
| **Synology NAS** (Container Manager) | €0 extra | Staat toch al aan, je hebt hem al | Werkt alleen op modellen met Container Manager; NAS moet internet hebben |
| **VPS** (bijv. Hetzner) | ongeveer €4 tot €6 per maand (prijs zelf controleren op hetzner.com) | Altijd aan, los van je eigen spullen | Kleine maandelijkse kosten, een server bijhouden |
| **Eigen pc** | €0 | Geen gedoe | Alleen als de pc aanstaat, dus geen echte 24/7 |

**Advies:** probeer eerst de **Synology**. Werkt dat niet (oud model of geen Container Manager), neem dan een VPS.

## Voorbereiding (voor elke plek)

1. **Databaseverbinding.** In Supabase: **Connect** → **Connection string** → **URI** → **Session pooler**. Vervang `[YOUR-PASSWORD]` door het databasewachtwoord (vergeten: Project Settings → Database → *Reset database password*).
2. **Migraties.** Alle bestanden in `supabase/migrations/` moeten in de database staan, op volgorde van naam. Dat kan via de SQL Editor in Supabase, of Claude past ze toe zodra `DATABASE_URL` is ingevuld.
3. **Welke code.** Gebruik `main` nadat de pull requests gemerged zijn. Wil je eerder beginnen, gebruik dan de branch met alles erin (nu `feat/marktoverzicht`).

Het `.env`-bestand op de server heeft minimaal dit nodig (kopieer `.env.example` en vul in):

```
DATABASE_URL=postgresql://postgres.<project>:<wachtwoord>@<regio>.pooler.supabase.com:5432/postgres
ANTHROPIC_API_KEY=            # optioneel: AI-uitleg bij signalen
LOG_LEVEL=INFO
```

Zet dit bestand **nooit** in git, en stuur het wachtwoord niet via chat of mail.

## Optie 1: Synology NAS

**Kan mijn NAS het?** Open **Package Center** en zoek op **Container Manager**. Staat hij erin, dan kan het. Zo niet, ga naar optie 2.

1. Installeer **Container Manager** via Package Center.
2. Zet **SSH** aan: Configuratiescherm → Terminal en SNMP → *SSH-service inschakelen*.
3. Maak in **File Station** een map `docker/koersradar` aan.
4. Log vanaf je pc in op de NAS (PowerShell of Terminal):
   ```bash
   ssh <jouw-nas-gebruiker>@<ip-van-je-nas>
   cd /volume1/docker/koersradar
   sudo git clone https://github.com/Realcookie29/Koersradar.git .
   ```
   Geen `git` op de NAS? Download de repo dan als ZIP van GitHub en pak hem uit in deze map via File Station.

   Een privé-repo vraagt bij `git clone` om in te loggen. Gebruik dan de ZIP-route, of een GitHub *fine-grained token* met alleen leesrechten.
5. Maak het `.env`-bestand aan in `/volume1/docker/koersradar` (zie hierboven), bijvoorbeeld met File Station → *Uploaden*, of met `sudo nano .env` in SSH.
6. Starten:
   ```bash
   sudo docker compose -f compose.server.yml up -d --build
   ```
   Op een oudere DSM heet het commando `sudo docker-compose` (met streepje).
7. Controleren:
   ```bash
   sudo docker compose -f compose.server.yml logs -f --tail 50
   ```
   Na een paar minuten zie je regels als `scan BTC/USDT 1h: NO_TRADE ...` en `paper trading: {...}`. De eerste keer haalt hij 45 dagen historie op; dat duurt een paar minuten.

**Gebruik niet de map die Synology Drive synchroniseert** (`D:\SynologyDrive\...`). De worker schrijft continu naar `data/`, en die wijzigingen gaan dan steeds heen en weer naar je pc.

## Optie 2: VPS

1. Maak bij een hostingbedrijf (bijvoorbeeld Hetzner Cloud) een kleine server: **Ubuntu 24.04**, de kleinste variant (2 vCPU, 2 tot 4 GB geheugen is ruim genoeg). Kies een locatie in de EU en log in met een SSH-sleutel, niet met een wachtwoord.
2. Log in en installeer Docker:
   ```bash
   ssh root@<ip-van-de-server>
   curl -fsSL https://get.docker.com | sh
   git clone https://github.com/Realcookie29/Koersradar.git /opt/koersradar
   cd /opt/koersradar
   cp .env.example .env && nano .env      # vul DATABASE_URL in
   docker compose -f compose.server.yml up -d --build
   docker compose -f compose.server.yml logs -f --tail 50
   ```
3. Houd de server bij: `apt update && apt upgrade` af en toe, of zet automatische beveiligingsupdates aan (`apt install unattended-upgrades`).

## Bijwerken na nieuwe code

```bash
git pull
docker compose -f compose.server.yml up -d --build
```

## Stoppen

```bash
docker compose -f compose.server.yml down
```

De data in `data/` en in Supabase blijft bewaard.

## Optie 3: eigen pc (tijdelijk)

Vanuit de hoofdmap van de repo, met de Python-omgeving uit de README:

```bash
set -a; . ./.env; set +a          # .env inlezen (Git Bash)
cd worker && .venv/Scripts/python -m koersradar.ingest.scheduler
```

Dit draait zolang het venster openstaat en de pc aanstaat.

## Problemen

- **`DATABASE_URL ontbreekt`**: het `.env`-bestand staat niet naast `compose.server.yml`, of de regel is leeg.
- **Verbinding mislukt / timeout**: gebruik de *Session pooler*-URL, niet *Direct connection*. De directe verbinding werkt alleen via IPv6.
- **`password authentication failed`**: het wachtwoord in de URL klopt niet. Staan er speciale tekens in (zoals `@`, `#` of `/`)? Reset het dan naar een wachtwoord met alleen letters en cijfers.
- **Supabase pauzeert het project**: dat gebeurt na een week zonder activiteit. Zolang de worker draait, gebeurt dat niet.
