"""
Technology mix visualization showing portfolio composition
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st
from typing import Dict, List

from .base_viz import BaseVisualization
from core.data_models import OptimizationSolution
from config.translations import get_technology_translation

class TechnologyMix(BaseVisualization):
    """Visualization for technology portfolio analysis"""
    
    def __init__(self):
        super().__init__(
            title="Technologieportfolio",
            description="Analyse des Technologiemix für das Gebäudeportfolio"
        )
    
    def _extract_installation_data(self, solution: OptimizationSolution):
        """Extract installation and uninstallation data from solution"""
        # Get all X variables (both X_in_ and X_out_)
        x_vars = solution.get_variables_by_type("X")
        
        if not x_vars:
            return None, None, [], []
        
        # Group by time period, installation type, and measure type
        installed_by_time_and_type = {}
        uninstalled_by_time_and_type = {}
        installed_measure_types = set()
        uninstalled_measure_types = set()
        all_time_periods = set()
        
        # First pass - collect all measure types and time periods
        for var_name, var in x_vars.items():
            if var.value is not None and var.value > 0.5 and var.time_period is not None:  # Only count measures that are actually selected
                time_period = var.time_period
                all_time_periods.add(time_period)
                
                # Determine if this is installation or uninstallation based on variable name
                if 'X_in_' in var_name:
                    measure_type = self._extract_measure_type(var_name, 'X_in_')
                    installed_measure_types.add(measure_type)
                elif 'X_out_' in var_name:
                    measure_type = self._extract_measure_type(var_name, 'X_out_')
                    uninstalled_measure_types.add(measure_type)
        
        # Fill in complete time period range (0 to max period) test
        if all_time_periods:
            max_period = max(all_time_periods)
            all_time_periods = set(range(max_period + 1))
            
        # Second pass - populate data structures with zero counts for all periods and measure types
        for time_period in all_time_periods:
            if time_period not in installed_by_time_and_type:
                installed_by_time_and_type[time_period] = {}
            if time_period not in uninstalled_by_time_and_type:
                uninstalled_by_time_and_type[time_period] = {}
                
            # Initialize all measure types with zero
            for measure_type in installed_measure_types:
                if measure_type not in installed_by_time_and_type[time_period]:
                    installed_by_time_and_type[time_period][measure_type] = 0
                    
            for measure_type in uninstalled_measure_types:
                if measure_type not in uninstalled_by_time_and_type[time_period]:
                    uninstalled_by_time_and_type[time_period][measure_type] = 0
                    
        # Third pass - count actual installations and uninstallations
        for var_name, var in x_vars.items():
            if var.value is not None and var.value > 0.5 and var.time_period is not None:
                time_period = var.time_period
                
                if 'X_in_' in var_name:
                    measure_type = self._extract_measure_type(var_name, 'X_in_')
                    installed_by_time_and_type[time_period][measure_type] += 1
                    
                elif 'X_out_' in var_name:
                    measure_type = self._extract_measure_type(var_name, 'X_out_')
                    uninstalled_by_time_and_type[time_period][measure_type] += 1
        
        # Convert sets to sorted lists
        installed_measure_types = sorted(installed_measure_types)
        uninstalled_measure_types = sorted(uninstalled_measure_types)
        
        return installed_by_time_and_type, uninstalled_by_time_and_type, installed_measure_types, uninstalled_measure_types
        
    def create_installation_pathway(self, solution: OptimizationSolution):
        """Create installation pathway diagram with stacked bars showing technology types per time period"""
        
        installed_by_time_and_type, _, installed_measure_types, _ = self._extract_installation_data(solution)
        
        if not installed_by_time_and_type:
            return self._create_empty_figure("No installation data found")
            
        # Get all time periods that should be displayed
        all_time_periods = sorted(installed_by_time_and_type.keys())
        
        if not all_time_periods or not installed_measure_types:
            return self._create_empty_figure("No installation measures found")
        
        # Create the plot
        fig = go.Figure()
        
        # Create x-axis labels as just the number
        x_labels = [f"{tp}" for tp in all_time_periods]
        
        # Get translations for all technology names
        translations = self._translate_technology_names(installed_measure_types)
        
        # Create stacked bars for each measure type
        for measure_type in installed_measure_types:
            y_values = []
            
            for time_period in all_time_periods:
                installed_count = installed_by_time_and_type.get(time_period, {}).get(measure_type, 0)
                y_values.append(installed_count)
            
            # Get consistent color for this measure type
            color = self._get_technology_color(measure_type)
            
            # Add trace for this measure type (will be stacked) with translated name
            fig.add_trace(go.Bar(
                name=translations[measure_type],
                x=x_labels,
                y=y_values,
                marker_color=color,
                hovertemplate="<b>%{fullData.name}</b><br>" +
                             "Jahr: %{x}<br>" +
                             "Anzahl: %{y}<br>" +
                             "<extra></extra>"
            ))
        
        # Update layout
        fig.update_layout(
            title='',
            xaxis_title='Jahr',
            yaxis_title='Anzahl installierter Maßnahmen',
            barmode='stack',
            showlegend=True,
            height=400,
            xaxis=dict(
                tickmode='array',
                tickvals=all_time_periods,
                ticktext=[str(tp) for tp in all_time_periods]
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
        
    def create_uninstallation_pathway(self, solution: OptimizationSolution):
        """Create uninstallation pathway diagram with stacked bars showing technology types per time period"""
        
        _, uninstalled_by_time_and_type, _, uninstalled_measure_types = self._extract_installation_data(solution)
        
        if not uninstalled_by_time_and_type:
            return self._create_empty_figure("Keine Deinstallationsdaten gefunden")
            
        # Get all time periods that should be displayed
        all_time_periods = sorted(uninstalled_by_time_and_type.keys())
        
        if not all_time_periods or not uninstalled_measure_types:
            return self._create_empty_figure("Keine Deinstallationsmaßnahmen gefunden")

        # Create the plot
        fig = go.Figure()
        
        # Create x-axis labels as just the number
        x_labels = [f"{tp}" for tp in all_time_periods]
        
        # Get translations for all technology names
        translations = self._translate_technology_names(uninstalled_measure_types)
        
        # Create stacked bars for each measure type
        for measure_type in uninstalled_measure_types:
            y_values = []
            
            for time_period in all_time_periods:
                uninstalled_count = uninstalled_by_time_and_type.get(time_period, {}).get(measure_type, 0)
                y_values.append(uninstalled_count)
            
            # Get consistent color for this measure type
            color = self._get_technology_color(measure_type)
            
            # Add trace for this measure type (will be stacked) with translated name
            fig.add_trace(go.Bar(
                name=translations[measure_type],
                x=x_labels,
                y=y_values,
                marker_color=color,
                hovertemplate="<b>%{fullData.name}</b><br>" +
                             "Jahr: %{x}<br>" +
                             "Anzahl: %{y}<br>" +
                             "<extra></extra>"
            ))
        
        # Update layout
        fig.update_layout(
            title='',
            xaxis_title='Jahr',
            yaxis_title='Anzahl deinstallierter Maßnahmen',
            barmode='stack',
            xaxis=dict(
                tickmode='array',
                tickvals=all_time_periods,
                ticktext=[str(tp) for tp in all_time_periods]
            ),
            showlegend=True,
            height=400,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    def _extract_measure_type(self, var_name, prefix):
        """Extract measure type from variable name.
        
        Args:
            var_name: Variable name like 'X_in_0_0_boi_gas'
            prefix: Prefix like 'X_in_'
            
        Returns:
            Measure type like 'boi_gas'
        """
        # Remove prefix
        remaining = var_name.replace(prefix, '')
        parts = remaining.split('_')
        
        # Skip first two parts (time period and building index), return the rest as measure type
        if len(parts) >= 3:
            return '_'.join(parts[2:])  # Join all parts after time and building indices
        return remaining
    
    def _translate_technology_names(self, measure_types):
        """Translate a list of technology names to German.
        
        Args:
            measure_types: List of technology names
            
        Returns:
            Dictionary mapping original names to translated names
        """
        return {tech: get_technology_translation(tech) for tech in measure_types}
    
    def _get_technology_color(self, measure_type):
        """Get a unique color for each technology type.
        
        Args:
            measure_type: Technology name like 'boi_gas', 'hp_air', etc.
            
        Returns:
            Hex color string
        """
        # Extended color palette with distinct colors for each technology
        color_palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
            '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5',
            '#393b79', '#637939', '#8c6d31', '#843c39', '#7b4173',
            '#5254a3', '#6b6ecf', '#9c9ede', '#637939', '#8ca252',
            '#b5cf6b', '#cedb9c', '#8c6d31', '#bd9e39', '#e7ba52',
            '#843c39', '#ad494a', '#d6616b', '#7b4173', '#a55194'
        ]
        
        # Create a consistent hash-based color assignment
        # This ensures the same technology always gets the same color
        import hashlib
        hash_value = int(hashlib.md5(measure_type.encode()).hexdigest(), 16)
        color_index = hash_value % len(color_palette)
        
        return color_palette[color_index]
    
    def _extract_building_time_data(self, solution: OptimizationSolution):
        """Extract building and time period data from solution variables."""
        import re
        
        # Get all X variables and filter for X_in and X_out patterns
        all_x_vars = solution.get_variables_by_type("X")
        
        buildings_data = {}
        max_time_period = 0  # Track the maximum time period across all variables
        
        # First pass: find the maximum time period by scanning ALL variables
        for var_name, var in all_x_vars.items():
            # Check for X_in or X_out pattern to extract time period
            match = re.match(r'X_(?:in|out)_\d+_(\d+)_.+', var_name)
            if match:
                try:
                    time_period = int(match.group(1))
                    max_time_period = max(max_time_period, time_period)
                except (ValueError, IndexError):
                    continue
        
        # Second pass: collect actual installation/uninstallation data
        for var_name, var in all_x_vars.items():
            if var.value is not None and var.value > 0.5:
                # Check for X_in pattern: X_in_{building_id}_{time_period}_{technology}
                match = re.match(r'X_in_(\d+)_(\d+)_(.+)', var_name)
                if match:
                    try:
                        building_id = int(match.group(1))
                        time_period = int(match.group(2))
                        technology = match.group(3)
                        
                        # Translate technology name
                        translated_technology = get_technology_translation(technology)
                        
                        if building_id not in buildings_data:
                            buildings_data[building_id] = {}
                        if time_period not in buildings_data[building_id]:
                            buildings_data[building_id][time_period] = {'installed': [], 'uninstalled': []}
                        
                        buildings_data[building_id][time_period]['installed'].append(translated_technology)
                    except (ValueError, IndexError):
                        continue
                
                # Check for X_out pattern: X_out_{building_id}_{time_period}_{technology}
                match = re.match(r'X_out_(\d+)_(\d+)_(.+)', var_name)
                if match:
                    try:
                        building_id = int(match.group(1))
                        time_period = int(match.group(2))
                        technology = match.group(3)
                        
                        # Translate technology name
                        translated_technology = get_technology_translation(technology)
                        
                        if building_id not in buildings_data:
                            buildings_data[building_id] = {}
                        if time_period not in buildings_data[building_id]:
                            buildings_data[building_id][time_period] = {'installed': [], 'uninstalled': []}
                        
                        buildings_data[building_id][time_period]['uninstalled'].append(translated_technology)
                    except (ValueError, IndexError):
                        continue
        
        # Store max_time_period in buildings_data for later use
        buildings_data['_max_time_period'] = max_time_period
        
        return buildings_data
    
    def _create_building_technology_table(self, buildings_data):
        """Create table data structure for building technology installations/uninstallations."""
        if not buildings_data:
            return {'headers': ['Building Name'], 'cells': [[]], 'cell_colors': []}
        
        # Get all buildings and time periods
        all_buildings = sorted(buildings_data.keys())
        all_time_periods = set()
        for building_data in buildings_data.values():
            all_time_periods.update(building_data.keys())
        all_time_periods = sorted(all_time_periods)
        
        # Create headers
        headers = ['Building Name'] + [f'Period {tp}' for tp in all_time_periods]
        
        # Create cell data with clickable building names
        building_names = []
        for bid in all_buildings:
            # Create a markdown link that will set query parameters
            building_link = f"Gebäude {bid}"
            building_names.append(building_link)
        
        cells = [building_names]
        cell_colors = []
        
        # For each time period, create a column
        for time_period in all_time_periods:
            period_data = []
            period_colors = []
            
            for building_id in all_buildings:
                cell_content = ""
                cell_color = "white"
                
                if building_id in buildings_data and time_period in buildings_data[building_id]:
                    installed = buildings_data[building_id][time_period]['installed']
                    uninstalled = buildings_data[building_id][time_period]['uninstalled']
                    
                    content_parts = []
                    if installed:
                        content_parts.append(f"📦 Installed: {', '.join(installed)}")
                        cell_color = "#d4edda"  # Darker green for better contrast
                    if uninstalled:
                        content_parts.append(f"📤 Uninstalled: {', '.join(uninstalled)}")
                        if cell_color == "white":
                            cell_color = "#f8d7da"  # Darker red for better contrast
                        else:
                            cell_color = "#fff3cd"  # Darker yellow for mixed actions
                    
                    cell_content = "<br>".join(content_parts) if content_parts else "—"
                else:
                    cell_content = "—"
                
                period_data.append(cell_content)
                period_colors.append(cell_color)
            
            cells.append(period_data)
            cell_colors.append(period_colors)
        
        return {
            'headers': headers,
            'cells': cells,
            'cell_colors': cell_colors
        }
    
    def create_building_technology_table(self, solution: OptimizationSolution):
        """Create technology portfolio analysis as a table showing installations/uninstallations by building and time period."""
        # Extract building and time period data dynamically
        buildings_periods_data = self._extract_building_time_data(solution)
        
        if not buildings_periods_data:
            return go.Figure().add_annotation(
                text="No building technology data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Create table data
        table_data = self._create_building_technology_table(buildings_periods_data)
        
        # Create table visualization
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=table_data['headers'],
                fill_color='#4472C4',  # Darker blue for better contrast
                align='center',
                font=dict(size=12, color='white'),  # White text on dark blue
                height=40
            ),
            cells=dict(
                values=table_data['cells'],
                fill_color=[['white'] * len(table_data['cells'][0])] + 
                           [table_data['cell_colors'][i] for i in range(len(table_data['cell_colors']))],
                align='left',
                font=dict(size=10, color='black'),  # Explicit black text
                height=30
            )
        )])
        
        fig.update_layout(
            title="Technology Portfolio Analysis - Installations and Uninstallations by Building",
            height=max(400, 50 + 35 * len(table_data['cells'][0])),  # Dynamic height based on number of buildings
            margin=dict(l=20, r=20, t=80, b=20)
        )
        
        return fig
    
    def create_building_technology_dataframe(self, solution: OptimizationSolution):
        """Create a DataFrame version of the building technology table for interactive display"""
        import pandas as pd
        
        # Extract building and time period data dynamically
        buildings_periods_data = self._extract_building_time_data(solution)
        
        if not buildings_periods_data:
            return pd.DataFrame({'Message': ['No building technology data available']})
        
        # Get all buildings and time periods
        all_buildings = sorted(buildings_periods_data.keys())
        all_time_periods = set()
        for building_data in buildings_periods_data.values():
            all_time_periods.update(building_data.keys())
        all_time_periods = sorted(all_time_periods)
        
        # Create DataFrame data
        rows = []
        for building_id in all_buildings:
            row = {'Building': f'Gebäude {building_id}', 'Building_ID': building_id}
            
            for time_period in all_time_periods:
                cell_content = "—"
                
                if building_id in buildings_periods_data and time_period in buildings_periods_data[building_id]:
                    installed = buildings_periods_data[building_id][time_period]['installed']
                    uninstalled = buildings_periods_data[building_id][time_period]['uninstalled']
                    
                    content_parts = []
                    if installed:
                        content_parts.append(f"📦 Installed: {', '.join(installed)}")
                    if uninstalled:
                        content_parts.append(f"📤 Uninstalled: {', '.join(uninstalled)}")
                    
                    cell_content = " | ".join(content_parts) if content_parts else "—"
                
                row[f'Period {time_period}'] = cell_content
            
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def create_figure(self, solution: OptimizationSolution, instance_data=None, **kwargs) -> go.Figure:
        """Create technology mix visualization"""
        
        chart_type = kwargs.get('chart_type', 'pie')
        
        if chart_type == 'pie':
            return self._create_technology_pie(solution, instance_data)
        elif chart_type == 'bar':
            return self._create_technology_bar(solution, instance_data)
        elif chart_type == 'treemap':
            return self._create_technology_treemap(solution, instance_data)
        elif chart_type == 'building_table':
            return self.create_building_technology_table(solution)
        else:
            return self._create_technology_pie(solution, instance_data)

    def _create_technology_pie(self, solution: OptimizationSolution, instance_data=None) -> go.Figure:
        """Create pie chart of technology installations"""
        
        x_vars = solution.get_variables_by_type("X")
        installed = {k: v for k, v in x_vars.items() if v.value == 1}
        
        if not installed:
            return self._create_empty_figure("No installed technologies found")
        
        # Count installations by category
        category_counts = {}
        for var in installed.values():
            category = var.category or 'other'
            category_counts[category] = category_counts.get(category, 0) + 1
        
        if not category_counts:
            return self._create_empty_figure("No categorized technologies found")
        
        categories = list(category_counts.keys())
        counts = list(category_counts.values())
        colors = [self._get_technology_color(cat) for cat in categories]
        
        fig = go.Figure(data=[go.Pie(
            labels=[cat.title() for cat in categories],
            values=counts,
            marker_colors=colors,
            hovertemplate="<b>%{label}</b><br>" +
                         "Installations: %{value}<br>" +
                         "Percentage: %{percent}<br>" +
                         "<extra></extra>"
        )])
        
        fig.update_layout(
            title="Technology Portfolio Distribution",
            height=self.config["height"]["medium"]
        )
        
        return fig
    
    def _create_technology_bar(self, solution: OptimizationSolution, instance_data=None) -> go.Figure:
        """Create bar chart of individual technologies"""
        
        x_vars = solution.get_variables_by_type("X")
        installed = {k: v for k, v in x_vars.items() if v.value == 1}
        
        if not installed:
            return self._create_empty_figure("No installed technologies found")
        
        # Count installations by technology
        tech_counts = {}
        for var in installed.values():
            if var.technology:
                tech_counts[var.technology] = tech_counts.get(var.technology, 0) + 1
        
        if not tech_counts:
            return self._create_empty_figure("No technology data found")
        
        # Sort by count
        sorted_techs = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)
        technologies, counts = zip(*sorted_techs) if sorted_techs else ([], [])
        
        # Get colors based on technology category
        colors = []
        for tech in technologies:
            # Simple categorization based on technology name
            if any(heating in tech.lower() for heating in ['boi', 'hp', 'chp', 'eh']):
                colors.append(self.colors["technology"]["heating"])
            elif any(envelope in tech.lower() for envelope in ['wall', 'roof', 'win']):
                colors.append(self.colors["technology"]["envelope"])
            elif any(storage in tech.lower() for storage in ['tes', 'bat']):
                colors.append(self.colors["technology"]["storage"])
            elif any(renewable in tech.lower() for renewable in ['pv', 'stc']):
                colors.append(self.colors["technology"]["renewable"])
            else:
                colors.append("#95A5A6")
        
        fig = go.Figure(data=[go.Bar(
            x=list(technologies),
            y=list(counts),
            marker_color=colors,
            hovertemplate="<b>%{x}</b><br>" +
                         "Installations: %{y}<br>" +
                         "<extra></extra>"
        )])
        
        fig.update_layout(
            title="Individual Technology Installations",
            xaxis_title="Technology",
            yaxis_title="Number of Installations",
            height=self.config["height"]["medium"],
            xaxis_tickangle=-45
        )
        
        return fig
    
    def _create_technology_treemap(self, solution: OptimizationSolution, instance_data=None) -> go.Figure:
        """Create treemap of technology hierarchy"""
        
        x_vars = solution.get_variables_by_type("X")
        installed = {k: v for k, v in x_vars.items() if v.value == 1}
        
        if not installed:
            return self._create_empty_figure("No installed technologies found")
        
        # Prepare hierarchical data
        treemap_data = []
        
        # Group by category and technology
        hierarchy = {}
        for var in installed.values():
            category = var.category or 'other'
            technology = var.technology or 'unknown'
            
            if category not in hierarchy:
                hierarchy[category] = {}
            if technology not in hierarchy[category]:
                hierarchy[category][technology] = 0
            hierarchy[category][technology] += 1
        
        # Build treemap data
        for category, technologies in hierarchy.items():
            # Add category level
            category_total = sum(technologies.values())
            treemap_data.append({
                'ids': category,
                'labels': category.title(),
                'parents': '',
                'values': category_total
            })
            
            # Add technology level
            for technology, count in technologies.items():
                treemap_data.append({
                    'ids': f"{category}-{technology}",
                    'labels': technology,
                    'parents': category,
                    'values': count
                })
        
        if not treemap_data:
            return self._create_empty_figure("No hierarchical data available")
        
        df_treemap = pd.DataFrame(treemap_data)
        
        fig = go.Figure(go.Treemap(
            ids=df_treemap['ids'],
            labels=df_treemap['labels'],
            parents=df_treemap['parents'],
            values=df_treemap['values'],
            branchvalues="total",
            hovertemplate="<b>%{label}</b><br>" +
                         "Count: %{value}<br>" +
                         "Parent: %{parent}<br>" +
                         "<extra></extra>"
        ))
        
        fig.update_layout(
            title="Technology Hierarchy Treemap",
            height=self.config["height"]["large"]
        )
        
        return fig
    
    def render(self, solution: OptimizationSolution, instance_data=None, **kwargs):
        """Render technology mix with interactive controls"""
        
        st.subheader(self.title)
        if self.description:
            st.markdown(self.description)
        if not solution:
            st.warning("Keine Lösungsdaten für die Visualisierung verfügbar")
            return
        
        # Installation pathway diagram at the top
        st.subheader("Modernisierungspfad: Installation von Technologien")
        installation_fig = self.create_installation_pathway(solution)
        if installation_fig:
            installation_fig.update_layout(
                font_family=self.config["font_family"],
                title_font_size=self.config["title_size"]
            )
            st.plotly_chart(installation_fig, use_container_width=True)
        else:
            st.info("Keine Installationsdaten verfügbar")
            
        # Uninstallation pathway diagram below
        st.subheader("Modernisierungspfad: Deinstallation von Technologien")
        uninstallation_fig = self.create_uninstallation_pathway(solution)
        if uninstallation_fig:
            uninstallation_fig.update_layout(
                font_family=self.config["font_family"],
                title_font_size=self.config["title_size"]
            )
            st.plotly_chart(uninstallation_fig, use_container_width=True)
        else:
            st.info("Keine Deinstallationsdaten verfügbar")
        
        st.markdown("---")
        
        # Create interactive table
        self._render_interactive_building_table(solution)
    
    def _render_interactive_building_table(self, solution: OptimizationSolution, instance_data=None):
        """Render interactive building table as a clean DataFrame with separate rows for installed/uninstalled"""
        
        # Extract building and time period data dynamically
        buildings_periods_data = self._extract_building_time_data(solution)
        
        if not buildings_periods_data:
            st.warning("Keine Gebäudetechnologiedaten verfügbar")
            return
        
        # Extract max time period (stored during data extraction)
        max_period = buildings_periods_data.pop('_max_time_period', 0)
        
        # Get all buildings
        all_buildings = sorted(buildings_periods_data.keys())
        
        # Create complete time period range from 0 to max (to show ALL columns including empty ones)
        all_time_periods = list(range(max_period + 1)) if max_period >= 0 else []
        
        # Table title
        st.markdown("### Technologieportfolio - Installationen und Deinstallationen nach Gebäude")
        
        # Add CSS for table styling with consistent column widths and gray separators
        st.markdown("""
        <style>
        .tech-table {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
            font-size: 14px;
            table-layout: fixed;
        }
        .tech-table th {
            background-color: #1f77b4;
            color: white;
            padding: 12px 8px;
            text-align: center;
            font-weight: bold;
            border: 1px solid #dee2e6;
            position: sticky;
            top: 0;
            z-index: 10;
            width: 150px;
        }
        .tech-table th:first-child {
            width: 220px;
        }
        .tech-table td {
            padding: 10px 8px;
            border: 1px solid #666666;
            word-wrap: break-word;
            overflow-wrap: break-word;
            width: 150px;
        }
        .tech-table td:first-child {
            width: 220px;
        }
        .tech-table td.building-id {
            background-color: #e3f2fd;
            font-weight: bold;
        }
        .tech-table td.installed-cell {
            background-color: #d4edda;
            color: #155724;
        }
        .tech-table td.uninstalled-cell {
            background-color: #f8d7da;
            color: #721c24;
        }
        .tech-table td.empty-cell {
            background-color: white;
        }
        .tech-table tr.separator-bottom td {
            border-bottom: 2px solid #666666 !important;
        }
        .tech-table-container {
            overflow-x: auto;
            max-height: 600px;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Build HTML table
        html_parts = ['<div class="tech-table-container"><table class="tech-table">']
        
        # Header row
        html_parts.append('<thead><tr>')
        html_parts.append('<th>Gebäude-ID</th>')
        for time_period in all_time_periods:
            html_parts.append(f'<th>Jahr {time_period}</th>')
        html_parts.append('</tr></thead>')
        
        # Data rows
        html_parts.append('<tbody>')
        for idx, building_id in enumerate(all_buildings):
            is_last_building = (idx == len(all_buildings) - 1)
            
            # Installed row
            html_parts.append('<tr>')
            html_parts.append(f'<td class="building-id">Gebäude {building_id} - Installiert</td>')
            for time_period in all_time_periods:
                cell_class = 'empty-cell'
                cell_content = '&nbsp;'  # Non-breaking space for empty cells
                if (building_id in buildings_periods_data and 
                    time_period in buildings_periods_data[building_id] and
                    buildings_periods_data[building_id][time_period]['installed']):
                    cell_class = 'installed-cell'
                    cell_content = ', '.join(buildings_periods_data[building_id][time_period]['installed'])
                html_parts.append(f'<td class="{cell_class}">{cell_content}</td>')
            html_parts.append('</tr>')
            
            # Uninstalled row with gray separator (except for last building)
            row_class = '' if is_last_building else 'separator-bottom'
            html_parts.append(f'<tr class="{row_class}">')
            html_parts.append(f'<td class="building-id">Gebäude {building_id} - Deinstalliert</td>')
            for time_period in all_time_periods:
                cell_class = 'empty-cell'
                cell_content = '&nbsp;'  # Non-breaking space for empty cells
                if (building_id in buildings_periods_data and 
                    time_period in buildings_periods_data[building_id] and
                    buildings_periods_data[building_id][time_period]['uninstalled']):
                    cell_class = 'uninstalled-cell'
                    cell_content = ', '.join(buildings_periods_data[building_id][time_period]['uninstalled'])
                html_parts.append(f'<td class="{cell_class}">{cell_content}</td>')
            html_parts.append('</tr>')
        
        html_parts.append('</tbody></table></div>')
        
        # Display the HTML table
        st.markdown(''.join(html_parts), unsafe_allow_html=True)
