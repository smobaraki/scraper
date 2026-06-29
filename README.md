# Torshov Sport Scraper

Home Assistant add-on som overvåker en produktside på [torshovsport.no](https://www.torshovsport.no) for nye størrelser og lagerendringer. Sender epost-varsel umiddelbart når noe endrer seg.

## Slik fungerer det

Scraperen kjører i bakgrunnen og sjekker produktsiden hvert N. minutt. Den leser Apollo GraphQL-cachen på siden og trekker ut alle variant-data (størrelser, lagersaldo, priser, lagerbeholdning per butikk). Ved endring sender den epost umiddelbart.

---

## Installasjon i Home Assistant

### 1. Legg til add-on repository

1. Åpne Home Assistant → **Innstillinger** → **Tillegg**
2. Trykk på **Tilleggsbutikk**
3. Trykk på ⋮ (oppe til høyre) → **Lagre**
4. Lim inn: `https://github.com/smobaraki/scraper`
5. Trykk **Legg til**

### 2. Installer add-on

1. I Tilleggsbutikken finner du **"Torshov Sport size scraper"**
2. Trykk **Installer** — første gang tar 3-5 minutter (Docker-image bygges med Python + Chromium)

---

## Konfigurasjon

### Obligatorisk

| Felt | Beskrivelse | Eksempel |
|------|-------------|----------|
| **URL** | Lenke til produktsiden du vil overvåke | `https://www.torshovsport.no/fotball/.../nike-norge-...` |

Scraperen finner produkt-ID automatisk fra siden. Du trenger bare å lime inn URL-en.

### Valgfritt

| Felt | Standard | Beskrivelse |
|------|----------|-------------|
| **Poll interval** | `300` | Hvor ofte siden sjekkes, i sekunder (300 = 5 min) |

### Epost-varsling (valgfritt, anbefalt)

For å få epost når endringer oppdages, fyll inn SMTP-innstillingene:

| Felt | Eksempel | Beskrivelse |
|------|----------|-------------|
| **SMTP Host** | `smtp.gmail.com` | SMTP-serveradresse |
| **SMTP Port** | `587` | Port (587 for TLS, 465 for SSL) |
| **SMTP User** | `din.epost@gmail.com` | Epostadresse for innlogging |
| **SMTP Pass** | `abcd efgh ijkl mnop` | App-passord (IKKE ditt vanlige passord) |
| **SMTP From** | `din.epost@gmail.com` | Avsenderadresse |
| **SMTP To** | `din.epost@gmail.com` | Mottakeradresse |
| **SMTP TLS** | `true` | Bruk TLS-kryptering |

#### Slik lager du Gmail app-passord

1. Gå til https://myaccount.google.com/apppasswords
2. Logg inn med Google-kontoen din
3. Velg **App**: "Mail" og **Enhet**: "Annen"
4. Kopier passordet på 16 tegn (mellomrom godtas)

**Merk:** 2-faktor-autentisering må være påslått for at app-passord skal fungere.

---

## Hva skjer når noe endrer seg

Du får en epost som ser slik ut:

```
Subject: Torshov Sport – Nike Norge Herrelandslaget VM 2026 Fotballdrakt Hjemme

Nike Norge Herrelandslaget VM 2026 Fotballdrakt Hjemme
Tid: 2026-07-01 14:35:00

Endringer:
S ER NÅ PÅ LAGER! — 12594468_221111_257926 — 1249 kr
Ny størrelse: M (ikke på lager) — 12594468_221112_257926

Gå til produktsiden: https://www.torshovsport.no/fotball/...

— Torshov Sport Scraper
```

Endringer som varsles:
- 🆕 Ny størrelse dukker opp
- ✅ Størrelse går fra utsolgt → **på lager**
- ❌ Størrelse går tom
- 💲 Prisendring
- 🗑 Størrelse fjernes

---

## Logg

Følg med på hva som skjer under **Tillegg → Torshov Sport → Logg**:

```
🚀 Torshov Sport size scraper started
URL: https://www.torshovsport.no/...
Polling every 300 seconds
==================================================
Starting scrape of https://www.torshovsport.no/...
Detected product ID: 50368 — Nike Norge Herrelandslaget VM 2026 Fotballdrakt Hjemme
Size count: 1
  ❌ 3XL  Valgt alternativ ikke på lager (12594468_221052_258088)  1249 kr
    🏪 Torshov Sport Sandvika: -1
State saved to /data/state.json
Scrape finished.
Sleeping for 300 seconds...
```

---

## Oppdatering

Når ny versjon publiseres:
1. Gå til add-on'et i HA
2. Trykk **Rebuild** (eller avinstaller og installer på nytt)
