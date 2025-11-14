"""Visualisierung von Simulationsergebnissen."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
from typing import Optional, List
import pandas as pd

from features.auswertung.sql_parser import EnergyPlusSQLParser
from features.auswertung.kpi_rechner import GebaeudeKennzahlen, ErweiterteKennzahlen
from features.auswertung.tabular_reports import EndUseSummary, HVACSizing, SiteSourceEnergy, ZonalComparison


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

    def erstelle_detailliertes_end_use_chart(
        self,
        end_uses: EndUseSummary,
        titel: str = "Detaillierte Verbrauchsaufteilung (Tabular Reports)"
    ) -> go.Figure:
        """Erstelle detailliertes End-Use Pie Chart aus Tabular Reports.

        Zeigt eine umfassendere Aufschlüsselung als die Standard-Energiebilanz,
        inkl. Fans, Pumps, und andere Kategorien direkt aus EnergyPlus Reports.

        Args:
            end_uses: EndUseSummary aus TabularReportParser
            titel: Titel des Diagramms

        Returns:
            Plotly Figure
        """
        labels = []
        values = []
        colors = []

        # Mapping für Farben
        color_map = {
            'Heizung': '#FF6B6B',
            'Kühlung': '#4ECDC4',
            'Beleuchtung': '#FFE66D',
            'Geräte': '#95E1D3',
            'Ventilatoren': '#A8E6CF',
            'Pumpen': '#C7CEEA',
            'Sonstiges': '#B0B0B0'
        }

        # Nur nicht-null Werte hinzufügen
        if end_uses.heating_kwh > 0:
            labels.append('Heizung')
            values.append(end_uses.heating_kwh)
            colors.append(color_map['Heizung'])

        if end_uses.cooling_kwh > 0:
            labels.append('Kühlung')
            values.append(end_uses.cooling_kwh)
            colors.append(color_map['Kühlung'])

        if end_uses.interior_lighting_kwh > 0:
            labels.append('Beleuchtung')
            values.append(end_uses.interior_lighting_kwh)
            colors.append(color_map['Beleuchtung'])

        if end_uses.interior_equipment_kwh > 0:
            labels.append('Geräte')
            values.append(end_uses.interior_equipment_kwh)
            colors.append(color_map['Geräte'])

        if end_uses.fans_kwh > 0:
            labels.append('Ventilatoren')
            values.append(end_uses.fans_kwh)
            colors.append(color_map['Ventilatoren'])

        if end_uses.pumps_kwh > 0:
            labels.append('Pumpen')
            values.append(end_uses.pumps_kwh)
            colors.append(color_map['Pumpen'])

        # Sonstiges berechnen
        other = end_uses.other_kwh
        if other > 0:
            labels.append('Sonstiges')
            values.append(other)
            colors.append(color_map['Sonstiges'])

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textposition='inside',
            hovertemplate='<b>%{label}</b><br>%{value:.0f} kWh<br>%{percent}<extra></extra>'
        )])

        fig.update_layout(
            title=dict(
                text=f"{titel}<br><sub>Gesamt: {end_uses.total_kwh:.0f} kWh | "
                     f"Strom: {end_uses.electricity_kwh:.0f} kWh | "
                     f"Gas: {end_uses.natural_gas_kwh:.0f} kWh</sub>",
                x=0.5,
                xanchor='center'
            ),
            showlegend=True,
            height=500,
        )

        return fig

    def erstelle_hvac_design_loads_chart(
        self,
        hvac_sizing: HVACSizing,
        nettoflaeche_m2: float,
        titel: str = "HVAC Auslegungslasten"
    ) -> go.Figure:
        """Erstelle Balkendiagramm der HVAC Design-Lasten.

        Args:
            hvac_sizing: HVACSizing aus TabularReportParser
            nettoflaeche_m2: Nettofläche für spezifische Werte
            titel: Titel des Diagramms

        Returns:
            Plotly Figure
        """
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Absolute Lasten [kW]", "Spezifische Lasten [W/m²]"),
            horizontal_spacing=0.15
        )

        # Absolute Lasten
        fig.add_trace(
            go.Bar(
                x=['Heizlast', 'Kühllast'],
                y=[hvac_sizing.heating_design_load_kw, hvac_sizing.cooling_design_load_kw],
                marker=dict(color=['#FF6B6B', '#4ECDC4']),
                text=[f'{hvac_sizing.heating_design_load_kw:.1f} kW',
                      f'{hvac_sizing.cooling_design_load_kw:.1f} kW'],
                textposition='outside',
                showlegend=False
            ),
            row=1, col=1
        )

        # Spezifische Lasten
        fig.add_trace(
            go.Bar(
                x=['Heizlast', 'Kühllast'],
                y=[hvac_sizing.heating_design_load_per_area_w_m2,
                   hvac_sizing.cooling_design_load_per_area_w_m2],
                marker=dict(color=['#FF6B6B', '#4ECDC4']),
                text=[f'{hvac_sizing.heating_design_load_per_area_w_m2:.1f} W/m²',
                      f'{hvac_sizing.cooling_design_load_per_area_w_m2:.1f} W/m²'],
                textposition='outside',
                showlegend=False
            ),
            row=1, col=2
        )

        fig.update_layout(
            title=dict(
                text=f"{titel}<br><sub>Heiz-Auslegungstag: {hvac_sizing.heating_design_day} | "
                     f"Kühl-Auslegungstag: {hvac_sizing.cooling_design_day}</sub>",
                x=0.5,
                xanchor='center'
            ),
            height=400,
            showlegend=False
        )

        fig.update_yaxes(title_text="Last [kW]", row=1, col=1)
        fig.update_yaxes(title_text="Last [W/m²]", row=1, col=2)

        return fig

    def erstelle_site_source_energy_chart(
        self,
        site_source: SiteSourceEnergy,
        titel: str = "Site vs. Source Energy (Primärenergie)"
    ) -> go.Figure:
        """Erstelle Vergleichschart für Site und Source Energy.

        Args:
            site_source: SiteSourceEnergy aus TabularReportParser
            titel: Titel des Diagramms

        Returns:
            Plotly Figure
        """
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("Gesamtenergie [kWh/a]", "Spezifisch [kWh/m²a]"),
            horizontal_spacing=0.15
        )

        # Absolute Werte
        fig.add_trace(
            go.Bar(
                x=['Site Energy', 'Source Energy'],
                y=[site_source.total_site_energy_kwh, site_source.total_source_energy_kwh],
                marker=dict(color=['#95E1D3', '#FF6B6B']),
                text=[f'{site_source.total_site_energy_kwh:.0f} kWh',
                      f'{site_source.total_source_energy_kwh:.0f} kWh'],
                textposition='outside',
                showlegend=False
            ),
            row=1, col=1
        )

        # Spezifische Werte
        fig.add_trace(
            go.Bar(
                x=['Site Energy', 'Source Energy'],
                y=[site_source.site_energy_per_m2_kwh,
                   site_source.total_source_energy_kwh / (site_source.site_energy_per_m2_kwh / site_source.site_energy_per_m2_kwh) if site_source.site_energy_per_m2_kwh > 0 else 0],
                marker=dict(color=['#95E1D3', '#FF6B6B']),
                text=[f'{site_source.site_energy_per_m2_kwh:.1f} kWh/m²a',
                      f'{site_source.source_energy_per_m2_mj / 3.6:.1f} kWh/m²a'],
                textposition='outside',
                showlegend=False
            ),
            row=1, col=2
        )

        fig.update_layout(
            title=titel,
            height=400,
            showlegend=False
        )

        fig.update_yaxes(title_text="Energie [kWh/a]", row=1, col=1)
        fig.update_yaxes(title_text="Energie [kWh/m²a]", row=1, col=2)

        return fig

    def erstelle_erweiterte_uebersicht(
        self,
        erweiterte_kennzahlen: ErweiterteKennzahlen,
        sql_file: Path | str
    ) -> go.Figure:
        """Erstelle erweiterte Übersicht mit Tabular Reports.

        Args:
            erweiterte_kennzahlen: ErweiterteKennzahlen mit Tabular Data
            sql_file: Path zur SQL-Datei

        Returns:
            Plotly Figure mit erweitertem Dashboard
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Detaillierte Verbrauchsaufteilung',
                'HVAC Design-Lasten',
                'Site vs. Source Energy',
                'Monatliche Energiebilanz'
            ),
            specs=[
                [{'type': 'pie'}, {'type': 'bar'}],
                [{'type': 'bar'}, {'type': 'bar'}]
            ],
            vertical_spacing=0.15,
            horizontal_spacing=0.12,
        )

        kennzahlen = erweiterte_kennzahlen.basis_kennzahlen
        end_uses = erweiterte_kennzahlen.end_uses
        hvac_sizing = erweiterte_kennzahlen.hvac_sizing
        site_source = erweiterte_kennzahlen.site_source_energy

        # 1. Detaillierte End Uses (Pie)
        if end_uses:
            labels = ['Heizung', 'Kühlung', 'Beleuchtung', 'Geräte']
            values = [end_uses.heating_kwh, end_uses.cooling_kwh,
                     end_uses.interior_lighting_kwh, end_uses.interior_equipment_kwh]
            colors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3']

            if end_uses.fans_kwh > 0:
                labels.append('Ventilatoren')
                values.append(end_uses.fans_kwh)
                colors.append('#A8E6CF')

            if end_uses.pumps_kwh > 0:
                labels.append('Pumpen')
                values.append(end_uses.pumps_kwh)
                colors.append('#C7CEEA')

            fig.add_trace(
                go.Pie(labels=labels, values=values, marker=dict(colors=colors), showlegend=False),
                row=1, col=1
            )

        # 2. HVAC Design Loads
        if hvac_sizing:
            fig.add_trace(
                go.Bar(
                    x=['Heizlast', 'Kühllast'],
                    y=[hvac_sizing.heating_design_load_kw, hvac_sizing.cooling_design_load_kw],
                    marker=dict(color=['#FF6B6B', '#4ECDC4']),
                    text=[f'{hvac_sizing.heating_design_load_kw:.1f} kW',
                          f'{hvac_sizing.cooling_design_load_kw:.1f} kW'],
                    textposition='outside',
                    showlegend=False
                ),
                row=1, col=2
            )

        # 3. Site vs Source Energy
        if site_source:
            fig.add_trace(
                go.Bar(
                    x=['Site Energy', 'Source Energy'],
                    y=[site_source.total_site_energy_kwh, site_source.total_source_energy_kwh],
                    marker=dict(color=['#95E1D3', '#FF6B6B']),
                    text=[f'{site_source.total_site_energy_kwh:.0f} kWh',
                          f'{site_source.total_source_energy_kwh:.0f} kWh'],
                    textposition='outside',
                    showlegend=False
                ),
                row=2, col=1
            )

        # 4. Monatsuebersicht
        with EnergyPlusSQLParser(sql_file) as parser:
            df_monat = parser.get_monthly_summary()

        if not df_monat.empty:
            fig.add_trace(
                go.Bar(name='Heizung', x=df_monat['Monat'], y=df_monat['Heizung_kWh'],
                      marker_color='#FF6B6B', showlegend=False),
                row=2, col=2
            )
            fig.add_trace(
                go.Bar(name='Kühlung', x=df_monat['Monat'], y=df_monat['Kuehlung_kWh'],
                      marker_color='#4ECDC4', showlegend=False),
                row=2, col=2
            )

        fig.update_layout(
            title_text=f"Erweiterte Simulation (Tabular Reports) - Effizienzklasse {kennzahlen.effizienzklasse}",
            height=800,
            showlegend=False,
        )

        fig.update_yaxes(title_text="Last [kW]", row=1, col=2)
        fig.update_yaxes(title_text="Energie [kWh]", row=2, col=1)
        fig.update_yaxes(title_text="Energie [kWh]", row=2, col=2)

        return fig

    def erstelle_zonalen_vergleich(
        self,
        zonal: ZonalComparison,
        titel: str = "Zonaler Vergleich: Nord/Ost/Süd/West/Kern"
    ) -> go.Figure:
        """
        Erstellt 4-Subplot Dashboard für zonalen Vergleich.

        Args:
            zonal: ZonalComparison Objekt
            titel: Titel des Dashboards

        Returns:
            Plotly Figure mit 4 Subplots
        """
        # Sortiere Zonen nach Orientierung
        orientations = ['North', 'East', 'South', 'West', 'Core']
        zones_sorted = []
        for orientation in orientations:
            for zone in zonal.zones.values():
                if zone.orientation == orientation:
                    zones_sorted.append(zone)
                    break

        if not zones_sorted:
            # Fallback: Leeres Chart
            fig = go.Figure()
            fig.add_annotation(
                text="Keine zonalen Daten verfügbar",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16)
            )
            return fig

        zone_names = [z.orientation for z in zones_sorted]
        colors_by_orientation = {
            'North': '#3498db',  # Blau (kalt)
            'East': '#e74c3c',   # Rot (Morgensonne)
            'South': '#f39c12',  # Orange (viel Sonne)
            'West': '#e67e22',   # Dunkles Orange (Abendsonne)
            'Core': '#95a5a6'    # Grau (keine Sonne)
        }

        # Erstelle 2x2 Subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Durchschnittstemperaturen',
                'Solare Gewinne (Orientierungseffekt!)',
                'Innere Gewinne',
                'Heiz-/Kühllasten'
            ),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )

        # 1. Temperaturen
        temps_avg = [z.avg_temperature_c for z in zones_sorted]
        temps_min = [z.min_temperature_c for z in zones_sorted]
        temps_max = [z.max_temperature_c for z in zones_sorted]

        fig.add_trace(
            go.Bar(
                name='Ø Temperatur',
                x=zone_names,
                y=temps_avg,
                marker_color=[colors_by_orientation[z] for z in zone_names],
                text=[f"{t:.1f}°C" for t in temps_avg],
                textposition='auto',
            ),
            row=1, col=1
        )

        # 2. Solare Gewinne (zeigt Orientierungseffekt!)
        solar_gains = [z.solar_gains_kwh for z in zones_sorted]
        fig.add_trace(
            go.Bar(
                name='Solare Gewinne',
                x=zone_names,
                y=solar_gains,
                marker_color=[colors_by_orientation[z] for z in zone_names],
                text=[f"{s:.0f} kWh" for s in solar_gains],
                textposition='auto',
            ),
            row=1, col=2
        )

        # 3. Innere Gewinne
        internal_gains = [z.internal_gains_kwh for z in zones_sorted]
        fig.add_trace(
            go.Bar(
                name='Innere Gewinne',
                x=zone_names,
                y=internal_gains,
                marker_color=[colors_by_orientation[z] for z in zone_names],
                text=[f"{i:.0f} kWh" for i in internal_gains],
                textposition='auto',
            ),
            row=2, col=1
        )

        # 4. Heiz-/Kühllasten (Grouped Bar)
        heating_loads = [z.heating_kwh for z in zones_sorted]
        cooling_loads = [z.cooling_kwh for z in zones_sorted]

        fig.add_trace(
            go.Bar(
                name='Heizlast',
                x=zone_names,
                y=heating_loads,
                marker_color='#FF6B6B',
                text=[f"{h:.0f}" for h in heating_loads],
                textposition='auto',
            ),
            row=2, col=2
        )
        fig.add_trace(
            go.Bar(
                name='Kühllast',
                x=zone_names,
                y=cooling_loads,
                marker_color='#4ECDC4',
                text=[f"{c:.0f}" for c in cooling_loads],
                textposition='auto',
            ),
            row=2, col=2
        )

        # Layout
        fig.update_layout(
            title_text=titel,
            height=800,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        # Y-Achsen Beschriftungen
        fig.update_yaxes(title_text="Temperatur [°C]", row=1, col=1)
        fig.update_yaxes(title_text="Energie [kWh]", row=1, col=2)
        fig.update_yaxes(title_text="Energie [kWh]", row=2, col=1)
        fig.update_yaxes(title_text="Energie [kWh]", row=2, col=2)

        return fig

    def erstelle_zonale_solar_gewinne_chart(
        self,
        zonal: ZonalComparison
    ) -> go.Figure:
        """
        Erstellt detaillierten Chart für solare Gewinne (Orientierungseffekt).

        Args:
            zonal: ZonalComparison Objekt

        Returns:
            Plotly Figure (Bar Chart)
        """
        # Nur Perimeter-Zonen (nicht Kern)
        perimeter_zones = [z for z in zonal.zones.values() if z.orientation != 'Core']

        if not perimeter_zones:
            fig = go.Figure()
            fig.add_annotation(
                text="Keine Perimeter-Zonen verfügbar",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig

        # Sortiere nach solaren Gewinnen (absteigend)
        perimeter_zones.sort(key=lambda z: z.solar_gains_kwh, reverse=True)

        zone_names = [z.orientation for z in perimeter_zones]
        solar_gains = [z.solar_gains_kwh for z in perimeter_zones]

        colors = {
            'North': '#3498db',
            'East': '#e74c3c',
            'South': '#f39c12',
            'West': '#e67e22'
        }

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=zone_names,
                y=solar_gains,
                marker_color=[colors[z] for z in zone_names],
                text=[f"{s:.1f} kWh" for s in solar_gains],
                textposition='auto',
            )
        )

        fig.update_layout(
            title="Solare Gewinne nach Orientierung (Perimeter-Zonen)",
            xaxis_title="Orientierung",
            yaxis_title="Solare Gewinne [kWh/a]",
            height=400,
            showlegend=False
        )

        return fig
