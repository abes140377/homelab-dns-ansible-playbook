# DNS-Architektur im Homelab

## Übersicht

Das DNS-Setup kombiniert vier spezialisierte Dienste zu einer hochverfügbaren Lösung:

1. **AdGuard Home** - Zentraler Gateway mit Ad-Blocking und DNS-Routing
2. **Bind9 Primary** - Master-Verwaltung der internen Zone `home.sflab.io`
3. **Bind9 Secondary** - Redundanz durch automatische Synchronisation
4. **Unbound** - Privacy-freundlicher rekursiver Resolver für externe Domains

## Komponenten

### AdGuard Home (Port 53)
- **Standort**: Raspberry Pi (192.168.1.13:53)
- **Funktion**: Zentraler Einstiegspunkt für alle DNS-Anfragen
- **Features**:
  - Ad-Blocking und Tracking-Schutz
  - DNS-over-HTTPS/TLS Unterstützung
  - Query-Logging und Statistiken (Web-UI auf Port 3000)
  - Intelligentes Routing zu Bind9 Primary oder Unbound

### Bind9 Primary (Port 5353)
- **Standort**: Raspberry Pi (192.168.1.13:5353)
- **Funktion**: Autoritativer Master für interne Domains
- **Zuständigkeit**:
  - Master-Zone `home.sflab.io`
  - Reverse-DNS für 192.168.1.0/24
  - Zonentransfer und NOTIFY an Secondary
- **Erreichbarkeit**: Lokal für AdGuard Home (127.0.0.1:5353), extern für Zonentransfer (192.168.1.13:5353)

### Bind9 Secondary (Port 53)
- **Standort**: Proxmox LXC (192.168.1.14:53)
- **Funktion**: Read-Only Slave für Hochverfügbarkeit
- **Features**:
  - Automatische Synchronisation via AXFR/IXFR
  - Failover bei Primary-Ausfall
  - Lastverteilung für DNS-Anfragen

### Unbound (Port 5335)
- **Standort**: Raspberry Pi (127.0.0.1:5335)
- **Funktion**: Rekursiver Resolver für externe Domains
- **Vorteile**:
  - Direkte Kommunikation mit Root-Servern
  - Keine Abhängigkeit von ISP/Public-DNS
  - Erhöhte Privacy

## Architektur-Diagramm

```
┌─────────────────────────────────────────────────┐
│           Clients (192.168.1.20-50)             │
└──────────────┬──────────────────────────────────┘
               │ DNS-Anfrage
               │ Primary: 192.168.1.13:53
               │ Secondary: 192.168.1.14:53
      ┌────────┴──────────────┐
      │                       │
      ↓ (Primary)             ↓ (Failover)
┌───────────────────┐   ┌────────────────┐
│   Raspberry Pi    │   │  Proxmox LXC   │
│   192.168.1.13    │   │  192.168.1.14  │
│                   │   │                │
│ ┌──────────────┐  │   │ ┌────────────┐ │
│ │AdGuard Home  │  │   │ │Bind9 Sec.  │ │
│ │  (Port 53)   │  │   │ │ (Port 53)  │ │
│ └─┬──────────┬─┘  │   │ │ Read-Only  │ │
│   │          │    │   │ └────────────┘ │
│ ┌─▼─────┐  ┌─▼──┐ │   │       ↑        │
│ │Bind9  │  │Unb │ │   │       │        │
│ │       │  │oun │ │   │       │        │
│ │Primary│  │d   │ │   │       │        │
│ │5353   │  │5335│─│───┼───────┘        │
│ └───────┘  └────┘ │   │ Zonentransfer  │
│ Master Zone       │   │ NOTIFY/AXFR    │
└───────────────────┘   └────────────────┘
```

## DNS-Auflösung - Szenarien

### 1. Externe Domain (z.B. google.com)

```
Client → AdGuard Home (192.168.1.13:53)
  ├─→ Prüfung: Blocklist? [NEIN]
  └─→ Weiterleitung → Unbound (127.0.0.1:5335)
      └─→ Rekursive Auflösung über Root-Server
          └─→ Antwort → AdGuard Home → Client
```

### 2. Blockierte Domain (z.B. doubleclick.net)

```
Client → AdGuard Home (192.168.1.13:53)
  └─→ Prüfung: Blocklist? [JA]
      └─→ Direkte Antwort: 0.0.0.0
```

### 3. Interne Domain (z.B. nas.home.sflab.io)

