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
    
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500, use_fallback: bool = False) -> str:
        """
        Generiert Antwort mit lokalem LLM (primäres oder Fallback-Modell)
        
        Args:
            prompt: Prompt für das LLM
            temperature: Kreativität (0.0-1.0, niedrig = konservativer, Standard: 0.3)
            max_tokens: Maximale Anzahl Tokens
            use_fallback: Wenn True, nutze Fallback-Modell statt primäres Modell
        
        Returns:
            Generierte Antwort
        """
        # Stärkere System-Instruktion mit klaren Verboten
        system_instruction = (
            "Du bist ein intelligenter Dokumenten-Assistent. "
            "WICHTIG: Analysiere IMMER gründlich und antworte in EIGENEN WORTEN. "
            "NIEMALS einfach den Dokumententext kopieren oder wiederholen. "
            "Denke nach, bevor du antwortest. Formuliere präzise, fokussierte Antworten. "
            "Nutze NUR Informationen aus den Dokumenten, aber analysiere, berechne und ziehe logische Schlüsse."
        )
        
        full_prompt = f"{system_instruction}\n\n{prompt}"
        model_to_use = self.fallback_model if use_fallback else self.model
        timeout = 10 if use_fallback else 30  # Fallback hat kürzeres Timeout
        
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
