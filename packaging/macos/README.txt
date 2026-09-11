Digico×Soundscape — macOS (Apple Silicon / arm64)
=================================================

DiGiCo Quantum ↔ d&b DS100 OSC Bridge

Schnellstart
------------
1. Zip entpacken
2. Digico-x-Soundscape.app doppelklicken
3. App-Fenster öffnet die Web-UI (schwarz/grün)
4. IPs / Ports / Mappings setzen → Start
5. Zum Beenden: App-Fenster schließen

Falls macOS "unbekanntes Entwickler"-Warnung zeigt:
  Rechtsklick → Öffnen (einmalig), oder:
  Systemeinstellungen → Datenschutz & Sicherheit → Trotzdem öffnen

Dateien
-------
Digico-x-Soundscape.app   Desktop-App (WebKit-UI + gebündelter Server)
settings.json             Einstellungen (neben der .app ablegen)
README.txt                Diese Datei

Hinweis: Alle Laufzeit-Komponenten sind in der .app enthalten —
kein separates Python nötig.

Netzwerk
--------
- DiGiCo Pad → Bridge IP dieses Macs (in der GUI angezeigt)
- DiGiCo Send/Rcv Ports müssen zu den GUI-Ports passen
- DS100 Ports fest: 50010 (Send), 50011 (Listen)