```
Client → AdGuard Home (192.168.1.13:53)
  ├─→ Prüfung: *.home.sflab.io? [JA]
  └─→ Weiterleitung → Bind9 Primary (127.0.0.1:5353)
      └─→ Zonenlookup: nas IN A 192.168.1.20
          └─→ Antwort → AdGuard Home → Client
```

### 4. Failover-Szenario (Raspberry Pi offline)

```
Client → Primary DNS (192.168.1.13:53) [TIMEOUT]
  └─→ Fallback → Secondary DNS (192.168.1.14:53)
      └─→ Bind9 Secondary liefert interne Domains

⚠️  Externe Domains nicht verfügbar (kein Unbound auf Secondary)

Homelab-Lösungen:
  → Option A: Unbound auch auf Secondary installieren
  → Option B: AdGuard Home + Unbound auf LXC (echte Redundanz)
  → Option C: Ausfall akzeptieren (Primary meist verfügbar)
```

## Primary-Secondary Synchronisation

### Zonentransfer-Ablauf

```
1. Administrator ändert Zone auf Primary
   └─→ SOA Serial erhöhen (YYYYMMDDNN)

2. Primary sendet NOTIFY → Secondary (192.168.1.14)

3. Secondary prüft SOA Serial
   ├─→ Gleiche Serial → Keine Aktion
   └─→ Höhere Serial → AXFR/IXFR Request

4. Primary überträgt Zone
   ├─→ AXFR: Vollständiger Transfer
   └─→ IXFR: Nur Änderungen (effizient)

5. Secondary lädt Zone neu
```

### SOA Record Parameter

```dns
@  IN  SOA  ns1.home.sflab.io. admin.home.sflab.io. (
    2024101302  ; Serial - MUSS bei jeder Änderung erhöht werden
    600         ; Refresh (10 Min) - Prüfintervall für Homelab
    300         ; Retry (5 Min) - Schnelle Wiederholung bei Fehler
    604800      ; Expire (7 Tage) - Gültigkeit ohne Primary
    300 )       ; Negative Cache TTL (5 Min) - Schnelles Feedback
```

**Parameter erklärt:**

| Parameter        | Wert             | Beschreibung                                                               |
|------------------|------------------|----------------------------------------------------------------------------|
| **Serial**       | YYYYMMDDNN       | Format: Jahr-Monat-Tag-Nummer. MUSS bei jeder Änderung erhöht werden!      |
| **Refresh**      | 600s (10 Min)    | Secondary prüft Primary auf Updates (Homelab: kurz für schnelles Feedback) |
| **Retry**        | 300s (5 Min)     | Wiederholung bei fehlgeschlagenem Refresh                                  |
| **Expire**       | 604800s (7 Tage) | Nach dieser Zeit verweigert Secondary Antworten ohne Primary-Kontakt       |
| **Negative TTL** | 300s (5 Min)     | Caching-Zeit für "nicht existiert"-Antworten (kurz für Homelab)            |

### Synchronisations-Trigger

| Trigger     | Beschreibung                             | Vorteil                          |
|-------------|------------------------------------------|----------------------------------|
| **NOTIFY**  | Primary benachrichtigt Secondary sofort  | Schnelle Propagation (< 30s)     |
| **Refresh** | Secondary prüft periodisch (z.B. 10 Min) | Failsafe bei NOTIFY-Ausfall      |
| **Manuell** | `rndc reload` / `rndc refresh`           | Admin-gesteuerte Synchronisation |

## Hochverfügbarkeits-Szenarien

### Szenario A: Raspberry Pi offline
```
Situation: AdGuard Home, Bind9 Primary, Unbound offline
├─→ Funktion: Interne Domains über Secondary ✓
└─→ Einschränkung: Externe Domains nicht verfügbar ⚠️

⚠️  Homelab-Empfehlung: Akzeptiere Ausfall oder installiere
    AdGuard Home + Unbound auch auf Secondary (LXC)
```

### Szenario B: Proxmox LXC offline
```
Situation: Bind9 Secondary offline
├─→ Funktion: Alles normal über Primary ✓
└─→ Risiko: Keine Redundanz
```

### Szenario C: Netzwerk-Split
```
Situation: Primary und Secondary getrennt
├─→ Secondary nutzt letzte synchronisierte Zonendaten
├─→ Schutz: Keine Split-Brain-Gefahr (Secondary ist Read-Only)
└─→ Expire: Nach 4 Wochen verweigert Secondary Antworten
```

