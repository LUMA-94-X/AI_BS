"""Materials und Constructions Generator.

Erstellt Material-Definitionen und Konstruktionen (Wandaufbauten, Dächer, etc.)
basierend auf U-Werten aus dem Energieausweis.
"""

from typing import Any

from core.materialien import add_basic_constructions


class MaterialsGenerator:
    """Generiert Materialien und Konstruktionen für EnergyPlus IDFs.

    Aktuell: Verwendet Standard-Konstruktionen aus core.materialien
    Zukünftig: U-Wert-basierte Konstruktions-Generierung

    Roadmap:
        - Phase 1 (aktuell): Wrapper um add_basic_constructions()
        - Phase 2: U-Wert → Dämmstoffdicke Berechnung
        - Phase 3: Vollständiger Konstruktions-Generator aus Energieausweis-Daten
    """

    def add_constructions_from_u_values(
        self,
        idf: Any,
        ea_data: Any  # EnergieausweisInput
    ) -> None:
        """Erstellt Konstruktionen basierend auf U-Werten.

        Args:
            idf: eppy IDF-Objekt
            ea_data: EnergieausweisInput mit U-Werten

        Note:
            Aktuell wird add_basic_constructions() verwendet (Standard-Materialien).
            Die U-Werte aus ea_data werden noch NICHT verwendet, das ist für
            zukünftige Sprints geplant.

        Future Implementation:
            ```python
            self._create_construction_from_u_value(idf, "Wall", ea_data.u_wert_wand)
            self._create_construction_from_u_value(idf, "Roof", ea_data.u_wert_dach)
            self._create_construction_from_u_value(idf, "Floor", ea_data.u_wert_boden)
            self._create_window_construction(idf, ea_data.u_wert_fenster)
            ```
        """
        # Für jetzt: Standard-Konstruktionen
        add_basic_constructions(idf)

        # TODO Sprint 4+: U-Wert-basierte Konstruktionen
        # - Berechne Dämmstoffdicke aus Ziel-U-Wert
        # - Erstelle Material-Layer
        # - Validiere thermische Eigenschaften

    def _create_construction_from_u_value(
        self,
        idf: Any,
        component_type: str,
        u_value: float
    ) -> str:
        """Erstellt Konstruktion aus Ziel-U-Wert (zukünftige Implementierung).

        Args:
            idf: eppy IDF-Objekt
            component_type: Typ: "Wall", "Roof", "Floor"
            u_value: Ziel-U-Wert in W/m²K

        Returns:
            Name der erstellten Construction

        Algorithm (geplant):
            1. Wähle Basis-Aufbau (z.B. Außenputz, Mauerwerk, Dämmung, Innenputz)
            2. Berechne erforderliche Dämmstoffdicke für Ziel-U-Wert
            3. Erstelle MATERIAL-Objekte für alle Layer
            4. Erstelle CONSTRUCTION mit korrekter Layer-Reihenfolge
            5. Validiere: Berechne U-Wert und prüfe gegen Ziel

        References:
            - DIN EN ISO 6946: Berechnung des Wärmedurchgangskoeffizienten
            - EnergyPlus Engineering Reference: Material Properties
        """
        raise NotImplementedError(
            "U-value-based construction generation not yet implemented. "
            "See issue #X for roadmap."
        )

    def _create_window_construction(
        self,
        idf: Any,
        u_value: float,
        shgc: float = 0.7
    ) -> str:
        """Erstellt Fenster-Konstruktion (zukünftige Implementierung).

        Args:
            idf: eppy IDF-Objekt
            u_value: U-Wert in W/m²K
            shgc: Solar Heat Gain Coefficient (g-Wert)

        Returns:
            Name der erstellten WindowMaterial:SimpleGlazingSystem

        Note:
            SimpleGlazingSystem ist einfacher als CONSTRUCTION:WINDOWDATAGRID,
            aber ausreichend für Energieausweis-Berechnungen.
        """
        raise NotImplementedError(
            "Window construction generation not yet implemented."
        )

    def get_available_constructions(self, idf: Any) -> dict:
        """Listet alle verfügbaren Konstruktionen im IDF auf.

        Args:
            idf: eppy IDF-Objekt

        Returns:
            Dictionary: {construction_type: [construction_names]}
        """
        constructions = {
            'walls': [],
            'roofs': [],
            'floors': [],
            'windows': []
        }

        # Parse CONSTRUCTION objects
        for const in idf.idfobjects.get('CONSTRUCTION', []):
            name = const.Name.lower()
            if 'wall' in name:
                constructions['walls'].append(const.Name)
            elif 'roof' in name:
                constructions['roofs'].append(const.Name)
            elif 'floor' in name or 'ground' in name:
                constructions['floors'].append(const.Name)

        # Parse WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM
        for window in idf.idfobjects.get('WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM', []):
            constructions['windows'].append(window.Name)

        return constructions
