"""Project Manager für Verwaltung von Projekten"""
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import json
import uuid


class ProjectManager:
    """Verwaltet Projekte mit Team-Informationen"""
    
    def __init__(self, storage_dir: str = "projects"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.projects: Dict[str, dict] = {}  # project_id -> project_data
        self._load_projects()
    
    def _load_projects(self):
        """Lädt gespeicherte Projekte"""
        projects_file = self.storage_dir / "projects.json"
        if projects_file.exists():
            try:
                with open(projects_file, "r", encoding="utf-8") as f:
                    self.projects = json.load(f)
                print(f"✓ {len(self.projects)} Projekte geladen")
            except Exception as e:
                print(f"Fehler beim Laden der Projekte: {e}")
                self.projects = {}
    
    def _save_projects(self):
        """Speichert Projekte"""
        projects_file = self.storage_dir / "projects.json"
        try:
            with open(projects_file, "w", encoding="utf-8") as f:
                json.dump(self.projects, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der Projekte: {e}")
    
    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        team_type: Optional[str] = None,
        company_id: Optional[str] = None,
        status: str = "active"
    ) -> dict:
        """
        Erstellt ein neues Projekt
        
        Args:
            name: Projektname (Pflichtfeld)
            description: Projektbeschreibung (optional)
            team_type: Team-Typ ("Techniker", "Entwickler" oder None)
            company_id: Verknüpfung zu einer Firma (optional)
            status: Projektstatus (default: "active")
        
        Returns:
            Dict mit Projekt-Daten
        """
        # Generiere eindeutige Projekt-ID
        project_id = str(uuid.uuid4())[:8]  # Kurze ID für bessere Lesbarkeit
        
        project_data = {
            "project_id": project_id,
            "name": name,
            "description": description,
            "team_type": team_type,
            "company_id": company_id,
            "status": status,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.projects[project_id] = project_data
        self._save_projects()
        
        print(f"✓ Projekt '{name}' erstellt (ID: {project_id})")
        return project_data
    
    def get_project(self, project_id: str) -> Optional[dict]:
        """Holt Projekt nach ID"""
        return self.projects.get(project_id)
    
    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        team_type: Optional[str] = None,
        company_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[dict]:
        """Aktualisiert Projekt-Daten"""
        if project_id not in self.projects:
            return None
        
        project = self.projects[project_id]
        
        # Aktualisiere nur übergebene Felder
        if name is not None:
            project["name"] = name
        if description is not None:
            project["description"] = description
        if team_type is not None:
            project["team_type"] = team_type
        if company_id is not None:
            project["company_id"] = company_id
        if status is not None:
            project["status"] = status
        
        project["updated_at"] = datetime.utcnow().isoformat()
        self._save_projects()
        
        return project
    
    def delete_project(self, project_id: str) -> bool:
        """Löscht Projekt"""
        if project_id in self.projects:
            del self.projects[project_id]
            self._save_projects()
            return True
        return False
    
    def list_projects(
        self,
        company_id: Optional[str] = None,
        team_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[dict]:
        """Listet Projekte mit optionalen Filtern"""
        projects = list(self.projects.values())
        
        # Filter anwenden
        if company_id:
            projects = [p for p in projects if p.get("company_id") == company_id]
        if team_type:
            projects = [p for p in projects if p.get("team_type") == team_type]
        if status:
            projects = [p for p in projects if p.get("status") == status]
        
        # Sortiere nach Erstellungsdatum (neueste zuerst)
        projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return projects
    
    def project_exists(self, project_id: str) -> bool:
        """Prüft ob Projekt existiert"""
        return project_id in self.projects
