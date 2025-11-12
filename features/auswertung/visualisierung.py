"""Visualisierung von Simulationsergebnissen."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
from typing import Optional, List
import pandas as pd

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

    def erstelle_interaktive_temperaturkurve(
        self,
        sql_file: Path | str,
        start_tag: int = 1,
        anzahl_tage: int = 7,
        titel: str = "Raumtemperaturverlauf"
    ) -> go.Figure:
        """Erstelle interaktive Temperaturkurve mit voller Kontrolle.

        Args:
            sql_file: Path zur SQL-Datei
            start_tag: Startag des Jahres (1-365)
            anzahl_tage: Anzahl der anzuzeigenden Tage
            titel: Titel des Diagramms

        Returns:
            Plotly Figure mit interaktiver Temperaturkurve
        """
        with EnergyPlusSQLParser(sql_file) as parser:
            df = parser.get_timeseries_data('Zone Mean Air Temperature')

        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="Keine Temperaturdaten verfügbar",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16)
            )
            return fig

        # Berechne Start- und End-Index
        start_hour = (start_tag - 1) * 24
        end_hour = start_hour + (anzahl_tage * 24)

        # Limitiere auf den gewählten Zeitraum
        df_slice = df.iloc[start_hour:end_hour]

        if df_slice.empty:
            fig = go.Figure()
            fig.add_annotation(
                text=f"Keine Daten für Tag {start_tag}-{start_tag + anzahl_tage}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16)
            )
            return fig

        fig = go.Figure()

        # Haupttemperaturkurve
        fig.add_trace(go.Scatter(
            x=df_slice['datetime'],
            y=df_slice['Zone Mean Air Temperature'],
            mode='lines',
            name='Raumtemperatur',
            line=dict(color='#FF6B6B', width=2.5),
            hovertemplate='<b>%{x}</b><br>Temperatur: %{y:.1f}°C<extra></extra>'
        ))

        # Komfortbereich markieren (20-26°C)
        fig.add_hrect(
            y0=20, y1=26,
            fillcolor='green', opacity=0.1,
            line_width=0,
            annotation_text="Komfortbereich (20-26°C)",
            annotation_position="top right",
            annotation=dict(font_size=10, font_color="green")
        )

        # Heiz-Grenze (< 20°C)
        fig.add_hline(
            y=20,
            line_dash="dash",
            line_color="orange",
            annotation_text="Heiz-Solltemperatur",
            annotation_position="right",
            annotation=dict(font_size=9, font_color="orange")
        )

        # Kühl-Grenze (> 26°C)
        fig.add_hline(
            y=26,
            line_dash="dash",
            line_color="blue",
            annotation_text="Kühl-Solltemperatur",
            annotation_position="right",
            annotation=dict(font_size=9, font_color="blue")
        )

        # Statistiken im Zeitraum
        temp_min = df_slice['Zone Mean Air Temperature'].min()
        temp_max = df_slice['Zone Mean Air Temperature'].max()
        temp_mean = df_slice['Zone Mean Air Temperature'].mean()

        fig.update_layout(
            title=dict(
                text=f"{titel}<br><sub>Tag {start_tag} bis {start_tag + anzahl_tage - 1} des Jahres | "
                     f"Ø {temp_mean:.1f}°C | Min {temp_min:.1f}°C | Max {temp_max:.1f}°C</sub>",
                x=0.5,
                xanchor='center'
            ),
            xaxis_title="Datum/Zeit",
            yaxis_title="Temperatur [°C]",
            height=500,
            showlegend=True,
            hovermode='x unified',
            plot_bgcolor='rgba(240, 240, 240, 0.5)',
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(200, 200, 200, 0.3)'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(200, 200, 200, 0.3)',
                range=[temp_min - 2, temp_max + 2]  # Etwas Padding
            )
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
                'Raumtemperaturverlauf (Jahresübersicht)'
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

        # 4. Temperaturverlauf (Jahresübersicht mit täglichen Durchschnittswerten)
        with EnergyPlusSQLParser(sql_file) as parser:
            df_temp = parser.get_timeseries_data('Zone Mean Air Temperature')

        if not df_temp.empty:
            # Aggregiere auf Tagesbasis für bessere Lesbarkeit im Dashboard
            df_temp['date'] = df_temp['datetime'].dt.date
            df_temp_daily = df_temp.groupby('date')['Zone Mean Air Temperature'].mean().reset_index()
            df_temp_daily['datetime'] = pd.to_datetime(df_temp_daily['date'])

            # Komfortbereich als gefüllter Bereich (vor der Temperaturkurve)
            fig.add_trace(
                go.Scatter(
                    x=df_temp_daily['datetime'].tolist() + df_temp_daily['datetime'].tolist()[::-1],
                    y=[20]*len(df_temp_daily) + [26]*len(df_temp_daily),
                    fill='toself',
                    fillcolor='rgba(0, 255, 0, 0.1)',
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo='skip'
                ),
                row=2, col=2
            )

            # Temperaturkurve
            fig.add_trace(
                go.Scatter(
                    x=df_temp_daily['datetime'],
                    y=df_temp_daily['Zone Mean Air Temperature'],
                    mode='lines',
                    name='Temperatur',
                    line=dict(color='#FF6B6B', width=1.5),
                    showlegend=False
                ),
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
