"""Multi-Modell LLM Router für intelligente Modell-Auswahl"""
import os
import json
from typing import Optional, Dict, List
from pathlib import Path
from app.local_llm import LocalLLM


class LLMRouter:
    """
    Router für Multi-Modell LLM Support
    
    Unterstützt:
    - Intelligente Modell-Auswahl basierend auf Komplexität
    - Parallel-Nutzung mehrerer Modelle
    - Dynamisches Laden/Austauschen von Modellen
    - Fallback-Strategien
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialisiert LLM Router mit Modell-Konfiguration
        
        Args:
            config_path: Pfad zur Modell-Konfigurationsdatei (optional)
        """
        self.config_path = config_path or os.getenv("LLM_CONFIG_PATH", "llm_config.json")
        self.models: Dict[str, LocalLLM] = {}
        self.model_configs: Dict = {}
        self._load_config()
        self._initialize_models()
    
    def _load_config(self):
        """Lädt Modell-Konfiguration aus Datei oder Umgebungsvariablen"""
        # Versuche Config-Datei zu laden
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.model_configs = json.load(f)
                print(f"✓ Modell-Konfiguration geladen: {self.config_path}")
                return
            except Exception as e:
                print(f"⚠ Fehler beim Laden der Config: {e}, nutze Standard-Konfiguration")
        
        # Fallback: Standard-Konfiguration
        self.model_configs = {
            "fast": {
                "model": os.getenv("LLM_MODEL_FAST", "qwen2.5:3b"),
                "fallback": os.getenv("LLM_FALLBACK_MODEL", "llama3.2:1b"),
                "max_tokens": 150,
                "temperature": 0.1,
                "timeout": 10,
                "description": "Schnelles Modell für einfache Fragen"
            },
            "standard": {
                "model": os.getenv("LLM_MODEL", "qwen2.5:7b"),
                "fallback": os.getenv("LLM_FALLBACK_MODEL", "llama3.2:1b"),
                "max_tokens": 400,
                "temperature": 0.2,
                "timeout": 30,
                "description": "Standard-Modell für normale Fragen"
            },
            "reasoning": {
                "model": os.getenv("LLM_MODEL_REASONING", "qwen2.5:7b"),  # Fallback zu Standard wenn nicht verfügbar
                "fallback": os.getenv("LLM_MODEL", "qwen2.5:7b"),
                "max_tokens": 600,
                "temperature": 0.3,
                "timeout": 60,
                "description": "Reasoning-Modell für komplexe Fragen"
            }
        }
        print("✓ Standard-Modell-Konfiguration verwendet")
    
    def _initialize_models(self):
        """Initialisiert LLM-Instanzen für alle konfigurierten Modelle"""
        ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        
        for model_type, config in self.model_configs.items():
            try:
                llm = LocalLLM(
                    base_url=ollama_url,
                    model=config["model"],
                    fallback_model=config.get("fallback")
                )
                self.models[model_type] = llm
                print(f"✓ {model_type} Modell initialisiert: {config['model']}")
            except Exception as e:
                print(f"⚠ Fehler beim Initialisieren von {model_type}: {e}")
                # Erstelle trotzdem eine Instanz für Fallback
                self.models[model_type] = None
    
    def calculate_complexity(self, query: str, context_chunks: List[Dict], rsq: float) -> float:
        """
        Berechnet Komplexitäts-Score für Modell-Auswahl
        
        Args:
            query: Benutzerfrage
            context_chunks: Liste relevanter Dokumenten-Abschnitte
            rsq: Relevance Score Quality (0.0 - 1.0)
        
        Returns:
            Komplexitäts-Score (0.0 - 1.0)
        """
        complexity = 0.0
        query_lower = query.lower()
        
        # 1. Frage-Länge (längere Fragen = komplexer)
        query_length = len(query.split())
        if query_length > 15:
            complexity += 0.2
        elif query_length > 8:
            complexity += 0.1
        
        # 2. Komplexe Fragewörter
        reasoning_keywords = ["warum", "weshalb", "wieso", "wie funktioniert", "erkläre", "analysiere", 
                            "vergleiche", "unterschied", "zusammenhang", "begründ", "schlussfolger"]
        if any(kw in query_lower for kw in reasoning_keywords):
            complexity += 0.3
        
        # 3. Anzahl Kontext-Chunks (mehr Kontext = komplexer)
        num_chunks = len(context_chunks)
        if num_chunks > 3:
            complexity += 0.2
        elif num_chunks > 1:
            complexity += 0.1
        
        # 4. Kontext-Länge
        total_context_length = sum(len(chunk.get("text", "")) for chunk in context_chunks)
        if total_context_length > 2000:
            complexity += 0.2
        elif total_context_length > 1000:
            complexity += 0.1
        
        # 5. RSQ (niedrige Relevanz = komplexer, da mehr Reasoning nötig)
        if rsq < 0.3:
            complexity += 0.2
        elif rsq < 0.5:
            complexity += 0.1
        
        # 6. Mehrteilige Fragen
        if " und " in query_lower or " sowie " in query_lower or " oder " in query_lower:
            complexity += 0.1
        
        return min(complexity, 1.0)  # Max 1.0
    
    def route(self, query: str, context_chunks: List[Dict], rsq: float) -> tuple[LocalLLM, Dict]:
        """
        Routet Anfrage zum passenden Modell
        
        Args:
            query: Benutzerfrage
            context_chunks: Relevante Dokumenten-Abschnitte
            rsq: Relevance Score Quality
        
        Returns:
            Tuple (LLM-Instanz, Modell-Konfiguration)
        """
        complexity = self.calculate_complexity(query, context_chunks, rsq)
        
        # Routing-Entscheidung
        if complexity < 0.3:
            # Einfache Frage → Fast Modell
            model_type = "fast"
        elif complexity < 0.7:
            # Normale Frage → Standard Modell
            model_type = "standard"
        else:
            # Komplexe Reasoning-Frage → Reasoning Modell
            model_type = "reasoning"
        
        # Hole Modell und Config
        llm = self.models.get(model_type)
        config = self.model_configs.get(model_type, {})
        
        # Fallback wenn Modell nicht verfügbar
        if llm is None:
            print(f"⚠ {model_type} Modell nicht verfügbar, nutze Fallback")
            # Versuche Standard-Modell
            llm = self.models.get("standard")
            config = self.model_configs.get("standard", {})
            if llm is None:
                # Letzter Fallback: Fast Modell
                llm = self.models.get("fast")
                config = self.model_configs.get("fast", {})
        
        print(f"📊 Komplexität: {complexity:.2f} → Modell: {model_type} ({config.get('model', 'unknown')})")
        
        return llm, config
    
    def generate(self, query: str, context_chunks: List[Dict], rsq: float, prompt: str, is_planovo: bool = False) -> str:
        """
        Generiert Antwort mit automatischer Modell-Auswahl
        
        Args:
            query: Benutzerfrage
            context_chunks: Relevante Dokumenten-Abschnitte
            rsq: Relevance Score Quality
            prompt: Vollständiger Prompt für das LLM
            is_planovo: Wenn True, nutze Planovo-Support-Stil (ohne Denkprozess)
        
        Returns:
            Generierte Antwort
        """
        llm, config = self.route(query, context_chunks, rsq)
        
        if llm is None:
            raise RuntimeError("Kein LLM-Modell verfügbar")
        
        try:
            # Nutze Timeout aus Config
            config_timeout = config.get("timeout", None)
            answer = llm.generate(
                prompt,
                temperature=config.get("temperature", 0.2),
                max_tokens=config.get("max_tokens", 400),
                use_fallback=False,
                timeout=config_timeout,
                is_planovo=is_planovo  # NEU: Durchreichen an LocalLLM
            )
            return answer
        except Exception as e:
            print(f"⚠ Fehler mit {config.get('model')}: {e}")
            # Versuche Fallback-Modell
            if config.get("fallback") and config.get("fallback") != config.get("model"):
                try:
                    fallback_llm = LocalLLM(
                        base_url=os.getenv("OLLAMA_URL", "http://ollama:11434"),
                        model=config["fallback"]
                    )
                    print(f"🔄 Nutze Fallback-Modell: {config['fallback']}")
                    # Für Fallback: Nutze mindestens 60s Timeout (aber nicht mehr als ursprünglich)
                    if config_timeout:
                        fallback_timeout = max(int(config_timeout * 0.7), 60)  # Mindestens 60s, aber 70% des ursprünglichen
                    else:
                        fallback_timeout = 60  # Standard 60s für Fallback
                    return fallback_llm.generate(
                        prompt,
                        temperature=config.get("temperature", 0.2),
                        max_tokens=config.get("max_tokens", 400),
                        use_fallback=True,
                        timeout=fallback_timeout,
                        is_planovo=is_planovo  # NEU: Auch für Fallback
                    )
                except Exception as e2:
                    print(f"✗ Fallback fehlgeschlagen: {e2}")
                    raise
            raise
    
    def list_available_models(self) -> Dict[str, bool]:
        """Listet verfügbare Modelle und ihren Status"""
        available = {}
        for model_type, llm in self.models.items():
            if llm:
                try:
                    # Prüfe ob Modell verfügbar ist
                    llm._check_ollama()
                    available[model_type] = True
                except:
                    available[model_type] = False
            else:
                available[model_type] = False
        return available
    
    def reload_config(self):
        """Lädt Modell-Konfiguration neu (für dynamisches Nachladen)"""
        self._load_config()
        self._initialize_models()
        print("✓ Modell-Konfiguration neu geladen")