## Netzwerk-Details

### Port-Übersicht

| Dienst          | Server       | Port | Erreichbarkeit | Zweck               |
|-----------------|--------------|------|----------------|---------------------|
| AdGuard Home    | Raspberry Pi | 53   | 192.168.1.13   | DNS + Ad-Blocking   |
| AdGuard Home UI | Raspberry Pi | 3000 | 192.168.1.13   | Web-Interface       |
| Bind9 Primary   | Raspberry Pi | 5353 | 127.0.0.1      | Intern für AdGuard  |
| Bind9 Primary   | Raspberry Pi | 5353 | 192.168.1.13   | Zonentransfer       |
| Bind9 Secondary | Proxmox LXC  | 53   | 192.168.1.14   | Redundanz           |
| Unbound         | Raspberry Pi | 5335 | 127.0.0.1      | Rekursive Auflösung |

### Nameserver Records

```dns
home.sflab.io.      IN  NS  ns1.home.sflab.io.
home.sflab.io.      IN  NS  ns2.home.sflab.io.

ns1.home.sflab.io.  IN  A   192.168.1.13
ns2.home.sflab.io.  IN  A   192.168.1.14
```

**Warum beide NS-Records?**
- DNS-Standards erlauben Client-Wahl
- Lastverteilung möglich
- Redundanz bei Server-Ausfall
- Übergeordnete Zonen können auf beide verweisen

### Netzwerk-Topologie

```
                   Internet
                      │
                  ┌───┴────┐
                  │ Router │
                  └───┬────┘
                      │
        ┌─────────────┼──────────────┐
        │      192.168.1.0/24        │
        └─────────────┬──────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ↓             ↓             ↓
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │Raspberry │  │ Proxmox  │  │ Clients  │
  │    Pi    │  │   LXC    │  │          │
  │          │  │          │  │ .1.20-50 │
  │  .1.13   │←→│  .1.14   │  │          │
  │          │  │          │  │          │
  │ Primary  │  │Secondary │  │          │
  │+ AdGuard │  │   DNS    │  │          │
  │+ Unbound │  │          │  │          │
  └──────────┘  └──────────┘  └──────────┘
       │              │              │
       └──────────────┴──────────────┘
              Zonentransfer
              + DNS-Anfragen
```

## Best Practices

### Client-Konfiguration

```
Primary DNS:   192.168.1.13  (AdGuard Home - volle Funktionalität)
Secondary DNS: 192.168.1.14  (Bind9 Secondary - nur interne Domains)

⚠️  KEIN Tertiary DNS empfohlen für Homelab:
    - Clients nutzen DNS-Server nicht sequenziell
    - 1.1.1.1 könnte spontan genutzt werden → Ad-Blocking umgangen
    - Besser: Bei Primary-Ausfall kurze Downtime akzeptieren
    - Alternative: AdGuard Home auch auf LXC für echte Redundanz
```

### Zonenverwaltung

**DO ✓**
- Alle Änderungen nur auf Primary
- Serial bei jeder Änderung erhöhen
- Zonendateien vor Reload validieren
- Regelmäßige Backups

**DON'T ✗**
- Niemals Zonendateien auf Secondary ändern
- Serial vergessen zu erhöhen
- Mehrere Änderungen ohne Serial-Inkrement

### Monitoring

**Kritische Metriken:**
- Zonentransfer-Erfolgsrate
- SOA Serial-Synchronisation (Delta < 5 Min)
- NOTIFY-Erfolgsrate
- DNS-Query-Response-Zeit
- Server-Verfügbarkeit

### Sicherheit

**Access Control Lists:**
- Zonentransfer nur von bekannten IPs (Secondary)
- NOTIFY nur an definierte Secondary-Server
- Rekursion nur für vertrauenswürdige Netze (z.B. 192.168.1.0/24)

**Optional: DNSSEC**
- Signierung der Zonen
- Schutz vor DNS-Spoofing/Cache-Poisoning

## Troubleshooting

### Secondary synchronisiert nicht

**Prüfungen:**
```bash
ping 192.168.1.13                            # Erreichbarkeit
nc -zv 192.168.1.13 5353                     # Port offen?
dig @192.168.1.13 -p 5353 home.sflab.io SOA  # SOA abrufbar?
```

**Lösung:**
- Firewall-Regeln prüfen (TCP Port 5353)
- Bind9-Logs analysieren: `journalctl -u named`
- Manueller Transfer: `rndc refresh home.sflab.io`

