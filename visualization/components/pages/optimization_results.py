"""
Optimization results visualization page
"""
import streamlit as st
from typing import Optional

from core.instance_manager import InstanceManager
from core.data_models import OptimizationSolution, InstanceMetadata
from components.sidebar import StatusIndicator, MetricsDisplay
from visualizations.investment_analysis import InvestmentAnalysis
from visualizations.technology_mix import TechnologyMix
from config.translations import get_technology_translation

class OptimizationResultsPage:
    """Page for visualizing optimization results"""
    
    def __init__(self, instance_manager: InstanceManager):
        self.instance_manager = instance_manager
        self.investment_viz = InvestmentAnalysis()
        self.technology_viz = TechnologyMix()
    
    def _is_debugging_model(self, solution: OptimizationSolution) -> bool:
        """
        Detect if the solution comes from the debugging model by checking for 
        debugging-specific variables that are not present in the compact model.
        
        Returns:
            bool: True if debugging model variables are found, False otherwise
        """
        # List of variable patterns that are unique to the debugging model
        debugging_variable_patterns = [
            'yearly_rental_income_',
            'credit_repayment_',
            'credit_interest_',
            'credit_payment_',
            'pre_credit_payment_',
            'bonus_costs_',
            'total_investment_measures_',
            'subsidies_',  # Added subsidies variable
            'total_investment_measures_building_',  # Building-specific investment measures
            'subsidies_building_',  # Building-specific subsidies
            'CO2_costs_',  # CO2 costs variable
            'CO2_costs_building_'  # Building-specific CO2 costs
        ]
        
        # Check if any debugging-specific variables exist in the solution
        for var_name in solution.variables.keys():
            for pattern in debugging_variable_patterns:
                if pattern in var_name:
                    return True
        
        return False
    
    def render(self, selected_instance: Optional[InstanceMetadata] = None):
        """Render the optimization results page"""
        
        st.header("→ Optimierungsergebnisse")
        
        if not selected_instance:
            st.warning("Bitte wählen Sie eine Instanz aus der Seitenleiste, um die Ergebnisse anzuzeigen.")
            return
        
        if not selected_instance.has_solution:
            st.error(f"Keine Lösung verfügbar für die Instanz '{selected_instance.name}'")
            st.info("Bitte stellen Sie sicher, dass die Optimierung für diese Instanz durchgeführt wurde.")
            return

        #Load instance metadata
        instance_data = self.instance_manager.load_instance_from_pickle(selected_instance.name)

        # Load solution
        with st.spinner("Lade Optimierungslösung..."):
            solution = self.instance_manager.load_instance_solution(selected_instance)
        
        if not solution:
            st.error("Fehler beim Laden der Lösungsdaten")
            return
        
        # Display solution status and key metrics
        st.subheader(f"Ergebnisse für: {selected_instance.name}")
        
        # Status indicator
        StatusIndicator.render_solution_status(
            selected_instance.has_solution, 
            solution.solution_status
        )
        
        st.markdown("---")
        
        # Visualization tabs - conditional based on advanced view
        if st.session_state.get('advanced_view', False):
            tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "Zielfunktion",
                "Finanzen",
                "Portfolio-Analyse", 
                "Gebäude-Analyse",
                "Rohdaten",
                "Erweiterte Analysen"
            ])
        else:
            tab0, tab1, tab2, tab3 = st.tabs([
                "Zielfunktion",
                "Finanzübersicht",
                "Portfolio-Analyse", 
                "Gebäude-Analyse"
            ])
        
        with tab0:
            self._render_objective_tab(solution)
        
        with tab1:
            self.investment_viz.render(solution, instance_data=instance_data)

            # Debugging Model Specific Financial Analysis
            if self._is_debugging_model(solution):
                st.markdown("---")
                
                # Yearly Rental Income
                st.subheader("Jährliche Mieteinnahmen des Gebäudeportfolios")
                self._render_yearly_rental_income_chart(solution)
                st.markdown("---")

                # Credit Analysis
                st.subheader("Bestandskredite, neue Kredite sowie zugehörige Zins- und Tilgungszahlungen")
                self._render_credit_analysis_chart(solution)
                st.markdown("---")

                # Investment Analysis
                st.subheader("Gesamtinvestitionsmaßnahmen, CO2-Kosten sowie Bonuserträge")
                self._render_investment_analysis_chart(solution)
                st.markdown("---")

                # Total Subsidies
                st.subheader("Gesamtförderung des Gebäudeportfolios")
                self._render_subsidies_chart(solution)
        
        with tab2:
            self.technology_viz.render(solution, instance_data=instance_data)

        with tab3:
            self._render_building_pathway(solution, instance_data)
            
        # Advanced tabs only shown when advanced view is enabled
        if st.session_state.get('advanced_view', False):
            with tab4:
                self._render_raw_data(solution)
                
            with tab5:
                self._render_advanced_analytics(solution)
    
    def _render_advanced_analytics(self, solution: OptimizationSolution):
        """Render advanced analytics and in-depth analysis of the solution"""
        
        st.subheader("Erweiterte Analysen")
        
        if not solution.variables:
            st.warning("Keine Variablen in der Lösung gefunden")
            return
            
        st.info("Diese Funktion bietet zusätzliche Analysen und Einblicke in die Optimierungslösung.")
        
        # Add sections for advanced analytics here
        st.subheader("Sensitivitätsanalyse")
        st.write("Detaillierte Analyse der Empfindlichkeit der Lösung gegenüber Änderungen der Eingabeparameter.")
        # Placeholder for sensitivity analysis
        
        st.subheader("Zeitreihenanalyse")
        st.write("Analyse der zeitlichen Entwicklung von Schlüsselvariablen.")
        # Placeholder for time series analysis
        
    def _render_raw_data(self, solution: OptimizationSolution):
        """Render raw solution data"""
        
        st.subheader("Rohe Lösungsdaten")
        
        if not solution.variables:
            st.warning("Keine Variablen in der Lösung gefunden")
            return
        
        # Variable type filter
        variable_types = sorted(set(var.variable_type for var in solution.variables.values()))
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            selected_types = st.multiselect(
                "Filter by variable type:",
                variable_types,
                default=variable_types[:3] if len(variable_types) > 3 else variable_types
            )
            
            show_zeros = st.checkbox("Show zero values", value=False)
        
        with col1:
            if selected_types:
                # Filter variables
                filtered_vars = {}
                for name, var in solution.variables.items():
                    if var.variable_type in selected_types:
                        if show_zeros or var.value != 0:
                            filtered_vars[name] = var
                
                if filtered_vars:
                    # Create dataframe for display
                    import pandas as pd
                    
                    data = []
                    for name, var in filtered_vars.items():
                        data.append({
                            'Variable': name,
                            'Type': var.variable_type,
                            'Value': var.value,
                            'Building': var.building_id or 'N/A',
                            'Time Period': var.time_period if var.time_period is not None else 'N/A',
                            'Technology': var.technology or 'N/A',
                            'Category': var.category or 'N/A'
                        })
                    
                    df = pd.DataFrame(data)
                    
                    # Sort by value (descending) and then by variable name
                    df = df.sort_values(['Value', 'Variable'], ascending=[False, True])
                    
                    st.dataframe(df, hide_index=True, use_container_width=True)
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Als CSV herunterladen",
                        data=csv,
                        file_name=f"{solution.solution_status}_variables.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Keine Variablen entsprechen den ausgewählten Filtern")
            else:
                st.info("Bitte wählen Sie Variablentypen zur Anzeige aus")
    
    def _render_solution_summary(self, solution: OptimizationSolution):
        """Render solution summary and statistics"""
        
        st.subheader("Lösungszusammenfassung")
        
        # Get summary from parser
        from core.solution_parser import SolutionParser
        parser = SolutionParser()
        summary = parser.get_solution_summary(solution)
        
        # Basic solution info
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("→ Optimierungsergebnisse")
            st.metric("Zielfunktionswert", f"{summary['objective_value']:,.0f} k€")
            st.metric("Lösungsstatus", summary['solution_status'])
            st.metric("Gesamtanzahl Variablen", f"{summary['total_variables']:,}")
        
        with col2:
            st.subheader("🏢 Problemumfang")
            st.metric("Gebäude", len(summary['buildings']))
            st.metric("Jahre", len(summary['time_periods']))
            
            if summary['buildings']:
                st.write("**Gebäude-IDs:**", ", ".join(summary['buildings']))
            if summary['time_periods']:
                st.write("**Jahre:**", ", ".join(map(str, summary['time_periods'])))
        
        # Variable type breakdown
        if summary['variable_types']:
            st.subheader("Verteilung der Variablentypen")
            
            import plotly.express as px
            import pandas as pd
            
            var_type_df = pd.DataFrame(
                list(summary['variable_types'].items()),
                columns=['Variable Type', 'Count']
            )
            
            fig = px.bar(
                var_type_df,
                x='Variable Type',
                y='Count',
                title="Variablen nach Typ",
                color='Variable Type'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Technology installation summary
        if summary['installed_technologies']:
            st.subheader("🔧 Installierte Technologien nach Kategorie")
            
            tech_df = pd.DataFrame(
                list(summary['installed_technologies'].items()),
                columns=['Category', 'Installations']
            )
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.pie(
                    tech_df,
                    values='Installations',
                    names='Category',
                    title="Verteilung der Technologieinstallationen"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.dataframe(tech_df, hide_index=True)
        
        # Export summary
        st.subheader("📥 Exportoptionen")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Zusammenfassung als JSON exportieren"):
                import json
                summary_json = json.dumps(summary, indent=2, default=str)
                st.download_button(
                    label="JSON herunterladen",
                    data=summary_json,
                    file_name="solution_summary.json",
                    mime="application/json"
                )
        
            if st.button("Diagramme exportieren"):
                st.info("Funktion zum Exportieren von Diagrammen kommt in Kürze!")
                
            if st.button("Vollständige Daten exportieren"):
                st.info("Funktion zum Exportieren vollständiger Daten kommt in Kürze!")
    
    def _render_building_pathway(self, solution: OptimizationSolution, instance_data):
        """Render building pathway analysis"""
        
        st.subheader("Gebäude-Analyse: Modernisierungspfad")
        st.markdown("Analyse von Technologiepfaden und Maßnahmen an der Gebäudehülle für einzelne Gebäude.")

        # Extract buildings from solution data
        buildings = self._extract_buildings_from_solution(solution)
        
        if not buildings:
            st.warning("Keine Gebäudedaten in der Lösung gefunden")
            return
        
        # Building selection dropdown
        col1, col2 = st.columns([1, 2])
        
        with col1:
            selected_building = st.selectbox(
                "Gebäude-Wahl:",
                buildings,
                format_func=lambda x: f"Gebäude {x}",
                key="building_selector"
            )
        
        # Add some space before the info box
        st.markdown("<div style='height: 5px'></div>", unsafe_allow_html=True)
        
        # Display info box below the dropdown instead of in the second column
        if selected_building is not None:
            st.info(f"Analyse des Modernisierungspfads für Gebäude {selected_building}")
        
        st.markdown("---")
        
        # Building pathway content (placeholder for now)
        if selected_building is not None:
            self._render_building_pathway_content(solution, selected_building, instance_data)
    
    def _extract_buildings_from_solution(self, solution: OptimizationSolution):
        """Extract unique building IDs from solution variables"""
        import re
        
        buildings = set()
        
        # Look for building IDs in variable names
        for var_name in solution.variables.keys():
            # Try to extract building ID from various variable name patterns
            patterns = [
                r'X_(?:in|out)_(\d+)_',  # X_in_1_2_tech or X_out_1_2_tech
                r'E_(\d+)_',             # E_1_2_tech
                r'_(\d+)_\d+_',          # Any pattern with building_timeperiod
            ]
            
            for pattern in patterns:
                match = re.search(pattern, var_name)
                if match:
                    try:
                        building_id = int(match.group(1))
                        buildings.add(building_id)
                        break
                    except (ValueError, IndexError):
                        continue
        
        return sorted(list(buildings))
    
    def _render_building_pathway_content(self, solution: OptimizationSolution, building_id: int, instance_data):
        """Render the actual building pathway content"""
                
        # Installed Capacity Section - Show E_av variables over time
        st.subheader("Installierte Kapazitäten über die Zeit")
        self._render_installed_capacity_chart(solution, building_id)

        st.markdown("---")
    
        # Building Envelope Components Section - Show X_av variables for roof, wall, win
        st.subheader("Maßnahmen an der Gebäudehülle: Auswahl der Gebäudehüllekomponenten")
        self._render_envelope_components_chart(solution, building_id)
        
        st.markdown("---")

        # Financials Section - Rent and Energy Costs over Time
        st.subheader("Finanzen - Kaltmiete, Energiekosten und CO2-Kosten")
        
        # Extract rent and energy cost data for the selected building
        rent_data = self._extract_rent_data(solution, building_id)
        energy_data = self._extract_energy_cost_data(solution, building_id)
        
        # Extract CO2 costs for debugging model
        co2_costs_data = {}
        if self._is_debugging_model(solution):
            co2_costs_data = self._extract_co2_costs_building_data(solution, building_id, instance_data)
        
        if rent_data or energy_data or co2_costs_data:
            # Get all time periods from all datasets
            all_time_periods = set()
            if rent_data:
                all_time_periods.update(rent_data.keys())
            if energy_data:
                all_time_periods.update(energy_data.keys())
            if co2_costs_data:
                all_time_periods.update(co2_costs_data.keys())
            
            time_periods = sorted(all_time_periods)
            
            # Create combined plot
            import plotly.graph_objects as go
            
            fig = go.Figure()
            
            # Add rent trace if data exists
            if rent_data:
                rent_values = [rent_data.get(tp, 0) for tp in time_periods]
                fig.add_trace(go.Scatter(
                    x=time_periods,
                    y=rent_values,
                    mode='lines+markers',
                    name='Kaltmiete',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=8)
                ))
            
            # Add energy cost trace if data exists
            if energy_data:
                energy_values = [energy_data.get(tp, 0) for tp in time_periods]
                fig.add_trace(go.Scatter(
                    x=time_periods,
                    y=energy_values,
                    mode='lines+markers',
                    name='Energiekosten',
                    line=dict(color='#ff7f0e', width=3),
                    marker=dict(size=8)
                ))
            
            # Add CO2 costs trace if data exists (debugging model only)
            if co2_costs_data:
                co2_values = [co2_costs_data.get(tp, 0) for tp in time_periods]
                fig.add_trace(go.Scatter(
                    x=time_periods,
                    y=co2_values,
                    mode='lines+markers',
                    name='CO2-Kosten',
                    line=dict(color='#ff0000', width=3),  # Red color
                    marker=dict(size=8)
                ))
            
            fig.update_layout(
                title=f"Gebäude {building_id}",
                xaxis_title="Jahr",
                yaxis_title="Wert in €",
                yaxis=dict(rangemode='tozero'),  # Ensure y-axis starts at 0
                height=400,
                showlegend=True,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.warning(f"Keine finanziellen Daten für Gebäude {building_id} gefunden")

        st.markdown("---")

        # Depreciation Costs Section
        st.subheader("Abschreibungskosten über die Zeit")
        self._render_depreciation_costs_chart(solution, building_id)

        st.markdown("---")


        # Modernization Costs Section (C_mod and C_mod_heat)
        st.subheader("Modernisierungsumlagen durch Modernisierungsmaßnahmen")
        self._render_cmod_costs_chart(solution, building_id)

        # Building-specific debugging plots (only shown for debugging model)
        if self._is_debugging_model(solution):
            # Investment Measures Building Section
            st.subheader("Investitionsmaßnahmen: Installations-, Deinstallations- und Wartungskosten")
            self._render_investment_measures_building_chart(solution, building_id)
            
            # Subsidies Building Section  
            st.subheader("Förderungen für Modernisierungsmaßnahmen")
            self._render_subsidies_building_chart(solution, building_id)


    def _render_installed_capacity_chart(self, solution: OptimizationSolution, building_id: int):
        """Render installed capacity chart showing E_av variables over time as stacked bars"""
        import re
        import plotly.graph_objects as go
        import pandas as pd

        # Extract E_av data for the specific building
        capacity_data = {}

        # Look for E_av variables for the specific building
        for var_name, var in solution.variables.items():
            # Pattern: E_av_{building_id}_{time_period}_{technology}
            pattern = rf'E_av_{building_id}_(\d+)_(.+)'
            match = re.match(pattern, var_name)

            if match and var.value is not None and var.value > 0:
                try:
                    time_period = int(match.group(1))
                    technology = match.group(2)

                    if time_period not in capacity_data:
                        capacity_data[time_period] = {}

                    # Convert from W to kW for all technologies except PV (which is already in kW)
                    if technology.startswith('pv'):
                        capacity_data[time_period][technology] = var.value  # PV already in kW
                    else:
                        capacity_data[time_period][technology] = var.value / 1000.0  # Convert from W to kW
                except (ValueError, IndexError):
                    continue

        if not capacity_data:
            st.warning(f"Keine installierten Kapazitätsdaten (E_av-Variablen) für Gebäude {building_id} gefunden")
            return

        # Get all time periods and technologies
        time_periods = sorted(capacity_data.keys())
        all_technologies = set()
        for tp_data in capacity_data.values():
            all_technologies.update(tp_data.keys())
        technologies = sorted(all_technologies)

        # Define color palette for technologies
        color_palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
        ]

        # Create stacked bar chart
        fig = go.Figure()

        for i, technology in enumerate(technologies):
            values = []
            for tp in time_periods:
                values.append(capacity_data.get(tp, {}).get(technology, 0))
                
            # Get translated technology name
            tech_name_translated = get_technology_translation(technology)

            fig.add_trace(go.Bar(
                x=time_periods,
                y=values,
                name=tech_name_translated,
                marker_color=color_palette[i % len(color_palette)],
                hovertemplate=f'<b>{tech_name_translated}</b><br>' +
                             'Jahr: %{x}<br>' +
                             'Kapazität: %{y:.2f}<br>' +
                             '<extra></extra>'
            ))

        fig.update_layout(
            title=f"Gebäude {building_id}",
            xaxis_title="Jahr",
            yaxis_title="Installierte Kapazität (kW)",
            barmode='stack',
            height=400,
            showlegend=True,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        st.plotly_chart(fig, use_container_width=True)


    def _render_envelope_components_chart(self, solution: OptimizationSolution, building_id: int):
        """Render building envelope components chart showing X_av variables for roof, wall, win components"""
        import re
        import plotly.graph_objects as go
        import pandas as pd

        # Extract X_av data for building envelope components (roof, wall, win)
        envelope_data = {}

        # Look for X_av variables for the specific building and envelope components
        for var_name, var in solution.variables.items():
            # Pattern: X_av_{building_id}_{time_period}_{component}_{number}
            # where component is one of: roof, wall, win
            pattern = rf'X_av_{building_id}_(\d+)_(roof|wall|win)_(\d+)'
            match = re.match(pattern, var_name)

            if match and var.value is not None and var.value == 1:  # Only binary vars with value 1
                try:
                    time_period = int(match.group(1))
                    component_type = match.group(2)
                    component_number = int(match.group(3))

                    if time_period not in envelope_data:
                        envelope_data[time_period] = {}

                    if component_type not in envelope_data[time_period]:
                        envelope_data[time_period][component_type] = []

                    envelope_data[time_period][component_type].append(component_number)
                except (ValueError, IndexError):
                    continue

        if not envelope_data:
            st.warning(f"Keine Daten zu Gebäudehüllenkomponenten (X_av-Variablen für Dach/Wand/Fenster) für Gebäude {building_id} gefunden")
            return

        # Get all time periods
        time_periods = sorted(envelope_data.keys())
        component_types = ['roof', 'wall', 'win']

        # Create subplot layout for the three component types
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Dach: Sanierungszustand', 'Wand: Sanierungszustand', 'Fenster: Sanierungszustand'),
            vertical_spacing=0.08,
            shared_xaxes=True
        )

        # Define colors for different component numbers
        colors = {
            1: '#1f77b4',  # Blue
            2: '#ff7f0e',  # Orange
            3: '#2ca02c'   # Green
        }

        # Process each component type
        for row_idx, component_type in enumerate(component_types, 1):
            # Get all possible component numbers for this type
            all_numbers = set()
            for tp_data in envelope_data.values():
                if component_type in tp_data:
                    all_numbers.update(tp_data[component_type])

            if all_numbers:
                for number in sorted(all_numbers):
                    # Create binary data for this component number
                    y_values = []
                    for tp in time_periods:
                        if (tp in envelope_data and
                            component_type in envelope_data[tp] and
                            number in envelope_data[tp][component_type]):
                            y_values.append(number)
                        else:
                            y_values.append(None)

                    # Add scatter trace for active periods
                    active_periods = [tp for tp, val in zip(time_periods, y_values) if val is not None]
                    active_values = [val for val in y_values if val is not None]

                    # German component type names for display
                    component_display_names = {
                        'roof': 'Dach',
                        'wall': 'Wand',
                        'win': 'Fenster'
                    }
                    
                    display_name = component_display_names.get(component_type, component_type.title())
                    
                    if active_periods:
                        fig.add_trace(
                            go.Scatter(
                                x=active_periods,
                                y=active_values,
                                mode='markers+lines',
                                name=f'{display_name} {number}',
                                marker=dict(
                                    color=colors.get(number, '#17becf'),
                                    size=12,
                                    symbol='circle'
                                ),
                                line=dict(
                                    color=colors.get(number, '#17becf'),
                                    width=3,
                                    dash='solid'
                                ),
                                hovertemplate=f'<b>{display_name} {number}</b><br>' +
                                            'Jahr: %{x}<br>' +
                                            'Klasse: %{y}<br>' +
                                            '<extra></extra>',
                                showlegend=(row_idx == 1)  # Only show legend for first subplot
                            ),
                            row=row_idx, col=1
                        )

        # Update layout
        fig.update_layout(
            title=f"Gebäude {building_id}",
            height=600,
            showlegend=False,  # Hide legend as requested
            hovermode='closest'
        )

        # Update x-axes
        fig.update_xaxes(title_text="Jahr", row=3, col=1)

        # Update y-axes with German titles
        component_type_titles = {
            'roof': 'Dachklasse',
            'wall': 'Wandklasse',
            'win': 'Fensterklasse'
        }
        
        for row_idx, component_type in enumerate(component_types, 1):
            fig.update_yaxes(
                title_text=component_type_titles.get(component_type, f"{component_type.title()} Type"),
                row=row_idx, col=1,
                tickmode='linear',
                tick0=1,
                dtick=1,
                range=[0.5, 3.5]
            )

        st.plotly_chart(fig, use_container_width=True)

        

    def _extract_rent_data(self, solution: OptimizationSolution, building_id: int):
        """Extract rent data for a specific building from solution variables"""
        import re
        
        rent_data = {}
        
        # Look for C_rent variables for the specific building
        for var_name, var in solution.variables.items():
            # Pattern: C_rent_{building_id}_{time_period}
            pattern = rf'C_rent_{building_id}_(\d+)'
            match = re.match(pattern, var_name)
            
            if match and var.value is not None:
                try:
                    time_period = int(match.group(1))
                    rent_data[time_period] = var.value
                except (ValueError, IndexError):
                    continue
        
        return rent_data
    
    def _extract_energy_cost_data(self, solution: OptimizationSolution, building_id: int):
        """Extract energy cost data for a specific building from solution variables"""
        import re
        
        energy_data = {}
        
        # Look for C_en variables for the specific building
        for var_name, var in solution.variables.items():
            # Pattern: C_en_{building_id}_{time_period}
            pattern = rf'C_en_{building_id}_(\d+)'
            match = re.match(pattern, var_name)
            
            if match and var.value is not None:
                try:
                    time_period = int(match.group(1))
                    energy_data[time_period] = var.value
                except (ValueError, IndexError):
                    continue
        
        return energy_data
    
    def _extract_cmod_data(self, solution: OptimizationSolution, building_id: int):
        """Extract C_mod and C_mod_heat data for a specific building from solution variables"""
        import re
        
        cmod_data = {}
        cmod_heat_data = {}
        
        # Look for C_mod and C_mod_heat variables for the specific building
        for var_name, var in solution.variables.items():
            # Pattern: C_mod_{building_id}_{time_period}
            cmod_pattern = rf'C_mod_{building_id}_(\d+)'
            cmod_match = re.match(cmod_pattern, var_name)
            
            # Pattern: C_mod_heat_{building_id}_{time_period}  
            cmod_heat_pattern = rf'C_mod_heat_{building_id}_(\d+)'
            cmod_heat_match = re.match(cmod_heat_pattern, var_name)
            
            if cmod_match and var.value is not None:
                try:
                    time_period = int(cmod_match.group(1))
                    cmod_data[time_period] = var.value
                except (ValueError, IndexError):
                    continue
            elif cmod_heat_match and var.value is not None:
                try:
                    time_period = int(cmod_heat_match.group(1))
                    cmod_heat_data[time_period] = var.value
                except (ValueError, IndexError):
                    continue
        
        return {
            'cmod': cmod_data,
            'cmod_heat': cmod_heat_data
        }
    
    def _extract_yearly_rental_income_data(self, solution: OptimizationSolution):
        """Extract yearly rental income data for debugging model analysis"""
        import re
        
        rental_income_data = {}
        
        # Look for yearly_rental_income variables (these are time-period specific)
        for var_name, var in solution.variables.items():
            # Pattern: yearly_rental_income_{time_period}
            pattern = rf'yearly_rental_income_(\d+)'
            match = re.match(pattern, var_name)
            
            if match and var.value is not None:
                try:
                    time_period = int(match.group(1))
                    rental_income_data[time_period] = var.value
                except (ValueError, IndexError):
                    continue
        
        return rental_income_data
    
    def _extract_credit_analysis_data(self, solution: OptimizationSolution):
        """Extract credit-related variables for debugging model analysis"""
        import re
        
        credit_data = {
            'credit_repayment': {},
            'credit_interest': {},
            'credit_payment': {},
            'pre_credit_payment': {}
        }
        
        # Extract all credit-related variables
        for var_name, var in solution.variables.items():
            if var.value is not None:
                # Pattern: credit_repayment_{time_period}
                repayment_match = re.match(rf'credit_repayment_(\d+)', var_name)
                if repayment_match:
                    try:
                        time_period = int(repayment_match.group(1))
                        credit_data['credit_repayment'][time_period] = var.value
                    except (ValueError, IndexError):
                        continue
                
                # Pattern: credit_interest_{time_period}
                interest_match = re.match(rf'credit_interest_(\d+)', var_name)
                if interest_match:
                    try:
                        time_period = int(interest_match.group(1))
                        credit_data['credit_interest'][time_period] = var.value
                    except (ValueError, IndexError):
                        continue
                
                # Pattern: credit_payment_{time_period}
                payment_match = re.match(rf'credit_payment_(\d+)', var_name)
                if payment_match:
                    try:
                        time_period = int(payment_match.group(1))
                        credit_data['credit_payment'][time_period] = var.value
                    except (ValueError, IndexError):
                        continue
                
                # Pattern: pre_credit_payment_{time_period}
                pre_payment_match = re.match(rf'pre_credit_payment_(\d+)', var_name)
                if pre_payment_match:
                    try:
                        time_period = int(pre_payment_match.group(1))
                        credit_data['pre_credit_payment'][time_period] = var.value
                    except (ValueError, IndexError):
                        continue
        
        return credit_data
    
    def _extract_investment_analysis_data(self, solution: OptimizationSolution):
        """Extract investment-related variables for debugging model analysis"""
        import re
        
        investment_data = {
            'bonus_costs': {},
            'total_investment_measures': {},
            'CO2_costs': {}
        }
        
        # Extract investment-related variables
        for var_name, var in solution.variables.items():
            if var.value is not None:
                # Pattern: bonus_costs_{time_period}
                bonus_match = re.match(rf'bonus_costs_(\d+)', var_name)
                if bonus_match:
                    try:
                        time_period = int(bonus_match.group(1))
                        investment_data['bonus_costs'][time_period] = var.value
                    except (ValueError, IndexError):
                        continue
                
                # Pattern: total_investment_measures_{time_period}
                investment_match = re.match(rf'total_investment_measures_(\d+)', var_name)
                if investment_match:
                    try:
                        time_period = int(investment_match.group(1))
                        investment_data['total_investment_measures'][time_period] = var.value
                    except (ValueError, IndexError):
                        continue
                
                # Pattern: CO2_costs_{time_period}
                co2_match = re.match(rf'CO2_costs_(\d+)', var_name)
                if co2_match:
                    try:
                        time_period = int(co2_match.group(1))
                        investment_data['CO2_costs'][time_period] = var.value
                    except (ValueError, IndexError):
                        continue
        
        return investment_data
    
    def _extract_subsidies_data(self, solution: OptimizationSolution):
        """Extract subsidies data for debugging model analysis"""
        import re
        
        subsidies_data = {}
        
        # Extract subsidies variables
        for var_name, var in solution.variables.items():
            if var.value is not None:
                # Pattern: subsidies_{time_period}
                subsidies_match = re.match(rf'subsidies_(\d+)', var_name)
                if subsidies_match:
                    try:
                        time_period = int(subsidies_match.group(1))
                        subsidies_data[time_period] = var.value
                    except (ValueError, IndexError):
                        continue
        
        return subsidies_data
        
    def _extract_investment_measures_building_data(self, solution: OptimizationSolution, building_id: int):
        """Extract building-specific investment measures data from solution variables"""
        import re
        
        investment_data = {}
        
        # Extract total_investment_measures_building variables for the specific building
        for var_name, var in solution.variables.items():
            if var.value is not None:
                # Pattern: total_investment_measures_building_{building_id}_{time_period}
                investment_match = re.match(rf'total_investment_measures_building_{building_id}_(\d+)', var_name)
                if investment_match:
                    try:
                        time_period = int(investment_match.group(1))
                        investment_data[time_period] = var.value
                    except (ValueError, IndexError):
                        continue
        
        return investment_data
        
    def _extract_subsidies_building_data(self, solution: OptimizationSolution, building_id: int):
        """Extract building-specific subsidies data from solution variables"""
        import re
        
        subsidies_data = {}
        
        # Extract subsidies_building variables for the specific building
        for var_name, var in solution.variables.items():
            if var.value is not None:
                # Pattern: subsidies_building_{building_id}_{time_period}
                subsidies_match = re.match(rf'subsidies_building_{building_id}_(\d+)', var_name)
                if subsidies_match:
                    try:
                        time_period = int(subsidies_match.group(1))
                        subsidies_data[time_period] = var.value
                    except (ValueError, IndexError):
                        continue
        
        return subsidies_data
        
    def _extract_co2_costs_building_data(self, solution: OptimizationSolution, building_id: int, instance_data):
        """Extract building-specific CO2 costs data from solution variables"""
        import re
        
        co2_costs_data = {}
        
        # Extract CO2_costs_building variables for the specific building
        co2_costs_data = {}

        for var_name, var in solution.variables.items():
            if var.value is not None and var_name.startswith(f"F_en_{building_id}_"):
                match = re.match(rf"F_en_{building_id}_(\d+)$", var_name)
                if match:
                    time_period = int(match.group(1))
                    co2_costs_data[time_period] = var.value * instance_data["params"]["c_co2"][time_period]

        return co2_costs_data
        
    def _extract_depreciation_cost_data(self, solution: OptimizationSolution, building_id: int):
        """Extract depreciation cost data for a specific building from solution variables"""
        import re
        
        # Dictionary to store time period -> total depreciation cost
        depreciation_data = {}
        
        # Dictionary to store time period -> {measure -> cost} for detailed breakdown
        depreciation_by_measure = {}
        
        # Look for both new and legacy depreciation variables for the specific building
        for var_name, var in solution.variables.items():
            # Pattern for existing depreciation costs: C_dep_ex_{building_id}_{time_period}_{measure}
            pattern_existing = rf'C_dep_ex_{building_id}_(\d+)_(.+)'
            # Pattern for new depreciation costs: C_dep_{building_id}_{time_period}_{measure}
            pattern_new = rf'C_dep_{building_id}_(\d+)_(.+)'
            
            match = re.match(pattern_existing, var_name) or re.match(pattern_new, var_name)
            
            if match and var.value is not None:
                try:
                    time_period = int(match.group(1))
                    measure = match.group(2)
                    cost_value = var.value
                    
                    # Only include non-zero costs
                    if cost_value > 0:
                        # Add to total depreciation for this time period
                        if time_period not in depreciation_data:
                            depreciation_data[time_period] = 0
                        depreciation_data[time_period] += cost_value
                        
                        # Store detailed breakdown by measure
                        if time_period not in depreciation_by_measure:
                            depreciation_by_measure[time_period] = {}
                        depreciation_by_measure[time_period][measure] = cost_value
                    
                except (ValueError, IndexError):
                    continue
        
        return {
            'total': depreciation_data,
            'by_measure': depreciation_by_measure
        }
        
    def _render_depreciation_costs_chart(self, solution: OptimizationSolution, building_id: int):
        """Render a chart showing depreciation costs over time for a building"""
        import plotly.graph_objects as go
        import pandas as pd
        
        # Extract depreciation cost data
        depreciation_data = self._extract_depreciation_cost_data(solution, building_id)
        
        if not depreciation_data['total']:
            st.info(f"Keine Abschreibungskosten für bestehende Systeme für Gebäude {building_id} gefunden. Dies könnte bedeuten, dass keine bestehenden Systeme mit Abschreibungen in den Optimierungsperioden vorhanden sind.")
            return
            
        # Create a DataFrame for the total depreciation costs
        total_data = []
        for time_period, cost in depreciation_data['total'].items():
            total_data.append({
                'Time Period': time_period,
                'Cost': cost,
                'Type': 'Total'
            })
            
        # Create a DataFrame for depreciation costs by measure
        measure_data = []
        for time_period, measures in depreciation_data['by_measure'].items():
            for measure, cost in measures.items():
                if cost > 0:  # Only include measures with non-zero costs
                    measure_data.append({
                        'Time Period': time_period,
                        'Cost': cost,
                        'Type': measure
                    })
        
        # Combine data for plotting
        all_data = pd.DataFrame(total_data + measure_data)
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["Jährliche Gesamtabschreibungen", "Jährliche Abschreibung pro Maßnahme"])
        
        with tab1:
            if total_data:
                # Sort by time period
                total_df = pd.DataFrame(total_data).sort_values('Time Period')
                
                # Create bar chart for total costs
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=total_df['Time Period'],
                    y=total_df['Cost'],
                    name='Abschreibungskosten',
                    marker_color="#34a7c4",  # Green color for depreciation
                    hovertemplate='Jahr: %{x}<br>Kosten: €%{y:.2f}<extra></extra>'
                ))
                
                fig.update_layout(
                    title=f'Gebäude {building_id}',
                    xaxis_title='Jahr',
                    yaxis_title='Abschreibungskosten (€)',
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
        with tab2:
            if measure_data:
                # Create DataFrame for measures
                measure_df = pd.DataFrame(measure_data).sort_values(['Time Period', 'Cost'], ascending=[True, False])
                
                # Get unique time periods and measures
                time_periods = sorted(measure_df['Time Period'].unique())
                
                # Create stacked bar chart for costs by measure
                fig = go.Figure()
                
                # Group by time period and measure
                pivot_df = measure_df.pivot_table(
                    index='Time Period', 
                    columns='Type', 
                    values='Cost', 
                    aggfunc='sum'
                ).fillna(0)
                
                # Add a trace for each measure
                for measure in pivot_df.columns:
                    # Get translated measure name
                    measure_translated = get_technology_translation(measure)
                    
                    fig.add_trace(go.Bar(
                        x=pivot_df.index,
                        y=pivot_df[measure],
                        name=measure_translated,
                        hovertemplate='Jahr: %{x}<br>Maßnahme: ' + measure_translated + '<br>Kosten: €%{y:.2f}<extra></extra>'
                    ))
                
                fig.update_layout(
                    title=f'Gebäude {building_id}',
                    xaxis_title='Jahr',
                    yaxis_title='Kosten (€)',
                    barmode='stack',
                    height=600,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)

    def _render_cmod_costs_chart(self, solution: OptimizationSolution, building_id: int):
        """Render C_mod and C_mod_heat costs chart for a building"""
        import plotly.graph_objects as go
        import pandas as pd
        
        # Extract C_mod data
        cmod_data = self._extract_cmod_data(solution, building_id)
        
        if not cmod_data['cmod'] and not cmod_data['cmod_heat']:
            st.info(f"Keine Modernisierungskostendaten (C_mod/C_mod_heat) für Gebäude {building_id} verfügbar.")
            return
        
        # Get all time periods from both datasets
        all_time_periods = set()
        if cmod_data['cmod']:
            all_time_periods.update(cmod_data['cmod'].keys())
        if cmod_data['cmod_heat']:
            all_time_periods.update(cmod_data['cmod_heat'].keys())
        
        if not all_time_periods:
            st.info(f"Keine Modernisierungskostendaten für Gebäude {building_id} gefunden.")
            return
        
        time_periods = sorted(all_time_periods)
        
        # Create combined plot
        fig = go.Figure()
        
        # Add C_mod trace if data exists
        if cmod_data['cmod']:
            cmod_values = [cmod_data['cmod'].get(tp, 0) for tp in time_periods]
            fig.add_trace(go.Scatter(
                x=time_periods,
                y=cmod_values,
                mode='lines+markers',
                name='Modernisierungsumlage',
                line=dict(color='#d62728', width=3),  # Red color
                marker=dict(size=8),
                hovertemplate='<b>Modernisierungsumlage</b><br>' +
                             'Jahr: %{x}<br>' +
                             'Kosten: €%{y:.2f}<br>' +
                             '<extra></extra>'
            ))
        
        # Add C_mod_heat trace if data exists
        if cmod_data['cmod_heat']:
            cmod_heat_values = [cmod_data['cmod_heat'].get(tp, 0) for tp in time_periods]
            fig.add_trace(go.Scatter(
                x=time_periods,
                y=cmod_heat_values,
                mode='lines+markers',
                name='Heizungsmodernisierungsumlage',
                line=dict(color='#ff7f0e', width=3),  # Orange color
                marker=dict(size=8),
                hovertemplate='<b>Heizungsmodernisierungsumlage</b><br>' +
                             'Jahr: %{x}<br>' +
                             'Kosten: €%{y:.2f}<br>' +
                             '<extra></extra>'
            ))
        
        fig.update_layout(
            title=f"Gebäude {building_id}",
            xaxis_title="Jahr",
            yaxis_title="Modernisierungsumlage (€)",
            yaxis=dict(rangemode='tozero'),  # Ensure y-axis starts at 0
            height=400,
            showlegend=True,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        

    def _render_yearly_rental_income_chart(self, solution: OptimizationSolution):
        """Render yearly rental income chart for debugging model"""
        import plotly.graph_objects as go
        import pandas as pd
        
        # Extract yearly rental income data
        rental_data = self._extract_yearly_rental_income_data(solution)
        
        if not rental_data:
            st.info("No yearly rental income data available.")
            return
        
        time_periods = sorted(rental_data.keys())
        rental_values = [rental_data[tp] for tp in time_periods]
        
        # Create the plot
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=time_periods,
            y=rental_values,
            mode='lines+markers',
            name='Jährliche Mieteinnahmen',
            line=dict(color='#2E8B57', width=3),
            marker=dict(size=10),
            fill='tonexty' if len(time_periods) > 1 else None,
            fillcolor='rgba(46, 139, 87, 0.1)',
            hovertemplate='<b>Jährliche Mieteinnahmen</b><br>' +
                         'Jahr: %{x}<br>' +
                         'Einnahmen: €%{y:,.2f}<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title="",
            xaxis_title="Jahr",
            yaxis_title="Mieteinnahmen (€)",
            yaxis=dict(rangemode='tozero'),
            height=400,
            showlegend=False,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        

    def _render_credit_analysis_chart(self, solution: OptimizationSolution):
        """Render credit analysis chart for debugging model"""
        import plotly.graph_objects as go
        import pandas as pd
        
        # Extract credit analysis data
        credit_data = self._extract_credit_analysis_data(solution)
        
        # Check if any credit data exists
        has_data = any(credit_data[key] for key in credit_data.keys())
        if not has_data:
            st.info("Keine Kreditanalyse-Daten verfügbar.")
            return
        
        # Get all time periods from all datasets
        all_time_periods = set()
        for data_type in credit_data.values():
            all_time_periods.update(data_type.keys())
        
        if not all_time_periods:
            st.info("Kein Kreditdaten gefunden.")
            return
        
        time_periods = sorted(all_time_periods)
        
        # Create the main plot
        fig = go.Figure()
        
        # Color scheme for different credit components
        colors = {
            'pre_credit_payment': "#5CC996",     # Green
            'credit_repayment': '#FF6B6B',      # Red
            'credit_interest': "#E4AC33",       # Teal
            'credit_payment': "#44B4CE"        # Blue   
        }
        
        # Add traces for each credit component
        for component, data in credit_data.items():
            if data:  # Only add if data exists
                values = [data.get(tp, 0) for tp in time_periods]
                # German translations for display names
                german_display_names = {
                    'pre_credit_payment': 'Bestehende Kredite',
                    'credit_repayment': 'Kredittilgung',
                    'credit_interest': 'Kreditzinsen',
                    'credit_payment': 'Neue Kreditzahlungen'
                }
                
                # Use German translation if available, otherwise use formatted original name
                display_name = german_display_names.get(component, component.replace('_', ' ').title())
                
                fig.add_trace(go.Scatter(
                    x=time_periods,
                    y=values,
                    mode='lines+markers',
                    name=display_name,
                    line=dict(color=colors[component], width=3),
                    marker=dict(size=8),
                    hovertemplate=f'<b>{display_name}</b><br>' +
                                 'Jahr: %{x}<br>' +
                                 'Betrag: €%{y:,.2f}<br>' +
                                 '<extra></extra>'
                ))
        
        fig.update_layout(
            title="",
            xaxis_title="Jahr",
            yaxis_title="Betrag (€)",
            yaxis=dict(rangemode='tozero'),
            height=500,
            showlegend=True,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        

    def _render_investment_analysis_chart(self, solution: OptimizationSolution):
        """Render investment analysis chart for debugging model"""
        import plotly.graph_objects as go
        import pandas as pd
        from plotly.subplots import make_subplots
        
        # Extract investment analysis data
        investment_data = self._extract_investment_analysis_data(solution)
        
        # Check if any investment data exists
        has_data = any(investment_data[key] for key in investment_data.keys())
        if not has_data:
            st.info("No investment analysis data available.")
            return
        
        # Get all time periods from all datasets
        all_time_periods = set()
        for data_type in investment_data.values():
            all_time_periods.update(data_type.keys())
        
        if not all_time_periods:
            st.info("No investment data found.")
            return
        
        time_periods = sorted(all_time_periods)
        
        # Create subplot with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add traces for investment components (primary y-axis)
        if investment_data['bonus_costs']:
            bonus_values = [investment_data['bonus_costs'].get(tp, 0) for tp in time_periods]
            fig.add_trace(go.Scatter(
                x=time_periods,
                y=bonus_values,
                mode='lines+markers',
                name='Bonuskosten',
                line=dict(color='#FF7F50', width=3),
                marker=dict(size=10),
                hovertemplate='<b>Bonuserträge</b><br>' +
                             'Jahr: %{x}<br>' +
                             'Kosten: €%{y:,.2f}<br>' +
                             '<extra></extra>'
            ), secondary_y=False)
        
        if investment_data['total_investment_measures']:
            investment_values = [investment_data['total_investment_measures'].get(tp, 0) for tp in time_periods]
            fig.add_trace(go.Scatter(
                x=time_periods,
                y=investment_values,
                mode='lines+markers',
                name='Gesamtinvestitionsmaßnahmen',
                line=dict(color='#32CD32', width=3),
                marker=dict(size=10),
                hovertemplate='<b>Gesamtinvestitionsmaßnahmen</b><br>' +
                             'Jahr: %{x}<br>' +
                             'Investment: €%{y:,.2f}<br>' +
                             '<extra></extra>'
            ), secondary_y=False)
        
        # Add CO2 costs on secondary y-axis
        if investment_data['CO2_costs']:
            co2_values = [investment_data['CO2_costs'].get(tp, 0) for tp in time_periods]
            fig.add_trace(go.Scatter(
                x=time_periods,
                y=co2_values,
                mode='lines+markers',
                name='CO2-Kosten',
                line=dict(color='#1E90FF', width=3),  # Blue solid line
                marker=dict(size=10, symbol='diamond'),
                hovertemplate='<b>CO2-Kosten</b><br>' +
                             'Jahr: %{x}<br>' +
                             'CO2-Kosten: €%{y:,.2f}<br>' +
                             '<extra></extra>'
            ), secondary_y=True)
        
        # Update layout and axis labels
        fig.update_layout(
            title="",
            xaxis_title="Jahr",
            height=500,
            showlegend=True,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            # Clean grid settings
            plot_bgcolor='white',
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                zeroline=True,
                zerolinewidth=1,
                zerolinecolor='rgba(128,128,128,0.3)'
            )
        )
        
        # Set y-axes titles
        fig.update_yaxes(
            title_text="Betrag (€)",
            rangemode='tozero',
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='rgba(128,128,128,0.3)',
            secondary_y=False
        )
        fig.update_yaxes(
            title_text="CO2-Kosten (€)",
            rangemode='tozero',
            showgrid=False,  # Hide grid for secondary y-axis to reduce clutter
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='rgba(128,128,128,0.3)',
            secondary_y=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        

    def _render_subsidies_chart(self, solution: OptimizationSolution):
        """Render total subsidies chart for debugging model"""
        import plotly.graph_objects as go
        import pandas as pd
        
    
        # Extract subsidies data
        subsidies_data = self._extract_subsidies_data(solution)
        
        if not subsidies_data:
            st.info("No subsidies data available.")
            return
        
        time_periods = sorted(subsidies_data.keys())
        subsidies_values = [subsidies_data[tp] for tp in time_periods]
        
        # Create the plot
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=time_periods,
            y=subsidies_values,
            mode='lines+markers',
            name='Gesamtförderungen',
            line=dict(color='#FFD700', width=3),  # Gold color for subsidies
            marker=dict(size=10),
            fill='tonexty' if len(time_periods) > 1 else None,
            fillcolor='rgba(255, 215, 0, 0.1)',  # Light gold fill
            hovertemplate='<b>Gesamtförderungen</b><br>' +
                         'Jahr: %{x}<br>' +
                         'Förderungen: €%{y:,.2f}<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title="",
            xaxis_title="Jahr",
            yaxis_title="Förderungen (€)",
            yaxis=dict(rangemode='tozero'),
            height=400,
            showlegend=False,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        

    def _render_investment_measures_building_chart(self, solution: OptimizationSolution, building_id: int):
        """Render building-specific investment measures chart for debugging model"""
        import plotly.graph_objects as go
        import pandas as pd
        
        
        
        # Extract investment measures data for the specific building
        investment_data = self._extract_investment_measures_building_data(solution, building_id)
        
        if not investment_data:
            st.info(f"Keine Investitionsmaßnahmendaten für Gebäude {building_id} verfügbar.")
            return
        
        time_periods = sorted(investment_data.keys())
        investment_values = [investment_data[tp] for tp in time_periods]
        
        # Create the plot
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=time_periods,
            y=investment_values,
            mode='lines+markers',
            name=f'Investitionsmaßnahmen Gebäude {building_id}',
            line=dict(color='#1f77b4', width=3),  # Blue color for investments
            marker=dict(size=10),
            fill='tonexty' if len(time_periods) > 1 else None,
            fillcolor='rgba(31, 119, 180, 0.1)',  # Light blue fill
            hovertemplate=f'<b>Investitionsmaßnahmen Gebäude {building_id}</b><br>' +
                         'Jahr: %{x}<br>' +
                         'Betrag: €%{y:,.2f}<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"Gebäude {building_id}",
            xaxis_title="Jahr",
            yaxis_title="Betrag (€)",
            yaxis=dict(rangemode='tozero'),
            height=400,
            showlegend=False,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def _render_subsidies_building_chart(self, solution: OptimizationSolution, building_id: int):
        """Render building-specific subsidies chart for debugging model"""
        import plotly.graph_objects as go
        import pandas as pd
        
        
        
        # Extract subsidies data for the specific building
        subsidies_data = self._extract_subsidies_building_data(solution, building_id)
        
        if not subsidies_data:
            st.info(f"Keine Fördermitteldaten für Gebäude {building_id} verfügbar.")
            return
        
        time_periods = sorted(subsidies_data.keys())
        subsidies_values = [subsidies_data[tp] for tp in time_periods]
        
        # Create the plot
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=time_periods,
            y=subsidies_values,
            mode='lines+markers',
            name=f'Fördermaßnahmen Gebäude {building_id}',
            line=dict(color='#FFD700', width=3),  # Gold color for subsidies
            marker=dict(size=10),
            fill='tonexty' if len(time_periods) > 1 else None,
            fillcolor='rgba(255, 215, 0, 0.1)',  # Light gold fill
            hovertemplate=f'<b>Fördermaßnahmen Gebäude {building_id}</b><br>' +
                         'Jahr: %{x}<br>' +
                         'Förderungen: €%{y:,.2f}<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"Gebäude {building_id}",
            xaxis_title="Jahr",
            yaxis_title="Förderungen (€)",
            yaxis=dict(rangemode='tozero'),
            height=400,
            showlegend=False,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def _render_objective_tab(self, solution: OptimizationSolution):
        """Render the objective tab with objective weights visualization"""
        st.subheader("Zielfunktion der Optimierung")
        
        st.markdown("---")

        # Get objective weights
        objective_weights = self._get_objective_weights()
        
        if objective_weights:
            # Render the objective weights chart
            self._render_objective_weights_chart(objective_weights)
        else:
            st.info("Gewichtung der Zielfunktion für die Optimierung nicht gefunden")
    
    def _get_objective_weights(self):
        """Get the objective weights from main.py"""
        try:
            import re
            from pathlib import Path
            
            # Path to main.py - need to go up from components/pages/ to visualization/ then to run/
            main_path = Path(__file__).resolve().parent.parent.parent.parent / "run" / "main.py"
            
            if not main_path.exists():
                st.warning(f"Could not find main.py at: {main_path}")
                return None
                
            # Read main.py content
            content = main_path.read_text()
            
            # Extract phi values using regex
            phi_eq = re.search(r'"phi_eq"\s*:\s*([\d\.]+)', content)
            phi_liq = re.search(r'"phi_liq"\s*:\s*([\d\.]+)', content)
            phi_em = re.search(r'"phi_em"\s*:\s*([\d\.]+)', content)
            
            if phi_eq and phi_liq and phi_em:
                return {
                    "phi_eq": float(phi_eq.group(1)),
                    "phi_liq": float(phi_liq.group(1)),
                    "phi_em": float(phi_em.group(1))
                }
            else:
                st.warning(f"Could not extract phi values from main.py. Found: phi_eq={phi_eq}, phi_liq={phi_liq}, phi_em={phi_em}")
            return None
        except Exception as e:
            st.error(f"Error reading objective weights: {e}")
            import traceback
            st.code(traceback.format_exc())
            return None
    
    def _render_objective_weights_chart(self, weights):
        """Render a donut chart showing objective weights"""
        import plotly.graph_objects as go
        
        # Filter non-zero weights for the chart
        labels = []
        values = []
        colors = []
        
        if weights["phi_eq"] > 0:
            labels.append("Eigenkapital")
            values.append(weights["phi_eq"])
            colors.append("#1f77b4")  # Blue
            
        if weights["phi_liq"] > 0:
            labels.append("Liquidität")
            values.append(weights["phi_liq"])
            colors.append("#2ca02c")  # Green
            
        if weights["phi_em"] > 0:
            labels.append("Emissionen")
            values.append(weights["phi_em"])
            colors.append("#d62728")  # Red
            
        # If all weights are zero, show placeholder
        if not values:
            labels = ["Keine Zielfunktionsgewichtung definiert"]
            values = [1]
            colors = ["#cccccc"]  # Gray
            
        # Create donut chart
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=.4,
            marker_colors=colors
        )])
        
        fig.update_layout(
            title="Gewichtung der Zielfunktion für die Optimierung des Gebäudeportfolios",
            height=250,
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-.2,
                xanchor="center",
                x=0.5
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)

