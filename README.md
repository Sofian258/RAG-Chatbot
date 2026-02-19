# RAG-Chatbot
Multi-Tenant RAG-Chatbot mit FastAPI, lokalen LLMs (Ollama) und Vektordatenbanken (ChromaDB). Unterstützt TXT, PDF und OCR. Multi-Modell-Routing, intelligente Text-Segmentierung und firmenspezifische Dokumentenverwaltung.



# Multi-Tenant RAG-Chatbot System

Ein intelligenter, firmenspezifischer Chatbot mit RAG (Retrieval-Augmented Generation), der Dokumente verarbeitet und KI-gestützte Antworten generiert.

## Features

- Multi-Tenant-Architektur: Jede Firma hat isolierte Dokumente und Indizes
- RAG-System: Kombiniert semantische Suche mit LLM-Generierung
- Multi-Format-Support: TXT, PDF und Bilder (mit OCR)
- Lokale LLMs: Integration mit Ollama (qwen2.5, llama3.2, mixtral)
- Vektordatenbanken: ChromaDB für semantische Suche
- Intelligente Segmentierung: Automatische Überschriften-Erkennung
- Multi-Modell-Routing: Intelligente Modellauswahl basierend auf Komplexität
- Projekt-Management: API für Projekt-Verwaltung
- Docker-Ready: Vollständig containerisiert

Tech Stack

- Backend: FastAPI, Python 3.11
- AI/ML: Ollama, Sentence Transformers, ChromaDB
- Dokumentenverarbeitung: PyPDF2, Tesseract OCR
- Container: Docker, Docker Compose
- Frontend: Vanilla JavaScript Widget

## Quick Start

docker-compose up -d


##API-Dokumentation
API verfügbar unter: http://localhost:8000