### Clients erreichen Secondary nicht

**Prüfungen:**
```bash
ping 192.168.1.14                     # Erreichbarkeit
dig @192.168.1.14 nas.home.sflab.io   # DNS antwortet?
```

**Lösung:**
- Bind9-Service-Status: `systemctl status named`
- Firewall auf LXC prüfen (Port 53 UDP/TCP)
- Client-DNS-Einstellungen verifizieren

### Zonenänderungen werden nicht übernommen

**Ursache:** Serial wurde nicht erhöht

**Lösung:**
```bash
# 1. Serial auf Primary erhöhen
vim /etc/bind/zones/db.home.sflab.io  # Serial: YYYYMMDDNN++

# 2. Zone neu laden
rndc reload home.sflab.io

# 3. Synchronisation prüfen
dig @192.168.1.14 home.sflab.io SOA
```

### Externe Domains über Secondary funktionieren nicht

**Antwort:** Das ist by Design! Secondary ist NUR für interne Domains autoritativ.

**Lösung:** Siehe Architektur-Varianten unten für vollständige Redundanz.

## Erweiterungen

### Zusätzliche Secondary-Server

```
Aktuell: Primary + 1 Secondary
Möglich: Primary + N Secondary

ns1.home.sflab.io (192.168.1.13) - Primary
ns2.home.sflab.io (192.168.1.14) - Secondary 1
ns3.home.sflab.io (192.168.1.15) - Secondary 2  ← Neu

Vorteil: Höhere Verfügbarkeit + Lastverteilung
```

### Hidden Primary

```
Konzept: Primary nicht öffentlich erreichbar
         Nur Secondary-Server antworten auf Clients

Vorteile:
├─→ Primary geschützt vor Angriffen
├─→ Primary nur für Zonentransfer erreichbar
└─→ Vereinfachte Sicherheit

Umsetzung:
├─→ Primary nur intern (127.0.0.1:5353)
└─→ Clients nutzen ausschließlich Secondary
```

### Dynamische DNS (DDNS)

```
DHCP vergibt IP → DHCP aktualisiert DNS automatisch
                → Primary fügt Record hinzu
                → NOTIFY an Secondary
                → Automatische Synchronisation

Nützlich für: Laptops, Smartphones, IoT-Geräte
```

## Architektur-Varianten für Homelab

Die aktuelle Architektur bietet gute Trennung der Komponenten, hat aber bei Failover Einschränkungen.
Hier sind drei Varianten mit unterschiedlichem Redundanz-Level:

### Variante 1: Minimale Redundanz (aktuell implementiert)

```
┌─────────────────┐   ┌─────────────────┐
│ Raspberry Pi    │   │ Proxmox LXC     │
│ 192.168.1.13    │   │ 192.168.1.14    │
│                 │   │                 │
│ AdGuard Home    │   │                 │
│      ↓          │   │                 │
│ Bind9 Primary   │◄─►│ Bind9 Secondary │
│      ↓          │   │ (nur interne    │
│ Unbound         │   │  Domains)       │
└─────────────────┘   └─────────────────┘
```

**Eigenschaften:**
- ✅ Einfach zu warten (wenige Dienste auf LXC)
- ✅ Interne Domains bei Primary-Ausfall verfügbar
- ⚠️ Externe Domains bei Primary-Ausfall nicht verfügbar
- ⚠️ Kein Ad-Blocking bei Primary-Ausfall

**Geeignet für:**
- Homelab mit stabiler Primary-Infrastruktur
- Lernszenario für DNS-Konzepte
- Wenn kurze Ausfälle akzeptabel sind

### Variante 2: Volle Redundanz (empfohlen für produktive Homelab-Services)

```
┌─────────────────┐   ┌─────────────────┐
│ Raspberry Pi    │   │ Proxmox LXC     │
│ 192.168.1.13    │   │ 192.168.1.14    │
│                 │   │                 │
│ AdGuard Home    │   │ AdGuard Home    │
│      ↓          │   │      ↓          │
│ Bind9 Primary   │◄─►│ Bind9 Secondary │
│      ↓          │   │      ↓          │
│ Unbound         │   │ Unbound         │
└─────────────────┘   └─────────────────┘
```

**Eigenschaften:**
- ✅ Vollständige Redundanz für alle Funktionen
- ✅ Ad-Blocking auch bei Primary-Ausfall
- ✅ Externe Domains über beide Server
- ⚠️ Doppelter Wartungsaufwand (2x AdGuard Home konfigurieren)

