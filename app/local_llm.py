"""Lokaler LLM-Service mit Ollama"""
import requests
import os
from typing import Optional


class LocalLLM:
    """Lokaler LLM-Service über Ollama mit Multi-Modell-Support"""
    
    def __init__(self, base_url: str = None, model: str = None, fallback_model: str = None):
        """
        Initialisiert lokalen LLM-Service mit Fallback-Modell
        
        Args:
            base_url: URL des Ollama-Servers (optional, sonst aus ENV)
            model: Name des primären LLM-Modells (optional, sonst aus ENV)
            fallback_model: Name des Fallback-Modells (optional, sonst aus ENV)
        
        Empfohlene Modelle:
        - Haupt: "qwen2.5:7b" (beste Analyse)
        - Schnell: "qwen2.5:3b" (schnell für einfache Fragen)
        - Fallback: "llama3.2:1b" (sehr schnell bei Timeout)
        """
        self.base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = model or os.getenv("LLM_MODEL", "qwen2.5:7b")
        self.fallback_model = fallback_model or os.getenv("LLM_FALLBACK_MODEL", "llama3.2:1b")
        self._check_ollama()
    
    def _check_ollama(self):
        """Prüft ob Ollama läuft und Modell verfügbar ist"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if self.model in model_names:
                    print(f"✓ Ollama verbunden: {self.base_url}, Modell: {self.model}")
                else:
                    print(f"⚠ Modell '{self.model}' nicht gefunden. Verfügbare Modelle: {model_names}")
                    print(f"  Installiere mit: ollama pull {self.model}")
                    print(f"  Oder im Docker-Container: docker exec -it <container> ollama pull {self.model}")
            else:
                raise ConnectionError("Ollama nicht erreichbar")
        except requests.exceptions.ConnectionError:
            print(f"⚠ Ollama nicht erreichbar unter {self.base_url}")
            print("  Starte Ollama mit: docker run -d -p 11434:11434 ollama/ollama")
            print(f"  Dann: docker exec -it <container> ollama pull {self.model}")
        except Exception as e:
            print(f"⚠ Ollama-Check fehlgeschlagen: {e}")
    
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500, use_fallback: bool = False, timeout: Optional[int] = None, is_planovo: bool = False) -> str:
        """
        Generiert Antwort mit lokalem LLM (primäres oder Fallback-Modell)
        
        Args:
            prompt: Prompt für das LLM
            temperature: Kreativität (0.0-1.0, niedrig = konservativer, Standard: 0.3)
            max_tokens: Maximale Anzahl Tokens
            use_fallback: Wenn True, nutze Fallback-Modell statt primäres Modell
            timeout: Timeout in Sekunden (optional, wird automatisch basierend auf Modell gesetzt)
            is_planovo: Wenn True, nutze Planovo-Support-Stil (ohne Denkprozess)
        
        Returns:
            Generierte Antwort
        """
        # System-Instruktion: Unterschiedlich für Planovo vs. Dev
        if is_planovo:
            # Planovo: KEINE Denk-Anweisungen, nur Support-Stil
            system_instruction = (
                "Du bist Support-Mitarbeiter von Planovo. "
                "Antworte kurz, direkt und verständlich. "
                "Erkläre nicht, wie du auf die Antwort kommst. "
                "Keine Worte wie 'Analysiere', 'Identifizieren', 'Mentale Schritte', keine Quellen. "
                "Wenn Infos fehlen, stell maximal 1-2 Rückfragen."
            )
        else:
            # Dev/Standard: Mit Denk-Anweisungen (für Code-Analyse etc.)
            system_instruction = (
                "Du bist ein intelligenter Dokumenten-Assistent. "
                "WICHTIG: DENKE IMMER Schritt für Schritt nach, bevor du antwortest. "
                "1. Analysiere die Frage gründlich - was wird wirklich gefragt? "
                "2. Finde die relevanten Informationen in den Dokumenten. "
                "3. Verstehe Zusammenhänge und ziehe logische Schlüsse. "
                "4. Formuliere dann eine präzise, zusammenhängende Antwort in EIGENEN WORTEN. "
                "NIEMALS einfach den Dokumententext kopieren oder wiederholen. "
                "Zeige durch deine Antwort, dass du die Informationen verstanden und analysiert hast. "
                "Nutze NUR Informationen aus den Dokumenten, aber analysiere, berechne und erkläre logisch."
            )
        
        full_prompt = f"{system_instruction}\n\n{prompt}"
        model_to_use = self.fallback_model if use_fallback else self.model
        
        # Timeout basierend auf Modell-Größe (große Modelle brauchen mehr Zeit)
        if timeout is None:
            if "8x22b" in model_to_use or "72b" in model_to_use:
                timeout = 300  # 5 Minuten für sehr große Modelle
            elif "32b" in model_to_use:
                timeout = 180  # 3 Minuten für große Modelle
            elif "7b" in model_to_use:
                timeout = 90   # 1.5 Minuten für mittlere Modelle
            elif "3b" in model_to_use:
                timeout = 60   # 1 Minute für kleine Modelle
            elif use_fallback:
                timeout = 60   # 60 Sekunden für Fallback-Modelle (erhöht von 30s)
            else:
                timeout = 60   # 1 Minute Standard
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_to_use,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "stop": ["\n\n\n", "=== KRITISCHE REGELN", "=== ANTWORT-REGELN"]  # Stoppe bei Wiederholungen
                    }
                },
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Ollama nicht erreichbar unter {self.base_url}. Stelle sicher, dass Ollama läuft.")
        except requests.exceptions.Timeout:
            if not use_fallback and self.fallback_model != self.model:
                # Versuche Fallback-Modell bei Timeout
                print(f"⚠ Timeout mit {self.model}, versuche Fallback {self.fallback_model}")
                return self.generate(prompt, temperature, max_tokens, use_fallback=True)
            raise TimeoutError(f"LLM-Request hat zu lange gedauert (>{timeout}s)")
        except Exception as e:
            if not use_fallback and self.fallback_model != self.model:
                # Versuche Fallback-Modell bei Fehler
                print(f"⚠ Fehler mit {self.model}: {e}, versuche Fallback {self.fallback_model}")
                return self.generate(prompt, temperature, max_tokens, use_fallback=True)
            print(f"LLM Error: {e}")
            raise
