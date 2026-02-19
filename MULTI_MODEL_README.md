# Multi-Modell LLM Support

Das System unterstützt jetzt mehrere Open-Source-LLMs gleichzeitig mit intelligenter Modell-Auswahl.

## Features

- **Intelligentes Routing**: Automatische Auswahl des passenden Modells basierend auf Komplexität
- **Parallel-Nutzung**: Mehrere Modelle können gleichzeitig verwendet werden
- **Austauschbarkeit**: Modelle können ohne Code-Änderung ausgetauscht werden
- **Fallback-Strategien**: Automatisches Fallback bei Modell-Fehlern
- **Konfigurierbar**: Modelle über Config-Datei oder Umgebungsvariablen

## Modell-Konfiguration

### Über Config-Datei (empfohlen)

Erstellen Sie eine `llm_config.json` Datei im Projekt-Root:

```json
{
  "fast": {
    "model": "qwen2.5:3b",
    "fallback": "llama3.2:1b",
    "max_tokens": 150,
    "temperature": 0.1,
    "timeout": 10,
    "description": "Schnelles Modell für einfache Fragen"
  },
  "standard": {
    "model": "qwen2.5:7b",
    "fallback": "llama3.2:1b",
    "max_tokens": 400,
    "temperature": 0.2,
    "timeout": 30,
    "description": "Standard-Modell für normale Fragen"
  },
  "reasoning": {
    "model": "qwen2.5:32b",
    "fallback": "qwen2.5:7b",
    "max_tokens": 600,
    "temperature": 0.3,
    "timeout": 60,
    "description": "Reasoning-Modell für komplexe Fragen"
  }
}
```

### Über Umgebungsvariablen

```bash
# Fast Modell
LLM_MODEL_FAST=qwen2.5:3b
LLM_FALLBACK_MODEL=llama3.2:1b

# Standard Modell
LLM_MODEL=qwen2.5:7b

# Reasoning Modell
LLM_MODEL_REASONING=qwen2.5:32b

# Router aktivieren/deaktivieren
USE_LLM_ROUTER=true

# Config-Datei (optional)
LLM_CONFIG_PATH=llm_config.json
```

## Routing-Logik

Das System wählt automatisch das passende Modell basierend auf:

1. **Frage-Länge**: Längere Fragen → komplexeres Modell
2. **Reasoning-Keywords**: "warum", "weshalb", "erkläre" → Reasoning-Modell
3. **Anzahl Kontext-Chunks**: Mehr Chunks → komplexeres Modell
4. **Kontext-Länge**: Längerer Kontext → komplexeres Modell
5. **Relevance Score (RSQ)**: Niedrige Relevanz → mehr Reasoning nötig

### Komplexitäts-Schwellenwerte

- **< 0.3**: Fast Modell (qwen2.5:3b)
- **0.3 - 0.7**: Standard Modell (qwen2.5:7b)
- **> 0.7**: Reasoning Modell (qwen2.5:32b / Mixtral 8x22B / Qwen 72B)

## Unterstützte Modelle

### Aktuell getestet:
- **qwen2.5:3b** - Schnell, ressourcen-sparend
- **qwen2.5:7b** - Gute Balance
- **llama3.2:1b** - Sehr schnell, Fallback

### Geplant (benötigen mehr GPU-Speicher):
- **qwen2.5:14b** - Light Reasoning
- **qwen2.5:32b** - Strong Reasoning
- **qwen2.5:72b** - High-End Reasoning
- **mixtral:8x7b** - Mid-Reasoning
- **mixtral:8x22b** - High-End Reasoning

## Installation neuer Modelle

```bash
# Im Docker-Container
docker exec -it chatbotproject-ollama-1 ollama pull qwen2.5:32b

# Oder lokal
ollama pull qwen2.5:32b
```

## Aktivierung

Der Router ist standardmäßig aktiviert. Um ihn zu deaktivieren:

```bash
USE_LLM_ROUTER=false
```

## Monitoring

Die Logs zeigen, welches Modell verwendet wird:

```
📊 Komplexität: 0.45 → Modell: standard (qwen2.5:7b)
🧠 Nutze Multi-Modell Router für intelligente Modell-Auswahl
```

## Flexibilität

- **Hardware**: Läuft auf jedem System mit Docker/Ollama
- **Deployment**: On-Prem, Bare Metal, Cloud - kein Code-Change nötig
- **Skalierung**: Neue Modelle können einfach hinzugefügt werden
- **Vendor-Lock-in**: Kein - alle Modelle sind Open-Source
- **Cloud-Zwang**: Kein - alles läuft lokal
