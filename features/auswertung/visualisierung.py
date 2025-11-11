"""Visualisierung von Simulationsergebnissen."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
from typing import Optional, List

from features.auswertung.sql_parser import EnergyPlusSQLParser
from features.auswertung.kpi_rechner import GebaeudeKennzahlen


class ErgebnisVisualisierer:
    """Erstellt Visualisierungen von Simulationsergebnissen."""

    # Farben für einheitliches Design
    FARBEN = {
        'heizung': '#FF6B6B',    # Rot
        'kuehlung': '#4ECDC4',   # Türkis
        'beleuchtung': '#FFE66D', # Gelb
        'geraete': '#95E1D3',    # Mintgrün
        'gesamt': '#2C3E50',     # Dunkelgrau
    }

    def erstelle_energiebilanz_chart(
        self,
        kennzahlen: GebaeudeKennzahlen,
        titel: str = "Energiebilanz"
    ) -> go.Figure:
        """Erstelle Tortendiagramm der Energiebilanz.

        Args:
            kennzahlen: Gebäudekennzahlen
            titel: Titel des Diagramms

        Returns:
            Plotly Figure
        """
        labels = ['Heizung', 'Kühlung', 'Beleuchtung', 'Geräte']
        values = [
            kennzahlen.ergebnisse.heizbedarf_kwh,
            kennzahlen.ergebnisse.kuehlbedarf_kwh,
            kennzahlen.ergebnisse.beleuchtung_kwh,
            kennzahlen.ergebnisse.geraete_kwh,
        ]
        colors = [
            self.FARBEN['heizung'],
            self.FARBEN['kuehlung'],
            self.FARBEN['beleuchtung'],
            self.FARBEN['geraete'],
        ]

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textposition='inside',
            hovertemplate='<b>%{label}</b><br>%{value:.0f} kWh<br>%{percent}<extra></extra>'
        )])

        fig.update_layout(
            title=titel,
            showlegend=True,
            height=400,
        )

        return fig

    def erstelle_kennzahlen_balken(
        self,
        kennzahlen: GebaeudeKennzahlen,
        titel: str = "Spezifische Energiekennzahlen"
    ) -> go.Figure:
        """Erstelle Balkendiagramm der Kennzahlen.

        Args:
            kennzahlen: Gebäudekennzahlen
            titel: Titel des Diagramms

        Returns:
            Plotly Figure
        """
        kategorien = ['Gesamt', 'Heizung', 'Kühlung', 'Beleuchtung', 'Geräte']
        werte = [
            kennzahlen.energiekennzahl_kwh_m2a,
            kennzahlen.heizkennzahl_kwh_m2a,
            kennzahlen.kuehlkennzahl_kwh_m2a,
            kennzahlen.ergebnisse.beleuchtung_kwh / kennzahlen.gesamtflaeche_m2,
            kennzahlen.ergebnisse.geraete_kwh / kennzahlen.gesamtflaeche_m2,
        ]
        farben = [
            self.FARBEN['gesamt'],
            self.FARBEN['heizung'],
            self.FARBEN['kuehlung'],
            self.FARBEN['beleuchtung'],
            self.FARBEN['geraete'],
        ]

        fig = go.Figure(data=[go.Bar(
            x=kategorien,
            y=werte,
            marker=dict(color=farben),
            text=[f'{v:.1f}' for v in werte],
            textposition='outside',
        )])

        fig.update_layout(
            title=titel,
            xaxis_title="Kategorie",
            yaxis_title="Energiekennzahl [kWh/m²a]",
            height=400,
            showlegend=False,
        )

        return fig

    def erstelle_monatsuebersicht(
        self,
        sql_file: Path | str,
        titel: str = "Monatliche Energiebilanz"
    ) -> go.Figure:
        """Erstelle gestapeltes Balkendiagramm der monatlichen Energien.

        Args:
            sql_file: Path zur SQL-Datei
            titel: Titel des Diagramms

        Returns:
            Plotly Figure
        """
        with EnergyPlusSQLParser(sql_file) as parser:
            df = parser.get_monthly_summary()

        if df.empty:
            # Leeres Diagramm wenn keine Daten
            fig = go.Figure()
            fig.add_annotation(
                text="Keine monatlichen Daten verfügbar",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig

        fig = go.Figure()

        # Heizung
        fig.add_trace(go.Bar(
            name='Heizung',
            x=df['Monat'],
            y=df['Heizung_kWh'],
            marker_color=self.FARBEN['heizung'],
        ))

        # Kühlung
        fig.add_trace(go.Bar(
            name='Kühlung',
            x=df['Monat'],
            y=df['Kuehlung_kWh'],
            marker_color=self.FARBEN['kuehlung'],
        ))

        # Beleuchtung
        fig.add_trace(go.Bar(
            name='Beleuchtung',
            x=df['Monat'],
            y=df['Beleuchtung_kWh'],
            marker_color=self.FARBEN['beleuchtung'],
        ))

        # Geräte
        fig.add_trace(go.Bar(
            name='Geräte',
            x=df['Monat'],
            y=df['Geraete_kWh'],
            marker_color=self.FARBEN['geraete'],
        ))

        fig.update_layout(
            title=titel,
            xaxis_title="Monat",
            yaxis_title="Energiebedarf [kWh]",
            barmode='stack',
            height=400,
            showlegend=True,
        )

        return fig

    def erstelle_temperaturverlauf(
        self,
        sql_file: Path | str,
        tage: int = 7,
        titel: str = "Raumtemperaturverlauf"
    ) -> go.Figure:
        """Erstelle Liniendiagramm des Temperaturverlaufs.

        Args:
            sql_file: Path zur SQL-Datei
            tage: Anzahl der anzuzeigenden Tage (vom Jahresbeginn)
            titel: Titel des Diagramms

        Returns:
            Plotly Figure
        """
        with EnergyPlusSQLParser(sql_file) as parser:
            df = parser.get_timeseries_data('Zone Mean Air Temperature')

        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="Keine Temperaturdaten verfügbar",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig

        # Limitiere auf die ersten N Tage
        df = df.head(tage * 24)  # Stündliche Daten

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['datetime'],
            y=df['Zone Mean Air Temperature'],
            mode='lines',
            name='Raumtemperatur',
            line=dict(color='#FF6B6B', width=2),
        ))

        # Komfortbereich markieren (20-26°C)
        fig.add_hrect(
            y0=20, y1=26,
            fillcolor='green', opacity=0.1,
            annotation_text="Komfortbereich",
            annotation_position="top right"
        )

        fig.update_layout(
            title=titel,
            xaxis_title="Datum/Zeit",
            yaxis_title="Temperatur [°C]",
            height=400,
            showlegend=True,
        )

        return fig

    def erstelle_dashboard(
        self,
        kennzahlen: GebaeudeKennzahlen,
        sql_file: Path | str
    ) -> go.Figure:
        """Erstelle komplettes Dashboard mit allen Diagrammen.

        Args:
            kennzahlen: Gebäudekennzahlen
            sql_file: Path zur SQL-Datei

        Returns:
            Plotly Figure mit Subplots
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Energiebilanz',
                'Spezifische Kennzahlen',
                'Monatliche Energiebilanz',
                'Raumtemperaturverlauf (7 Tage)'
            ),
            specs=[
                [{'type': 'pie'}, {'type': 'bar'}],
                [{'type': 'bar'}, {'type': 'scatter'}]
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.1,
        )

        # 1. Energiebilanz (Torte)
        labels = ['Heizung', 'Kühlung', 'Beleuchtung', 'Geräte']
        values = [
            kennzahlen.ergebnisse.heizbedarf_kwh,
            kennzahlen.ergebnisse.kuehlbedarf_kwh,
            kennzahlen.ergebnisse.beleuchtung_kwh,
            kennzahlen.ergebnisse.geraete_kwh,
        ]
        colors = [
            self.FARBEN['heizung'],
            self.FARBEN['kuehlung'],
            self.FARBEN['beleuchtung'],
            self.FARBEN['geraete'],
        ]

        fig.add_trace(
            go.Pie(labels=labels, values=values, marker=dict(colors=colors)),
            row=1, col=1
        )

        # 2. Kennzahlen (Balken)
        kategorien = ['Gesamt', 'Heizung', 'Kühlung']
        werte = [
            kennzahlen.energiekennzahl_kwh_m2a,
            kennzahlen.heizkennzahl_kwh_m2a,
            kennzahlen.kuehlkennzahl_kwh_m2a,
        ]

        fig.add_trace(
            go.Bar(x=kategorien, y=werte, marker=dict(color=[self.FARBEN['gesamt'], self.FARBEN['heizung'], self.FARBEN['kuehlung']]), showlegend=False),
            row=1, col=2
        )

        # 3. Monatsuebersicht
        with EnergyPlusSQLParser(sql_file) as parser:
            df_monat = parser.get_monthly_summary()

        if not df_monat.empty:
            fig.add_trace(
                go.Bar(name='Heizung', x=df_monat['Monat'], y=df_monat['Heizung_kWh'], marker_color=self.FARBEN['heizung'], showlegend=False),
                row=2, col=1
            )
            fig.add_trace(
                go.Bar(name='Kühlung', x=df_monat['Monat'], y=df_monat['Kuehlung_kWh'], marker_color=self.FARBEN['kuehlung'], showlegend=False),
                row=2, col=1
            )

        # 4. Temperaturverlauf
        with EnergyPlusSQLParser(sql_file) as parser:
            df_temp = parser.get_timeseries_data('Zone Mean Air Temperature').head(7 * 24)

        if not df_temp.empty:
            fig.add_trace(
                go.Scatter(x=df_temp['datetime'], y=df_temp['Zone Mean Air Temperature'], mode='lines', name='Temperatur', line=dict(color='#FF6B6B'), showlegend=False),
                row=2, col=2
            )

        fig.update_layout(
            title_text=f"Gebäudesimulation Dashboard - Effizienzklasse {kennzahlen.effizienzklasse}",
            height=800,
            showlegend=False,
        )

        fig.update_xaxes(title_text="", row=2, col=1)
        fig.update_yaxes(title_text="Energie [kWh]", row=2, col=1)
        fig.update_xaxes(title_text="", row=2, col=2)
        fig.update_yaxes(title_text="Temperatur [°C]", row=2, col=2)

        return fig