**Geeignet für:**
- Kritische Homelab-Services (Home Assistant, etc.)
- Produktive Nutzung
- Wenn Hochverfügbarkeit wichtig ist

**Umsetzung:**
```bash
# Auf LXC zusätzlich installieren:
apt install adguardhome unbound

# AdGuard Home auf LXC konfigurieren:
# - Upstream DNS: localhost:5335 (Unbound) für externe
# - Upstream DNS: 192.168.1.13:5353 (Bind9 Primary) für interne
#   (Fallback auf lokale Bind9 Secondary bei Ausfall)
```

### Variante 3: Hybrid-Lösung (Kompromiss)

```
┌─────────────────┐   ┌─────────────────┐
│ Raspberry Pi    │   │ Proxmox LXC     │
│ 192.168.1.13    │   │ 192.168.1.14    │
│                 │   │                 │
│ AdGuard Home    │   │                 │
│      ↓          │   │                 │
│ Bind9 Primary   │◄─►│ Bind9 Secondary │
│      ↓          │   │      ↓          │
│ Unbound         │   │ Unbound         │
└─────────────────┘   └─────────────────┘
```

**Eigenschaften:**
- ✅ Externe Domains bei Primary-Ausfall verfügbar
- ✅ Geringer zusätzlicher Aufwand (nur Unbound)
- ⚠️ Kein Ad-Blocking bei Primary-Ausfall
- ⚠️ Clients müssen Secondary direkt nutzen für externe Domains

**Geeignet für:**
- Wenn externe DNS-Verfügbarkeit wichtiger als Ad-Blocking
- Kompromiss zwischen Komplexität und Redundanz

**Umsetzung:**
```bash
# Auf LXC zusätzlich installieren:
apt install unbound

# Clients konfigurieren mit:
# Primary: 192.168.1.13 (AdGuard Home → alles)
# Secondary: 192.168.1.14 (Bind9 + Unbound → alles ohne Ad-Block)
```

### Migrations-Empfehlung

**Von Variante 1 → Variante 2 (schrittweise):**

1. **Phase 1**: Unbound auf LXC installieren (→ Variante 3)
   ```bash
   # Test: Externe DNS über LXC funktioniert
   dig @192.168.1.14 google.com
   ```

2. **Phase 2**: AdGuard Home auf LXC installieren
   ```bash
   # Installation
   curl -s -S -L https://raw.githubusercontent.com/AdguardTeam/AdGuardHome/master/scripts/install.sh | sh -s -- -v

   # Port ändern zu 5380 (Web-UI) da 3000 evtl. belegt
   # DNS bleibt auf Port 53
   ```

3. **Phase 3**: AdGuard Home auf LXC konfigurieren
   - Upstream DNS: `127.0.0.1:5335` (lokaler Unbound)
   - Custom DNS: `home.sflab.io` → `127.0.0.1:53` (lokaler Bind9 Secondary)
   - Filterlisten von Primary kopieren oder synchronisieren

4. **Phase 4**: Clients aktualisieren
   ```
   Primary DNS:   192.168.1.13 (Pi AdGuard Home)
   Secondary DNS: 192.168.1.14 (LXC AdGuard Home)
   ```

**Rollback:** Einfach alte Client-DNS-Konfiguration wiederherstellen

## Vorteile dieser Architektur

| Kategorie             | Vorteil                                                      |
|-----------------------|--------------------------------------------------------------|
| **Modularität**       | Jede Komponente hat eine klare Rolle                         |
| **Hochverfügbarkeit** | Primary + Secondary mit automatischem Failover               |
| **Datenkonsistenz**   | NOTIFY + IXFR für schnelle, zuverlässige Synchronisation     |
| **Sicherheit**        | Ad-Blocking, lokale Kontrolle, ACLs                          |
| **Performance**       | Mehrschichtiges Caching (AdGuard + Unbound)                  |
| **Privacy**           | Unbound kommuniziert direkt mit Root-Servern                 |
| **Wartbarkeit**       | Zentrale Zonenverwaltung, automatische Replikation           |
| **Flexibilität**      | Drei Varianten je nach Anforderungen (siehe oben)            |

---

*Professionelle DNS-Infrastruktur mit Hochverfügbarkeit, automatischer Synchronisation und klarer Trennung der Zuständigkeiten.*
