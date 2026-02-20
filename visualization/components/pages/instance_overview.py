"""
Portfolio overview page for browsing and managing instances
"""
import streamlit as st
from typing import Optional

from core.instance_manager import InstanceManager
from core.data_models import InstanceMetadata
from components.instance_selector import InstanceSelector, InstanceCreator
from components.sidebar import StatusIndicator
from config.file_formats import FILE_FORMATS

class InstanceOverviewPage:
    """Page for instance management and overview"""
    
    def __init__(self, instance_manager: InstanceManager):
        self.instance_manager = instance_manager
        self.instance_selector = InstanceSelector(instance_manager)
        self.instance_creator = InstanceCreator()
    
    def render(self) -> Optional[InstanceMetadata]:
        """Render the portfolio overview page and return selected instance"""
        
        st.header("Portfolio-Übersicht")
        st.markdown("Durchsuchen, wählen und verwalten Sie Portfolio-Datensätze für die Analyse.")
        
        # Instance selection
        selected_instance = self.instance_selector.render()
        
        if selected_instance:
            st.markdown("---")
            self._render_instance_analysis(selected_instance)
        
        return selected_instance
    
    def _render_instance_analysis(self, instance: InstanceMetadata):
        """Render detailed instance analysis with tabs"""
        
        # Check data availability for different categories
        data_status = self._check_data_availability(instance)
        
        # Create tabs for different data categories
        tab1, tab2, tab3, tab4 = st.tabs([
            "Übersicht",
            "Gebäudedaten",
            "Finanzdaten", 
            "Portfolio Kapazitäten"
        ])
        
        with tab1:
            self._render_overview_tab(instance, data_status)
        
        with tab2:
            self._render_building_data_status(instance, data_status['building'])
        
        with tab3:
            self._render_financial_data_status(instance, data_status['financial'])
        
        with tab4:
            self._render_portfolio_resources_status(instance, data_status['portfolio'])
    
    def _render_overview_tab(self, instance: InstanceMetadata, data_status):
        """Render the Overview tab with data availability summary"""
        
        st.subheader("Überblick: Datenvollständigkeit des Portfolios")
        
        # Create a nice overview table
        self._render_data_overview_table(instance, data_status)
        
        # Overall status message
        st.markdown("---")
        overall_status = self._render_overall_status(data_status)
        
        # Actions
        st.markdown("---")
        st.subheader("Aktionen")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # View results button  
            if instance.has_solution:
                if st.button("→ Ergebnisse anzeigen"):
                    st.session_state.current_page = "Optimization Results"
                    st.rerun()
            else:
                st.button("→ Ergebnisse anzeigen", disabled=True,
                         help="Keine Lösung für diesen Portfolio-Datensatz verfügbar")
        
        with col2:
            # Run optimization - enabled if status is green or yellow (not red)
            can_optimize = overall_status != "red"
            if can_optimize:
                if st.button("Optimierung starten"):
                    st.info("Optimierungsfunktion wird bald verfügbar sein!")
            else:
                st.button("Optimierung starten", disabled=True,
                         help="Optimierung kann nicht starten: Kritische Daten fehlen (roter Status)!")
        
        # Add instance management sections below Actions
        st.markdown("---")
        
        # Get all instances for management sections
        all_instances = self.instance_manager.discover_instances()
        
        # Render New Instance section
        self.instance_selector._render_instance_creation_section(all_instances)
        
        st.markdown("---")
        
        # Render Delete Instance section
        self.instance_selector._render_delete_instance_section(instance, all_instances)
    
    def _render_data_overview_table(self, instance: InstanceMetadata, data_status):
        """Render a colored table with data availability overview"""
        
        import pandas as pd
        
        # Prepare data for the table
        config_files = instance.config_files if instance.config_files else {}
        
        # Building Data
        building_files = ['building_constraints.csv', 'stock_properties.csv']
        building_available = sum(1 for f in building_files if config_files.get(f) and config_files.get(f).exists())
        building_total = len(building_files)
        
        # Financial Data
        financial_files = ['financial_properties.csv', 'general_finances.json']
        financial_available = sum(1 for f in financial_files if config_files.get(f) and config_files.get(f).exists())
        financial_total = len(financial_files)
        
        # Portfolio Resources
        portfolio_files = ['portfolio_caps.csv', 'portfolio_caps.json']
        portfolio_available = sum(1 for f in portfolio_files if config_files.get(f) and config_files.get(f).exists())
        portfolio_total = len(portfolio_files)
        
        # Create DataFrame with status codes for styling
        data = {
            'Daten': ['Gebäudedaten', 'Finanzdaten', 'Portfolio Kapazitäten'],
            'Status': [
                data_status['building'],
                data_status['financial'],
                data_status['portfolio']
            ],
            'StatusDisplay': [
                self._get_status_display(data_status['building']),
                self._get_status_display(data_status['financial']),
                self._get_status_display(data_status['portfolio'])
            ]
        }
        
        df = pd.DataFrame(data)
        
        # Get status list for row coloring
        data_status_list = [data_status['building'], data_status['financial'], data_status['portfolio']]
        
        # Replace Status with display text
        df['Status'] = df['StatusDisplay']
        df = df.drop('StatusDisplay', axis=1)
        
        # Function to color rows based on row index (maps to status list)
        def color_rows_by_index(row):
            idx = row.name  # Get row index
            status = data_status_list[idx] if idx < len(data_status_list) else 'red'
            if status == 'green':
                return ['background-color: #d4edda; color: #155724'] * 2  # 2 columns
            elif status == 'yellow':
                return ['background-color: #fff3cd; color: #856404'] * 2
            else:  # red
                return ['background-color: #f8d7da; color: #721c24'] * 2
        
        # Apply styling
        styled_df = df.style.apply(color_rows_by_index, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    def _get_status_display(self, status_code):
        """Convert status code to display text"""
        status_map = {
            'green': '✅ Vollständig',
            'yellow': '⚠️ Teilweise',
            'red': '❌ Fehlend'
        }
        return status_map.get(status_code, '❓ Unbekannt')
    
    def _render_overall_status(self, data_status):
        """Render overall status message"""
        
        statuses = [data_status['building'], data_status['financial'], data_status['portfolio']]
        
        # Count status types
        green_count = statuses.count('green')
        red_count = statuses.count('red')
        yellow_count = statuses.count('yellow')
        
        # Overall status - RED takes priority, then YELLOW
        if red_count > 0:
            overall = 'red'
            st.error("⛔ Optimierung kann nicht gestartet werden: Kritische Daten fehlen")
        elif yellow_count > 0:
            overall = 'yellow'
            st.warning("⚠️ Optimierung kann gestartet werden - Einige Daten unvollständig, Standardwerte werden verwendet")
        else:
            overall = 'green'
            st.success("✅ Alle Daten vollständig - Bereit für die Optimierung")

        return overall
    
    def _check_data_availability(self, instance: InstanceMetadata):
        """Check data availability across different categories with actual validation"""
        
        config_files = instance.config_files if instance.config_files else {}
        
        # Validate Building Data
        stock_properties_path = config_files.get('stock_properties.csv')
        financial_properties_path = config_files.get('financial_properties.csv')
        if stock_properties_path and stock_properties_path.exists():
            df = self._read_building_dataframe(stock_properties_path, financial_properties_path)
            building_validation = self._validate_building_data(df)
            building_status = building_validation['status']
        else:
            building_status = 'red'
        
        # Validate Financial Data
        general_finances_path = config_files.get('general_finances.json')
        if general_finances_path and general_finances_path.exists():
            import json
            try:
                with open(general_finances_path, 'r') as f:
                    data = json.load(f)
                financial_validation = self._validate_financial_data(data)
                financial_status = financial_validation['status']
            except:
                financial_status = 'red'
        else:
            financial_status = 'red'
        
        # Validate Portfolio Resources
        portfolio_caps_path = config_files.get('portfolio_caps.json')
        if portfolio_caps_path and portfolio_caps_path.exists():
            import json
            try:
                with open(portfolio_caps_path, 'r') as f:
                    data = json.load(f)
                portfolio_validation = self._validate_portfolio_resources(data)
                portfolio_status = portfolio_validation['status']
            except:
                portfolio_status = 'yellow'
        else:
            portfolio_status = 'yellow'
        
        return {
            'building': building_status,
            'financial': financial_status,
            'portfolio': portfolio_status
        }
    
    def _evaluate_files_status(self, files_dict):
        """Evaluate the status of a set of files
        Returns: 'green' (all present), 'yellow' (some missing), 'red' (all missing or critical missing)
        """
        if not files_dict:
            return 'red'
        
        existing_files = [f for f in files_dict.values() if f and f.exists()]
        total_files = len(files_dict)
        existing_count = len(existing_files)
        
        if existing_count == total_files:
            return 'green'
        elif existing_count > 0:
            return 'yellow'
        else:
            return 'red'
    
    def _validate_building_data(self, df):
        """
        Validate building data and return status
        
        Returns:
            dict with 'status', 'message', 'missing_critical', 'missing_optional'
        """
        import pandas as pd
        
        if df is None or df.empty:
            return {
                'status': 'red',
                'message': 'Keine Gebäudedaten verfügbar',
                'missing_critical': ['alle Daten'],
                'missing_optional': []
            }
        
        missing_critical = []
        missing_optional = []
        
        # Check for critical field: location
        if 'location' in df.columns:
            none_locations = df['location'].isna() | (df['location'] == '') | (df['location'] == 'None')
            if none_locations.any():
                missing_critical.append('Standort (in einigen Gebäuden)')
        else:
            missing_critical.append('Standort-Spalte')
        
        # Check all other fields for None/0/empty (skip ID columns)
        for col in df.columns:
            if col == 'location':
                continue  # Already checked as critical
            
            # Skip ID columns - they are auto-managed
            if col.lower() in ['id', 'building_id', 'buildingid']:
                continue
            
            # Check for None, empty string, or 'None' string - zero is a valid value
            empty_mask = df[col].isna() | (df[col] == '') | (df[col] == 'None')
            if empty_mask.any():
                missing_optional.append(f'{col} (in einigen Gebäuden)')
        
        # Determine overall status
        if missing_critical:
            status = 'red'
            message = '❌ Kritische Daten fehlen - Optimierung kann nicht gestartet werden'
        elif missing_optional:
            status = 'yellow'
            message = '⚠️ Daten unvollständig - Standardwerte werden verwendet'
        else:
            status = 'green'
            message = '✅ Alle Daten vollständig'
        
        return {
            'status': status,
            'message': message,
            'missing_critical': missing_critical,
            'missing_optional': missing_optional
        }
    
    def _validate_financial_data(self, data):
        """
        Validate financial data (general_finances.json) and return status
        
        Returns:
            dict with 'status', 'message', 'missing_critical', 'missing_optional'
        """
        if data is None:
            return {
                'status': 'red',
                'message': 'Keine Finanzdaten verfügbar',
                'missing_critical': ['alle Daten'],
                'missing_optional': []
            }
        
        missing_critical = []
        missing_optional = []
        
        # Check critical fields: initial_equity and initial_liabilities
        if 'equity' in data and 'initial_equity' in data['equity']:
            if data['equity']['initial_equity'] is None or data['equity']['initial_equity'] == '':
                missing_critical.append('equity.initial_equity')
        else:
            missing_critical.append('equity.initial_equity')
        
        if 'liabilities' in data and 'initial_liabilities' in data['liabilities']:
            if data['liabilities']['initial_liabilities'] is None or data['liabilities']['initial_liabilities'] == '':
                missing_critical.append('liabilities.initial_liabilities')
        else:
            missing_critical.append('liabilities.initial_liabilities')
        
        # Check all other nested fields for None/empty
        def check_nested_fields(obj, path=""):
            """Recursively check nested dictionary for None values"""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Skip critical fields (already checked)
                    if current_path in ['equity.initial_equity', 'liabilities.initial_liabilities']:
                        continue
                    
                    if isinstance(value, dict):
                        check_nested_fields(value, current_path)
                    elif value is None or value == '':
                        missing_optional.append(current_path)
        
        check_nested_fields(data)
        
        # Determine overall status
        if missing_critical:
            status = 'red'
            message = '❌ Kritische Daten fehlen - Optimierung kann nicht gestartet werden'
        elif missing_optional:
            status = 'yellow'
            message = '⚠️ Daten unvollständig - Standardwerte werden verwendet'
        else:
            status = 'green'
            message = '✅ Alle Daten vollständig'
        
        return {
            'status': status,
            'message': message,
            'missing_critical': missing_critical,
            'missing_optional': missing_optional
        }
    
    def _validate_portfolio_resources(self, data):
        """
        Validate portfolio resources (portfolio_caps.json) and return status
        
        Returns:
            dict with 'status', 'message', 'missing_critical', 'missing_optional'
        """
        if data is None:
            return {
                'status': 'yellow',
                'message': 'Keine Portfolio-Kapazitätsdaten - Standardwerte werden verwendet',
                'missing_critical': [],
                'missing_optional': ['alle Daten']
            }
        
        missing_optional = []
        
        # Check all nested fields for None/empty (everything is optional/yellow)
        def check_nested_fields(obj, path=""):
            """Recursively check nested dictionary for None values"""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if isinstance(value, dict):
                        check_nested_fields(value, current_path)
                    elif value is None or value == '':
                        missing_optional.append(current_path)
        
        check_nested_fields(data)
        
        # Determine overall status (no critical fields for portfolio resources)
        if missing_optional:
            status = 'yellow'
            message = '⚠️ Daten unvollständig - Standardwerte werden verwendet'
        else:
            status = 'green'
            message = '✅ Alle Daten vollständig'
        
        return {
            'status': status,
            'message': message,
            'missing_critical': [],
            'missing_optional': missing_optional
        }
    
    def _check_solution_and_confirm_delete(self, instance: InstanceMetadata, data_type: str, save_triggered_key: str = None) -> bool:
        """
        Check if instance has a solution and get user confirmation to delete it
        
        Args:
            instance: The instance being modified
            data_type: Type of data being modified (e.g., 'financial_data', 'portfolio_caps', 'building_data')
            save_triggered_key: Session state key to set when confirmation is done (to trigger save)
        
        Returns:
            True if save should proceed (either no solution or user confirmed deletion)
            False if save should be cancelled
        """
        # Check if instance has a solution
        if not instance.has_solution:
            return True
        
        # Create unique session state key for this warning
        warning_key = f"solution_warning_{data_type}_{instance.name}"
        confirmed_key = f"solution_confirmed_{data_type}_{instance.name}"
        
     
        
        # Check if user already confirmed in this session
        if st.session_state.get(confirmed_key, False):
            # Reset confirmation after use
            st.session_state[confirmed_key] = False
            
            # Delete the solution
            success, message = self.instance_manager.delete_solution_files(instance)
            if success:
                st.info(f"✓ Lösung gelöscht: {message}")
                # Force reload instance metadata to update has_solution flag
                st.session_state.pop('_instance_cache', None)
                return True
            else:
                st.error(f"Fehler beim Löschen der Lösung: {message}")
                return False
        
        
        # Display prominent warning
        st.warning("⚠️ **WARNUNG: Dieser Portfolio-Datensatz verfügt über eine bestehende Lösung!**")
        st.markdown("""
        **Das Speichern von Änderungen führt zum Invalidieren und Löschen der aktuellen Lösung.**
        
        Die bestehenden Optimierungsergebnisse werden dauerhaft entfernt, weil:
        - Geänderte Datensätze bedeuten, dass die bestehende Lösung nicht mehr zum Problem passt
        - Die Optimierung muss mit den aktualisierten Parametern erneut durchgeführt werden
        
        **💡 Empfehlung:** Wenn Sie die bestehende Lösung behalten möchten:
        1. Brechen Sie diesen Speichervorgang ab
        2. Verwenden Sie die Funktion **Portfolio-Datensatz kopieren**, um ein Duplikat zu erstellen
        3. Nehmen Sie Ihre Änderungen in der neuen Kopie vor
        """)
        
        # Define callback functions that will be called BEFORE the rerun
        def on_confirm_click():
            st.session_state[confirmed_key] = True
            if save_triggered_key:
                st.session_state[save_triggered_key] = True
        
        def on_cancel_click():
            st.session_state[warning_key] = False
            # Reset session state to reload from file
            if 'financial_data' in data_type:
                st.session_state.pop('financial_data_edited', None)
                st.session_state.pop('financial_data_original', None)
                st.session_state.pop('financial_data_filepath', None)
            elif 'portfolio_caps' in data_type:
                st.session_state.pop('portfolio_caps_edited', None)
                st.session_state.pop('portfolio_caps_original', None)
                st.session_state.pop('portfolio_caps_filepath', None)
        
        col1, col2 = st.columns(2)
        with col1:
            st.button("⚠️ Bestätigen & Lösung löschen", 
                     key=f"confirm_delete_{data_type}", 
                     type="primary",
                     on_click=on_confirm_click)
        
        with col2:
            st.button("❌ Speichern abbrechen", 
                     key=f"cancel_save_{data_type}",
                     on_click=on_cancel_click)
        
        # Return False to prevent save until confirmed
        return False
    
    def _render_building_data_status(self, instance: InstanceMetadata, status_info):
        """Render building data availability status"""
        
        config_files = instance.config_files if instance.config_files else {}
        
        # Import file name translations from the central translations module
        from config.translations import get_file_translation
        
        # Get both stock properties and financial properties
        stock_properties_path = config_files.get('stock_properties.csv')
        financial_properties_path = config_files.get('financial_properties.csv')
        
        if stock_properties_path and stock_properties_path.exists():
            # Read and validate the data first
            df = self._read_building_dataframe(stock_properties_path, financial_properties_path)
            
            # Run validation
            validation_result = self._validate_building_data(df)
            
            # Display validation status at the top (message only)
            if validation_result['status'] == 'red':
                st.error(validation_result['message'])
            elif validation_result['status'] == 'yellow':
                st.warning(validation_result['message'])
            else:
                st.success(validation_result['message'])
            
            st.markdown("---")
            
            # Render the table with highlighting
            self._render_stock_properties_table(stock_properties_path, financial_properties_path, instance)
        else:
            st.error("❌ Kritische Daten fehlen - Optimierung kann nicht gestartet werden")
            st.warning("Gebäudebestandsdaten nicht verfügbar")
            st.info("Bitte fügen Sie Gebäude zu Ihrem Portfolio hinzu, um fortzufahren.")
    
    def _render_financial_data_status(self, instance: InstanceMetadata, status_info):
        """Render financial data availability status"""
        
        config_files = instance.config_files if instance.config_files else {}
        
        # Only show General Finances JSON (financial_properties.csv moved to Building Data)
        general_finances_path = config_files.get('general_finances.json')
        if general_finances_path and general_finances_path.exists():
            # Read and validate the data
            import json
            try:
                with open(general_finances_path, 'r') as f:
                    data = json.load(f)
                
                # Run validation on FILE data (what's actually saved)
                validation_result = self._validate_financial_data(data)
                
                # Check if there are unsaved changes by comparing widget values with original
                original_data = st.session_state.get('financial_data_original')
                has_changes = False
                if original_data:
                    has_changes = self._has_widget_changes(original_data, prefix="")
                
                # Display validation status at the top (message only) - based on FILE state
                st.markdown("**Status der gespeicherten Datei:**")
                if validation_result['status'] == 'red':
                    st.error(validation_result['message'])
                elif validation_result['status'] == 'yellow':
                    st.warning(validation_result['message'])
                else:
                    st.success(validation_result['message'])
                
                # Show unsaved changes warning if applicable
                if has_changes:
                    st.warning("⚠️ **Sie haben ungespeicherte Änderungen!** Der Status oben spiegelt wider, was in der **gespeicherten Datei** enthalten ist. Farbmarkierungen (🔴/🟡/✅) zeigen ebenfalls den gespeicherten Zustand. Klicken Sie auf **Änderungen speichern**, um die Datei zu aktualisieren, oder auf **Zurücksetzen**, um Änderungen zu verwerfen.")
                
                st.markdown("---")
                
                # Render the editable form
                self._render_editable_json_data(general_finances_path, instance)
            except Exception as e:
                st.error(f"❌ Kritische Daten fehlen - Optimierung kann nicht gestartet werden")
                st.error(f"Fehler beim Lesen der Finanzdaten: {e}")
        else:
            st.error("❌ Kritische Daten fehlen - Optimierung kann nicht gestartet werden")
            st.warning("general_finances.json nicht verfügbar")
    
    def _render_portfolio_resources_status(self, instance: InstanceMetadata, status_info):
        """Render portfolio resources availability status"""
        
        config_files = instance.config_files if instance.config_files else {}
        
        # Only show portfolio_caps.json with editable interface
        portfolio_caps_path = config_files.get('portfolio_caps.json')
        if portfolio_caps_path and portfolio_caps_path.exists():
            # Read and validate the data
            import json
            try:
                with open(portfolio_caps_path, 'r') as f:
                    data = json.load(f)
                
                # Run validation on FILE data (what's actually saved)
                validation_result = self._validate_portfolio_resources(data)
                
                # Check if there are unsaved changes by comparing widget values with original
                original_data = st.session_state.get('portfolio_caps_original')
                has_changes = False
                if original_data:
                    has_changes = self._has_widget_changes(original_data, prefix="")
                
                # Display validation status at the top (message only) - based on FILE state
                st.markdown("**Status der gespeicherten Datei:**")
                if validation_result['status'] == 'yellow':
                    st.warning(validation_result['message'])
                else:
                    st.success(validation_result['message'])
                
                # Show unsaved changes warning if applicable
                if has_changes:
                    st.warning("⚠️ **Sie haben ungespeicherte Änderungen!** Der Status oben spiegelt wider, was in der **gespeicherten Datei** enthalten ist. Farbmarkierungen (🔴/🟡/✅) zeigen ebenfalls den gespeicherten Zustand. Klicken Sie auf **Änderungen speichern**, um die Datei zu aktualisieren, oder auf **Zurücksetzen**, um Änderungen zu verwerfen.")
                
                st.markdown("---")
                
                # Render the editable form
                self._render_editable_portfolio_caps(portfolio_caps_path, instance)
            except Exception as e:
                st.warning("⚠️ Daten unvollständig - Standardwerte werden verwendet")
                st.error(f"Fehler beim Lesen der Portfolio-Kapazitäten: {e}")
        else:
            st.warning("⚠️ Daten unvollständig - Standardwerte werden verwendet")
            st.info("portfolio_caps.json nicht verfügbar")
    
    def _render_status_indicator(self, status: str, label: str):
        """Render a colored status indicator"""
        
        if status == 'green':
            st.success(f"✅ {label}: Alle Daten verfügbar")
        elif status == 'yellow':
            st.warning(f"⚠️ {label}: Einige Daten fehlen")
        else:
            st.error(f"❌ {label}: Erforderliche Daten fehlen")
    
    def _render_tab_status_header(self, status: str, category: str):
        """Render a status header at the top of data tabs"""
        
        if status == 'green':
            st.success(f"✅ {category} - Alle erforderlichen Dateien verfügbar")
        elif status == 'yellow':
            st.warning(f"⚠️ {category} - Einige Dateien fehlen")
        else:
            st.error(f"❌ {category} - Kritische Daten fehlen")
    
    def _render_file_status(self, filename: str, filepath):
        """Render individual file status"""
        # Import translation function
        from config.translations import get_file_translation
        
        # Get translated filename
        translated_name = get_file_translation(filename)
        
        if filepath and filepath.exists():
            file_size = filepath.stat().st_size
            st.write(f"- ✅ {translated_name} ({file_size:,} bytes)")
        else:
            st.write(f"- ❌ {translated_name} (fehlt)")
    
    def _render_csv_table(self, filepath):
        """Render CSV file contents in a table"""
        import pandas as pd
        
        try:
            # Try reading with different options to handle various CSV formats
            df = None
            
            try:
                df = pd.read_csv(filepath)
            except Exception:
                try:
                    df = pd.read_csv(filepath, sep=';')
                except Exception:
                    try:
                        df = pd.read_csv(filepath, on_bad_lines='skip')
                    except Exception:
                        st.error("Could not read CSV file. Please check the file format.")
                        return
            
            if df is not None and not df.empty:
                # Remove empty rows
                df = df.dropna(how='all')
                df = df[~df.apply(lambda row: row.astype(str).str.strip().eq('').all(), axis=1)]
                
                # Display the table
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    height=min(400, 50 + len(df) * 35)
                )
            else:
                st.info("The file is empty.")
                
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")
    
    def _render_json_data(self, filepath):
        """Render JSON file contents"""
        import json
        import pandas as pd
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # If it's a dictionary, try to display as a table
            if isinstance(data, dict):
                # Check if values are uniform (can be converted to table)
                if data and all(isinstance(v, (dict, list)) for v in data.values()):
                    # Try to create a DataFrame
                    try:
                        df = pd.DataFrame(data)
                        st.dataframe(
                            df,
                            use_container_width=True,
                            height=min(400, 50 + len(df) * 35)
                        )
                    except:
                        # If can't create DataFrame, show as formatted JSON
                        st.json(data)
                else:
                    # Simple key-value pairs
                    st.json(data)
            elif isinstance(data, list):
                # If it's a list, try to create a DataFrame
                try:
                    df = pd.DataFrame(data)
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        height=min(400, 50 + len(df) * 35)
                    )
                except:
                    st.json(data)
            else:
                st.json(data)
                
        except Exception as e:
            st.error(f"Error reading JSON file: {e}")
    
    def _render_editable_json_data(self, filepath, instance):
        """Render JSON file contents as editable fields with visual structure"""
        import json
        import pandas as pd
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Track current filepath to detect instance changes
            current_filepath = str(filepath)
            if 'financial_data_filepath' not in st.session_state or st.session_state['financial_data_filepath'] != current_filepath:
                # Instance changed - clear old widget state and reload from file
                # Clear all old widget keys that start with 'field_'
                keys_to_delete = [k for k in st.session_state.keys() if k.startswith('field_')]
                for k in keys_to_delete:
                    del st.session_state[k]
                
                # Reset the counter when changing instances
                st.session_state['reset_counter'] = 0
                
                st.session_state['financial_data_filepath'] = current_filepath
                st.session_state['financial_data_original'] = data.copy()
                st.session_state['financial_data_edited'] = data.copy()
            
            # Store original data in session state if not already there
            if 'financial_data_original' not in st.session_state:
                st.session_state['financial_data_original'] = data.copy()
            
            # Use session state to store edits
            if 'financial_data_edited' not in st.session_state:
                st.session_state['financial_data_edited'] = data.copy()
            
            edited_data = st.session_state['financial_data_edited']
            
            # If it's a dictionary, render as organized editable fields
            if isinstance(data, dict):
                # Group related parameters
                # Detect groups by common prefixes or organize as flat structure
                self._render_editable_dict_fields(edited_data, filepath)
                
                # Save and Reset buttons
                col1, col2, col3 = st.columns([2, 2, 6])
                
                # Check if we should auto-trigger save after confirmation (OUTSIDE button check)
                save_triggered_key = f"save_triggered_financial_data_{instance.name}"
                should_save = st.session_state.get(save_triggered_key, False)

                
                with col1:
                    button_clicked = st.button("💾 Änderungen speichern", key="save_financial_data", use_container_width=True, type="primary")
                
                # Process save if button clicked OR auto-triggered after confirmation
                if button_clicked or should_save:
                    # Clear the trigger flag
                    if save_triggered_key in st.session_state:
                        del st.session_state[save_triggered_key]
                    
                    # Check for existing solution and get confirmation FIRST
                    check_result = self._check_solution_and_confirm_delete(instance, 'financial_data', save_triggered_key)
                    if check_result:
                        # Only collect widget values if user confirmed (or no solution exists)
                        self._collect_widget_values(st.session_state['financial_data_edited'], prefix="")
                        
                        try:
                            with open(filepath, 'w') as f:
                                json.dump(st.session_state['financial_data_edited'], f, indent=2)
                            st.session_state['financial_data_original'] = st.session_state['financial_data_edited'].copy()
                            st.success("✅ Finanzdaten erfolgreich gespeichert!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler beim Speichern der Finanzdaten: {e}")
                
                with col2:
                    if st.button("↺ Zurücksetzen", key="reset_financial_data", use_container_width=True):
                        # Reset edited data to original (deep copy to avoid reference issues)
                        import copy
                        st.session_state['financial_data_edited'] = copy.deepcopy(st.session_state['financial_data_original'])
                        # Increment reset counter to force widget recreation with new keys
                        if 'reset_counter' not in st.session_state:
                            st.session_state['reset_counter'] = 0
                        st.session_state['reset_counter'] += 1
                        # Clear all widget keys so they get recreated with original values
                        keys_to_delete = [k for k in list(st.session_state.keys()) if k.startswith('field_')]
                        for k in keys_to_delete:
                            del st.session_state[k]
                        st.rerun()
                
                # Import section
                st.markdown("---")
                st.markdown("### Daten Import")
                self._render_import_section(
                    'general_finances',
                    data,
                    filepath,
                    allow_concat=False
                )
                
                # Export & Template section
                st.markdown("---")
                st.markdown("### Export & Vorlage")
                col_export, col_template = st.columns(2)
                
                with col_export:
                    st.markdown("**Daten Export**")
                    self._render_export_section('general_finances', data)
                
                with col_template:
                    st.markdown("**Download Vorlage**")
                    self._render_template_section('general_finances')
            else:
                # If not a dict, fall back to JSON display
                st.json(data)
                st.info("Dieses Datenformat ist in der Benutzeroberfläche nicht bearbeitbar. Bitte bearbeiten Sie die JSON-Datei direkt.")
                
        except Exception as e:
            st.error(f"Error reading JSON file: {e}")
    
    def _render_editable_portfolio_caps(self, filepath, instance):
        """Render portfolio_caps.json as editable fields with visual structure"""
        import json
        import pandas as pd
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Track current filepath to detect instance changes
            current_filepath = str(filepath)
            if 'portfolio_caps_filepath' not in st.session_state or st.session_state['portfolio_caps_filepath'] != current_filepath:
                # Instance changed - clear old widget state and reload from file
                # Clear all old widget keys that start with 'field_'
                keys_to_delete = [k for k in st.session_state.keys() if k.startswith('field_')]
                for k in keys_to_delete:
                    del st.session_state[k]
                
                # Reset the counter when changing instances (or initialize if not exists)
                st.session_state['reset_counter'] = 0
                
                st.session_state['portfolio_caps_filepath'] = current_filepath
                st.session_state['portfolio_caps_original'] = data.copy()
                st.session_state['portfolio_caps_edited'] = data.copy()
            
            # Store original data in session state if not already there
            if 'portfolio_caps_original' not in st.session_state:
                st.session_state['portfolio_caps_original'] = data.copy()
            
            # Use session state to store edits
            if 'portfolio_caps_edited' not in st.session_state:
                st.session_state['portfolio_caps_edited'] = data.copy()
            
            edited_data = st.session_state['portfolio_caps_edited']
            
            # If it's a dictionary, render as organized editable fields
            if isinstance(data, dict):
                # Render sections similar to financial data
                self._render_portfolio_caps_fields(edited_data, filepath)
                
                # Save and Reset buttons
                col1, col2, col3 = st.columns([2, 2, 6])
                
                # Check if we should auto-trigger save after confirmation (OUTSIDE button check)
                save_triggered_key = f"save_triggered_portfolio_caps_{instance.name}"
                should_save = st.session_state.get(save_triggered_key, False)
                
                with col1:
                    button_clicked = st.button("💾 Änderungen speichern", key="save_portfolio_caps", use_container_width=True, type="primary")
                
                # Process save if button clicked OR auto-triggered after confirmation
                if button_clicked or should_save:
                    # Clear the trigger flag
                    if save_triggered_key in st.session_state:
                        del st.session_state[save_triggered_key]
                    
                    # Check for existing solution and get confirmation FIRST
                    check_result = self._check_solution_and_confirm_delete(instance, 'portfolio_caps', save_triggered_key)
                    if check_result:
                        # Only collect widget values if user confirmed (or no solution exists)
                        self._collect_widget_values(st.session_state['portfolio_caps_edited'], prefix="")
                        
                        try:
                            with open(filepath, 'w') as f:
                                json.dump(st.session_state['portfolio_caps_edited'], f, indent=4)
                            st.session_state['portfolio_caps_original'] = st.session_state['portfolio_caps_edited'].copy()
                            st.success("✅ Portfolio-Kapazitäten erfolgreich gespeichert!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler beim Speichern der Portfolio-Kapazitäten: {e}")
                
                with col2:
                    if st.button("↺ Zurücksetzen", key="reset_portfolio_caps", use_container_width=True):
                        # Reset edited data to original (deep copy to avoid reference issues)
                        import copy
                        st.session_state['portfolio_caps_edited'] = copy.deepcopy(st.session_state['portfolio_caps_original'])
                        # Increment reset counter to force widget recreation with new keys
                        if 'reset_counter' not in st.session_state:
                            st.session_state['reset_counter'] = 0
                        st.session_state['reset_counter'] += 1
                        # Clear all widget keys so they get recreated with original values
                        keys_to_delete = [k for k in list(st.session_state.keys()) if k.startswith('field_')]
                        for k in keys_to_delete:
                            del st.session_state[k]
                        st.rerun()
                
                # Import section
                st.markdown("---")
                st.markdown("### Import von Daten")
                self._render_import_section(
                    'portfolio_caps',
                    data,
                    filepath,
                    allow_concat=False
                )
                
                # Export & Template section
                st.markdown("---")
                st.markdown("### Export & Vorlage")
                col_export, col_template = st.columns(2)
                
                with col_export:
                    st.markdown("**Daten Export**")
                    self._render_export_section('portfolio_caps', data)
                
                with col_template:
                    st.markdown("**Download Vorlage**")
                    self._render_template_section('portfolio_caps')
            else:
                # If not a dict, fall back to JSON display
                st.json(data)
                st.info("Dies ist ein nicht bearbeitbares Datenformat in der Benutzeroberfläche. Bitte bearbeiten Sie die JSON-Datei direkt.")
                
        except Exception as e:
            st.error(f"Fehler beim Lesen der JSON-Datei: {e}")
    
    def _render_portfolio_caps_fields(self, data_dict, filepath, original_data=None):
        """Render portfolio caps dictionary as organized editable fields"""
        import pandas as pd
        
        # Ensure reset counter is initialized
        if 'reset_counter' not in st.session_state:
            st.session_state['reset_counter'] = 0
        
        # If no original data provided, use the session state original or current dict
        if original_data is None:
            original_data = st.session_state.get('portfolio_caps_original', data_dict)
        
        # Separate nested dicts (sections) from simple values
        nested_sections = {}
        simple_values = {}
        
        for key, value in data_dict.items():
            if isinstance(value, dict):
                nested_sections[key] = value
            else:
                simple_values[key] = value
        
        # Render nested sections first (num_measures, labor, energy, etc.)
        for section_name, section_data in sorted(nested_sections.items()):
            # German translation mapping for portfolio terms
            german_terms = {
                "num_measures": "Anzahl Maßnahmen",
                "labor": "Arbeitskraft",
                "energy": "Energie",
                "emissions": "Emissionen",
                "district_heating": "Fernwärme",
                "resources": "Ressourcen"
            }
            
            # If section name is in our mapping, use the German term, otherwise use the English one
            if section_name.lower() in german_terms:
                display_name = german_terms[section_name.lower()]
            else:
                # Fallback to standard formatting for unknown terms
                display_name = section_name.replace('_', ' ').title()
                
            st.markdown(f"**{display_name}**")
            
            # Check if this section has nested dicts (like energy with gas/pel)
            has_nested = any(isinstance(v, dict) for v in section_data.values())
            
            if has_nested:
                # Render sub-sections for things like energy.gas, energy.pel
                for sub_key, sub_value in sorted(section_data.items()):
                    if isinstance(sub_value, dict):
                        st.markdown(f"*{sub_key.replace('_', ' ').title()}*")
                        
                        # Special handling for energy section which seems to cause problems
                        if section_name == "energy":
                            # Try to fix malformed dictionaries that might be causing the issue
                            fixed_sub_value = {}
                            for k, v in sub_value.items():
                                if isinstance(k, str) and not isinstance(v, dict):  # Only include proper key-value pairs
                                    fixed_sub_value[k] = v
                            sub_value = fixed_sub_value
                        
                        # Use 2-column layout for start/end values
                        num_cols = 2
                        # Safely convert items to list and filter out any malformed entries
                        try:
                            items_list = []
                            for item in sub_value.items():
                                if isinstance(item, tuple) and len(item) == 2:
                                    items_list.append(item)
                                else:
                                    st.error(f"Überspringe ungültiges Element in {section_name}.{sub_key}: {item}")
                        except Exception as e:
                            st.error(f"Fehler beim Lesen von {section_name}.{sub_key}: {str(e)}")
                            items_list = []
                        
                        for i in range(0, len(items_list), num_cols):
                            cols = st.columns(num_cols)
                            
                            for j in range(num_cols):
                                if i + j < len(items_list):
                                    try:
                                        item = items_list[i + j]
                                        # Item is already verified to be a 2-tuple
                                        param_key, param_value = item
                                        with cols[j]:
                                            field_path = f"{section_name}.{sub_key}.{param_key}"
                                            # Get original value for comparison
                                            orig_val = None
                                            if isinstance(original_data.get(section_name), dict) and isinstance(original_data[section_name].get(sub_key), dict):
                                                orig_val = original_data[section_name][sub_key].get(param_key)
                                            # All portfolio fields are optional (YELLOW when missing)
                                            self._render_single_field(sub_value, param_key, param_value, f"{section_name}_{sub_key}_", field_path, False, orig_val)
                                    except ValueError as e:
                                        with cols[j]:
                                            st.error(f"Fehler beim Entpacken: {str(e)}")
                                    except Exception as e:
                                        with cols[j]:
                                            st.error(f"Fehler beim Verarbeiten: {str(e)}")
                    else:
                        # Direct value in section
                        field_path = f"{section_name}.{sub_key}"
                        orig_val = original_data.get(section_name, {}).get(sub_key) if isinstance(original_data.get(section_name), dict) else None
                        self._render_single_field(section_data, sub_key, sub_value, f"{section_name}_", field_path, False, orig_val)
            else:
                # Simple key-value pairs in section (like labor.start, labor.end)
                num_cols = 2
                # Safely convert items to list and filter out any malformed entries
                try:
                    items_list = []
                    for item in section_data.items():
                        if isinstance(item, tuple) and len(item) == 2:
                            items_list.append(item)
                        else:
                            st.error(f"Überspringe ungültiges Element in {section_name}: {item}")
                except Exception as e:
                    st.error(f"Fehler beim Lesen von {section_name}: {str(e)}")
                    items_list = []
                
                for i in range(0, len(items_list), num_cols):
                    cols = st.columns(num_cols)
                    
                    for j in range(num_cols):
                        if i + j < len(items_list):
                            try:
                                item = items_list[i + j]
                                # Item is already verified to be a 2-tuple
                                key, value = item
                                with cols[j]:
                                    field_path = f"{section_name}.{key}"
                                    # Get original value for comparison
                                    orig_val = original_data.get(section_name, {}).get(key) if isinstance(original_data.get(section_name), dict) else None
                                    # All portfolio fields are optional (YELLOW when missing)
                                    self._render_single_field(section_data, key, value, f"{section_name}_", field_path, False, orig_val)
                            except ValueError as e:
                                with cols[j]:
                                    st.error(f"Fehler beim Entpacken: {str(e)}")
                            except Exception as e:
                                with cols[j]:
                                    st.error(f"Fehler beim Verarbeiten: {str(e)}")
            
            st.markdown("---")  # Soft separator between sections
        
        # Render simple values under "Other Parameters" if any exist
        if simple_values:
            st.markdown("**Weitere Parameter**")
            
            num_cols = 2
            # Safely convert items to list and filter out any malformed entries
            try:
                items_list = []
                for item in simple_values.items():
                    if isinstance(item, tuple) and len(item) == 2:
                        items_list.append(item)
                    else:
                        st.error(f"Überspringe ungültiges Element in 'Weitere Parameter': {item}")
            except Exception as e:
                st.error(f"Fehler beim Lesen von 'Weitere Parameter': {str(e)}")
                items_list = []
            
            for i in range(0, len(items_list), num_cols):
                cols = st.columns(num_cols)
                
                for j in range(num_cols):
                    if i + j < len(items_list):
                        try:
                            item = items_list[i + j]
                            # Item is already verified to be a 2-tuple
                            key, value = item
                            with cols[j]:
                                # Get original value for comparison
                                orig_val = original_data.get(key) if isinstance(original_data, dict) else None
                                # All portfolio fields are optional (YELLOW when missing)
                                self._render_single_field(data_dict, key, value, "", key, False, orig_val)
                        except ValueError as e:
                            with cols[j]:
                                st.error(f"Fehler beim Entpacken: {str(e)}")
                        except Exception as e:
                            with cols[j]:
                                st.error(f"Fehler beim Verarbeiten: {str(e)}")
            
            st.markdown("---")
    
    def _render_editable_dict_fields(self, data_dict, filepath, prefix="", original_data=None):
        """Recursively render dictionary as editable fields with grouping and color coding"""
        import pandas as pd
        
        # Ensure reset counter is initialized
        if 'reset_counter' not in st.session_state:
            st.session_state['reset_counter'] = 0
        
        # If no original data provided, use the session state original or current dict
        if original_data is None:
            original_data = st.session_state.get('financial_data_original', data_dict)
        
        # Separate nested dicts (sections) from simple values
        nested_sections = {}
        simple_values = {}
        
        for key, value in data_dict.items():
            if isinstance(value, dict):
                nested_sections[key] = value
            else:
                simple_values[key] = value
        
        # Render nested sections first (equity, liquidity, liabilities, rates)
        for section_name, section_data in sorted(nested_sections.items()):
            # German translation mapping for financial terms
            german_terms = {
                "equity": "Eigenkapital",
                "liquidity": "Liquidität",
                "liabilities": "Verbindlichkeiten",
                "rates": "Zinssätze",
                "financial": "Finanzen",
                "costs": "Kosten",
                "revenue": "Einnahmen",
                "tax": "Steuern",
                "inflation": "Inflation",
                "debt": "Schulden",
                "credit": "Kredit",
                "alpha_credit": "Alpha-Kredit",
                "VAT": "Mehrwertsteuer",
                "BKI_development": "BKI-Entwicklung",
                "year_of_price_origin": "Preisreferenzjahr"
            }
            
            # If section name is in our mapping, use the German term, otherwise use the English one
            if section_name.lower() in german_terms:
                display_name = german_terms[section_name.lower()]
            else:
                # Fallback to standard formatting for unknown terms
                display_name = section_name.replace('_', ' ').title()
                
            st.markdown(f"**{display_name}**")
            
            # Use 2-column layout for fields within the section
            num_cols = 2
            # Safely convert items to list and filter out any malformed entries
            try:
                items_list = []
                for item in section_data.items():
                    if isinstance(item, tuple) and len(item) == 2:
                        items_list.append(item)
                    else:
                        st.error(f"Überspringe ungültiges Element in {section_name}: {item}")
            except Exception as e:
                st.error(f"Fehler beim Lesen von {section_name}: {str(e)}")
                items_list = []
            
            for i in range(0, len(items_list), num_cols):
                cols = st.columns(num_cols)
                
                for j in range(num_cols):
                    if i + j < len(items_list):
                        try:
                            item = items_list[i + j]
                            # Item is already verified to be a 2-tuple
                            key, value = item
                            with cols[j]:
                                # Determine if this is a critical field
                                field_path = f"{section_name}.{key}"
                                is_critical = field_path in ['equity.initial_equity', 'liabilities.initial_liabilities']
                                
                                # Get original value for comparison
                                original_value = original_data.get(section_name, {}).get(key) if isinstance(original_data.get(section_name), dict) else None
                                
                                # Update the nested dict directly
                                self._render_single_field(section_data, key, value, f"{prefix}{section_name}_", field_path, is_critical, original_value)
                        except ValueError as e:
                            with cols[j]:
                                st.error(f"Fehler beim Entpacken: {str(e)}")
                        except Exception as e:
                            with cols[j]:
                                st.error(f"Fehler beim Verarbeiten: {str(e)}")
            
            st.markdown("---")  # Soft separator between sections
        
        # Render simple values under "Other Parameters"
        if simple_values:
            st.markdown("**Weitere Parameter**")
            
            num_cols = 2
            # Safely convert items to list and filter out any malformed entries
            try:
                items_list = []
                for item in simple_values.items():
                    if isinstance(item, tuple) and len(item) == 2:
                        items_list.append(item)
                    else:
                        st.error(f"Überspringe ungültiges Element in 'Weitere Parameter': {item}")
            except Exception as e:
                st.error(f"Fehler beim Lesen von 'Weitere Parameter': {str(e)}")
                items_list = []
            
            for i in range(0, len(items_list), num_cols):
                cols = st.columns(num_cols)
                
                for j in range(num_cols):
                    if i + j < len(items_list):
                        try:
                            item = items_list[i + j]
                            # Item is already verified to be a 2-tuple
                            key, value = item
                            with cols[j]:
                                # Get original value for comparison
                                original_value = original_data.get(key) if isinstance(original_data, dict) else None
                                self._render_single_field(data_dict, key, value, prefix, key, False, original_value)
                        except ValueError as e:
                            with cols[j]:
                                st.error(f"Fehler beim Entpacken: {str(e)}")
                        except Exception as e:
                            with cols[j]:
                                st.error(f"Fehler beim Verarbeiten: {str(e)}")
            
            st.markdown("---")  # Soft separator after other parameters
    
    def _collect_widget_values(self, data_dict, prefix=""):
        """Recursively collect widget values from session state and update data_dict"""
        reset_counter = st.session_state.get('reset_counter', 0)
        for key, value in data_dict.items():
            if isinstance(value, dict):
                # Recursively collect values from nested dicts
                self._collect_widget_values(value, prefix=f"{prefix}{key}_")
            else:
                # Construct the widget key with version
                widget_key = f"field_{prefix}{key}_v{reset_counter}"
                # If the widget exists in session state, update the data
                if widget_key in st.session_state:
                    data_dict[key] = st.session_state[widget_key]
    
    def _has_widget_changes(self, original_dict, prefix=""):
        """Recursively check if any widget values differ from original_dict"""
        reset_counter = st.session_state.get('reset_counter', 0)
        for key, value in original_dict.items():
            if isinstance(value, dict):
                # Recursively check nested dicts
                if self._has_widget_changes(value, prefix=f"{prefix}{key}_"):
                    return True
            else:
                # Construct the widget key with version
                widget_key = f"field_{prefix}{key}_v{reset_counter}"
                # If the widget exists in session state, compare its value
                if widget_key in st.session_state:
                    widget_value = st.session_state[widget_key]
                    if widget_value != value:
                        return True
        return False
    
    def _render_single_field(self, data_dict, key, value, prefix="", field_path="", is_critical=False, original_value=None):
        """Render a single editable field based on value type with color coding"""
        full_key = f"{prefix}{key}" if prefix else key
        
        # German translation mapping for field names
        german_field_names = {
            # Equity section
            "initial_equity": "Anfangseigenkapital in €",
            "minimal_equity": "Minimales Eigenkapital in €",
            "minimum_equity_quota": "Mindest-Eigenkapitalquote in %",
            
            # Liquidity section
            "initial_liquidity": "Anfangsliquidität in €",
            "minimal_liquidity": "Mindestliquidität in €",
            "liquidity_rate": "Tagesgeldzinssatz in %",
            
            # Liabilities section
            "initial_liabilities": "Anfangsverbindlichkeiten in €",
            "remaining_credit_years": "Verbleibende Kreditjahre",
            "debt_interest_rate": "Schuldzinssatz in %",
            
            # Rates section
            "credit_rate": "Kreditzins in %",
            "interest_rate": "Zinssatz in %",
            "inflation_rate": "Inflationsrate in %",
            "avg_construction_price_increase": "Durchschnittlicher Baupreisanstieg in %",
            "credit_type": "Kredittyp",
            
            # General financial parameters
            "alpha_credit": "Alpha-Kredit Faktor",
            "VAT": "Mehrwertsteuer in %",
            "vat": "Mehrwertsteuer in %",  # Add lowercase version for case-insensitive matching
            "BKI_development": "BKI-Entwicklung",
            "bki_development": "BKI-Entwicklung",  # Add lowercase version for case-insensitive matching
            "year_of_price_origin": "Preisreferenzjahr",
            
            
            
            # Portfolio terms
            "start": "Start",
            "end": "Ende",
            "max_total": "Maximal gesamt",
            "max_per_period": "Maximal pro Periode",
            "min_total": "Minimal gesamt",
            "min_per_period": "Minimal pro Periode",
            "max_measures": "Maximale Maßnahmen",
            "max_investments": "Maximale Investitionen",
            "gas": "Gas",
            "pel": "Strom",
            "oil": "Öl",
            "wood": "Holz",
            "solar": "Solar",
            "capacity": "Kapazität",
            "building_limit": "Gebäudelimit",
            "technology_limit": "Technologielimit",
            "year": "Jahr"
        }
        
        # Check if this is a compound field path (e.g., "equity.initial_equity" or "energy.gas.start")
        if field_path and "." in field_path:
            # Split and handle paths with 2 or more parts (e.g., "equity.initial_equity" or "energy.gas.start")
            parts = field_path.split(".")
            if len(parts) == 2:
                section, field = parts
                compound_key = f"{section}_{field}"
            elif len(parts) >= 3:
                # For nested paths like "energy.gas.start", use the last part as field
                section = "_".join(parts[:-1])  # "energy_gas"
                field = parts[-1]  # "start"
                compound_key = f"{section}_{field}"
            else:
                # Single part, shouldn't happen but handle gracefully
                field = parts[0]
                compound_key = field
            
            # Create a case-insensitive lookup dictionary
            german_field_names_lower = {k.lower(): v for k, v in german_field_names.items()}
            
            if compound_key.lower() in german_field_names_lower:
                base_label = german_field_names_lower[compound_key.lower()]
            elif field.lower() in german_field_names_lower:
                base_label = german_field_names_lower[field.lower()]
            else:
                base_label = key.replace('_', ' ').title()
        # Check if the key itself is in our mapping - using case-insensitive lookup
        else:
            # Create a case-insensitive lookup dictionary
            german_field_names_lower = {k.lower(): v for k, v in german_field_names.items()}
            
            if key.lower() in german_field_names_lower:
                base_label = german_field_names_lower[key.lower()]
            elif key in german_field_names:  # Try direct match as fallback
                base_label = german_field_names[key]
            else:
                base_label = key.replace('_', ' ').title()
        
        # Include reset counter in widget key to force recreation on reset
        reset_counter = st.session_state.get('reset_counter', 0)
        widget_key_base = f"field_{full_key}_v{reset_counter}"
        
        # If no original value provided, use current value (no change detection)
        if original_value is None:
            original_value = value
        
        # Use a cleaner label without file value in the label
        label = base_label
        
        # Determine if field is empty/missing BASED ON FILE STATE (original_value)
        # Note: For financial/portfolio data, 0 is a VALID value (e.g., 0% rate, $0 equity)
        # Only None and empty string are considered truly "empty"
        is_empty = original_value is None or original_value == ''
        
        # Check if WIDGET value has changed from file (check session state, not data_dict)
        widget_value = st.session_state.get(widget_key_base)
        value_changed = False
        if widget_value is not None and widget_value != original_value:
            value_changed = True
        
        # Add color indicator based on criticality and emptiness OF FILE STATE
        if is_empty:
            if is_critical:
                # RED indicator for critical missing fields
                color_indicator = "🔴"
                help_text = "Kritisches Feld - erforderlich für die Optimierung"
            else:
                # YELLOW indicator for optional missing fields
                color_indicator = "🟡"
                help_text = "Optionales Feld - Standardwert wird verwendet, wenn leer"
        else:
            # GREEN indicator for filled fields
            color_indicator = "✅"
            help_text = "Ursprünglicher Parameter-Wert: " + str(original_value) if original_value is not None else "Ursprünglicher Parameter-Wert: leer"
        
        # Add value change indicator and update help text
        if value_changed:
            if help_text:
                help_text += " | ⚠️ UNGESPEICHERTE ÄNDERUNGEN"
            else:
                help_text = f"Ursprünglicher Parameter-Wert: {original_value} | ⚠️ UNGESPEICHERTE ÄNDERUNGEN"
        
        # Final label with color indicator
        label = f"{color_indicator} {label}"
        
        # Handle None values (null in JSON) - show as empty fields
        if value is None:
            # Special handling for VAT and BKI_development
            if key == 'VAT' or key.lower() == 'vat':
                widget_value = st.session_state.get(widget_key_base, None)
                st.number_input(
                    f"{color_indicator} Mehrwertsteuer in %", # Direct German label with color indicator
                    value=widget_value,
                    format="%.2f",
                    step=0.01,
                    key=widget_key_base,
                    placeholder="Mehrwertsteuer eingeben",
                    help=help_text
                )
            elif key == 'BKI_development' or key.lower() == 'bki_development':
                widget_value = st.session_state.get(widget_key_base, None)
                st.number_input(
                    f"{color_indicator} BKI-Entwicklung", # Direct German label with color indicator
                    value=widget_value,
                    format="%.5f", # Changed to %.5f to match the float handling
                    step=0.00001,
                    key=widget_key_base,
                    placeholder="BKI-Entwicklung eingeben",
                    help=help_text
                )
            # Determine field type from key name to show appropriate input
            elif any(keyword in key.lower() for keyword in ['year', 'count', 'num', 'remaining']):
                # Integer field - use session state if exists, otherwise None
                widget_value = st.session_state.get(widget_key_base, None)
                st.number_input(
                    label,
                    value=widget_value,
                    step=1,
                    key=widget_key_base,
                    placeholder="Ganzzahl eingeben",
                    help=help_text
                )
            elif key.lower() == 'credit_type':
                # Select box for credit types with German translations
                widget_value = st.session_state.get(widget_key_base, value or "")
                
                # Define credit type options with translations
                credit_type_options = {
                    "repayment_loan": "Tilgungsdarlehen",
                    "annuity_loan": "Annuitätendarlehen",
                }
                
                # Create options list preserving original values as keys
                options = list(credit_type_options.keys())
                
                # Format display values with translations
                format_func = lambda x: f"{credit_type_options.get(x, x)}"
                
                # Determine index of current value
                index = options.index(widget_value) if widget_value in options else 0
                
                # Render select box
                selected = st.selectbox(
                    label,
                    options=options,
                    format_func=format_func,
                    index=index,
                    key=widget_key_base,
                    help=help_text
                )
                
                # Update data dict with selected value
                data_dict[key] = selected
                
            elif any(keyword in key.lower() for keyword in ['type', 'name']):
                # Text field - use session state if exists, otherwise empty string
                widget_value = st.session_state.get(widget_key_base, "")
                st.text_input(
                    label,
                    value=widget_value,
                    key=widget_key_base,
                    placeholder="Text eingeben",
                    help=help_text
                )
            else:
                # Float field - use session state if exists, otherwise None
                widget_value = st.session_state.get(widget_key_base, None)
                st.number_input(
                    label,
                    value=widget_value,
                    format="%.6f",
                    key=widget_key_base,
                    placeholder="Zahlenwert eingeben",
                    help=help_text
                )
        elif isinstance(value, bool):
            # Use session state value if it exists, otherwise use value from data
            widget_value = st.session_state.get(widget_key_base, value)
            st.checkbox(
                label,
                value=widget_value,
                key=widget_key_base,
                help=help_text
            )
        elif isinstance(value, int):
            # Use session state value if it exists, otherwise use value from data
            widget_value = st.session_state.get(widget_key_base, value)
            st.number_input(
                label,
                value=widget_value,
                step=1,
                key=widget_key_base,
                help=help_text
            )
        elif isinstance(value, float):
            # Special handling for VAT and BKI_development
            if key == 'VAT' or key.lower() == 'vat':
                widget_value = st.session_state.get(widget_key_base, value)
                st.number_input(
                    f"{color_indicator} Mehrwertsteuer in %", # Direct German label with color indicator
                    value=widget_value,
                    format="%.2f",
                    step=0.01,
                    key=widget_key_base,
                    help=help_text
                )
            elif key == 'BKI_development' or key.lower() == 'bki_development':
                widget_value = st.session_state.get(widget_key_base, value)
                st.number_input(
                    f"{color_indicator} BKI-Entwicklung", # Direct German label with color indicator
                    value=widget_value,
                    format="%.5f",
                    step=0.00001,
                    key=widget_key_base,
                    help=help_text
                )
            else:
                # Use session state value if it exists, otherwise use value from data
                widget_value = st.session_state.get(widget_key_base, value)
                st.number_input(
                    label,
                    value=widget_value,
                    format="%.2f",
                    key=widget_key_base,
                    help=help_text
                )
        elif isinstance(value, str):
            # Use session state value if it exists, otherwise use value from data
            widget_value = st.session_state.get(widget_key_base, value)
            st.text_input(
                label,
                value=widget_value,
                key=widget_key_base,
                help=help_text
            )
        elif isinstance(value, list):
            # For lists, show as text area with JSON format
            data_dict[key] = st.text_area(
                label,
                value=str(value),
                height=100,
                key=f"field_{full_key}",
                help=help_text or "Als Python-Liste bearbeiten"
            )
        else:
            # Fallback to text input
            data_dict[key] = st.text_input(
                label,
                value=str(value) if value is not None else "",
                key=f"field_{full_key}",
                help=help_text
            )
    
    def _read_building_dataframe(self, filepath, financial_properties_path=None):
        """Read building dataframe (helper function for validation)"""
        import pandas as pd
        
        try:
            # Try reading with different options
            df = None
            try:
                df = pd.read_csv(filepath)
            except:
                try:
                    df = pd.read_csv(filepath, sep=';')
                except:
                    try:
                        df = pd.read_csv(filepath, on_bad_lines='skip')
                    except:
                        return pd.DataFrame()
            
            if df is not None and not df.empty:
                # Remove completely empty rows
                df = df.dropna(how='all')
                df = df[~df.apply(lambda row: row.astype(str).str.strip().eq('').all(), axis=1)]
                df = df.reset_index(drop=True)
                
                # Store the original English column names
                df.attrs['original_columns'] = df.columns.tolist()
                
                return df
            return pd.DataFrame()
        except:
            return pd.DataFrame()
    
    def _style_building_dataframe(self, df):
        """Apply conditional styling to building dataframe - RED for missing location, YELLOW for other missing"""
        import pandas as pd
        from config.translations import get_column_translation, get_technology_translation
        
        # Create a copy of the dataframe for display with translated column names
        display_df = df.copy()
        
        # Technology columns that need value translation
        tech_columns = ['ex_dis', 'always_available', 'ex_heat_prim', 'ex_dhw_sto', 'ex_sto', 'ex_heat_sec']
        
        # Age columns that need special handling
        age_columns = ['heat_age', 'dhw_age', 'solar_age', 'storage_age', 'rad_age', 'wall_age', 'windows_age', 'roof_age']
        
        # Additional columns that need dash for None values
        additional_none_dash_columns = ['cap_dhw_sto']
        
        # Try a different approach - use a non-breaking space character to force centering
        centered_dash = '—'
        
        # String to display for missing values (except for special columns)
        missing_value_text = "Fehlend"
        
        # Translate technology values for specific columns
        for col in tech_columns:
            if col in df.columns:
                # Convert boolean values to strings first for 'always_available'
                if col == 'always_available':
                    display_df[col] = df[col].apply(lambda x: str(x).lower() if pd.notna(x) else x)
                
                # Apply translation to non-empty values
                display_df[col] = df[col].apply(lambda x: get_technology_translation(str(x).lower()) if pd.notna(x) and x != '' and x != 'None' else centered_dash)
        
        # Handle age columns - replace None/NaN with dash
        for col in age_columns:
            if col in df.columns:
                display_df[col] = df[col].apply(lambda x: x if pd.notna(x) and x != '' and str(x).lower() != 'none' else centered_dash)
                
        # Handle additional columns with None/dash replacement
        for col in additional_none_dash_columns:
            if col in df.columns:
                display_df[col] = df[col].apply(lambda x: x if pd.notna(x) and x != '' and str(x).lower() != 'none' else centered_dash)
                
        # Replace all remaining None/NaN values with "Fehlend"
        # First, identify columns that haven't been processed yet
        processed_columns = tech_columns + age_columns + additional_none_dash_columns
        remaining_columns = [col for col in df.columns if col not in processed_columns]
        
        # Replace None/NaN with "Fehlend" in those columns
        for col in remaining_columns:
            if col in df.columns:
                display_df[col] = df[col].apply(lambda x: x if pd.notna(x) and x != '' and str(x).lower() != 'none' else missing_value_text)
        
        # Translate column names to German for display
        display_df.columns = [get_column_translation(col) for col in df.columns]
        
        def highlight_cells(row):
            """Apply cell-level highlighting"""
            styles = [''] * len(row)
            
            for idx, (col_name, value) in enumerate(row.items()):
                # Check if value is None, empty string, or 'None' string
                # Zero is considered a valid value, not a missing value
                is_empty = pd.isna(value) or value == '' or value == 'None'
                is_dash = value == '—'  # Check for em dash
                is_missing_text = value == "Fehlend"  # Check for "Fehlend" text
                
                # We need to check the original column name for 'location'
                original_col = df.columns[idx] if idx < len(df.columns) else None
                
                # Check if it's a special tech or age column that we've already replaced with dash
                tech_columns_original = ['ex_dis', 'always_available', 'ex_heat_prim', 'ex_dhw_sto', 'ex_sto', 'ex_heat_sec']
                age_columns_original = ['heat_age', 'dhw_age', 'solar_age', 'storage_age', 'rad_age', 'wall_age', 'windows_age', 'roof_age']
                additional_dash_columns = ['cap_dhw_sto']
                
                # Give the dash a distinct color and center it
                if is_dash:
                    # Use stronger centering styles
                    styles[idx] = 'color: #6c757d; font-weight: bold; text-align: center !important; display: block; margin: auto;'
                elif is_missing_text:
                    # Style for "Fehlend" text - yellow background with darker gray text, italic
                    styles[idx] = 'background-color: #fff3cd; color: #856404; font-style: italic;'
                elif original_col == 'location' and is_empty:
                    # RED for missing location
                    styles[idx] = 'background-color: #f8d7da; color: #721c24; font-weight: bold'
                elif is_empty and original_col not in tech_columns_original and original_col not in age_columns_original and original_col not in additional_dash_columns:
                    # YELLOW for other missing values, but not for columns where dash is expected
                    styles[idx] = 'background-color: #fff3cd; color: #856404'
            
            return styles
        
        # Create styled dataframe with the highlighting
        styled_df = display_df.style.apply(highlight_cells, axis=1)
        
        # Add cell-specific styling for em dash values
        dash_mask = display_df == '—'
        if dash_mask.any().any():
            # Get a DataFrame of booleans where True indicates a dash
            for col in display_df.columns:
                if dash_mask[col].any():
                    # Apply center styling to each cell with a dash
                    styled_df = styled_df.set_properties(subset=pd.IndexSlice[dash_mask[col], col], 
                                                        **{'text-align': 'center', 
                                                          'width': '100%', 
                                                          'display': 'block'})
        
        return styled_df
    
    def _render_stock_properties_table(self, filepath, financial_properties_path, instance):
        """Render stock properties data merged with financial properties in a table with ability to add buildings"""
        import pandas as pd
        
        try:
            # Read stock properties
            # Try reading with different options to handle various CSV formats
            df = None
            error_msg = None
            
            # First attempt: standard read
            try:
                df = pd.read_csv(filepath)
            except Exception as e1:
                error_msg = str(e1)
                
                # Second attempt: try with different separator
                try:
                    df = pd.read_csv(filepath, sep=';')
                except Exception as e2:
                    
                    # Third attempt: try reading with error handling
                    try:
                        df = pd.read_csv(filepath, on_bad_lines='skip')
                    except Exception as e3:
                        
                        # Fourth attempt: try with different encoding
                        try:
                            df = pd.read_csv(filepath, encoding='latin1')
                        except Exception as e4:
                            
                            # Final attempt: read as text and show raw content
                            st.error(f"Fehler beim Lesen der Gebäudeeigenschaften: {error_msg}")
                            st.warning("Versuche, den Rohinhalt der Datei anzuzeigen:")
                            
                            try:
                                with open(filepath, 'r') as f:
                                    content = f.read()
                                    st.text_area("Rohinhalt der Datei", content, height=300)
                                    
                                st.info("Bitte überprüfen Sie das Dateiformat. Es sollte sich um eine gültige CSV-Datei handeln.")
                            except Exception as e5:
                                st.error(f"Datei kann nicht gelesen werden: {e5}")
                            return
            
            if df is not None and not df.empty:
                # Import translations
                from config.translations import get_column_translation
                
                # Remove completely empty rows (all values are NaN or empty strings)
                df = df.dropna(how='all')
                # Also remove rows where all values are empty strings
                df = df[~df.apply(lambda row: row.astype(str).str.strip().eq('').all(), axis=1)]
                # Reset index after filtering
                df = df.reset_index(drop=True)
                
                # Store original column names before translation
                original_columns = df.columns.tolist()
                
                # Try to merge with financial properties if available
                if financial_properties_path and financial_properties_path.exists():
                    try:
                        # Try reading with different delimiters
                        financial_df = None
                        
                        # First try semicolon (as that's what your file uses)
                        try:
                            financial_df = pd.read_csv(financial_properties_path, sep=';')
                            if len(financial_df.columns) == 1:  # If only one column, wrong delimiter
                                raise ValueError("Wrong delimiter")
                        except:
                            # Then try comma
                            try:
                                financial_df = pd.read_csv(financial_properties_path, sep=',')
                                if len(financial_df.columns) == 1:  # If only one column, wrong delimiter
                                    raise ValueError("Wrong delimiter")
                            except:
                                # Try auto-detect with python engine
                                try:
                                    financial_df = pd.read_csv(financial_properties_path, sep=None, engine='python')
                                except:
                                    st.warning("⚠️ Could not read financial properties file")
                        
                        if financial_df is not None and len(financial_df.columns) > 1:
                            # Find common key column for merging
                            merge_key_stock = None
                            merge_key_financial = None
                            
                            # Check for ID columns in both dataframes
                            stock_id_cols = [col for col in df.columns if col.lower() in ['id', 'building_id', 'buildingid']]
                            financial_id_cols = [col for col in financial_df.columns if col.lower() in ['id', 'building_id', 'buildingid']]
                            
                            if stock_id_cols and financial_id_cols:
                                merge_key_stock = stock_id_cols[0]
                                merge_key_financial = financial_id_cols[0]
                                
                                # Merge the dataframes
                                df = pd.merge(df, financial_df, 
                                            left_on=merge_key_stock, 
                                            right_on=merge_key_financial, 
                                            how='left', 
                                            suffixes=('', '_financial'))
                                
                                # Track which columns came from which source
                                # Financial keywords include common financial terms and c_comp prefix
                                financial_keywords = ['cost', 'price', 'rent', 'income', 'expense', 'budget', 'investment', 
                                                     'depreciation', 'subsidy', 'tax', 'financial', 'economic']
                                
                                stock_columns = []
                                financial_columns = []
                                
                                for col in df.columns:
                                    # Check if column starts with c_comp or contains financial keywords
                                    is_financial = col.startswith('c_comp') or any(keyword in col.lower() for keyword in financial_keywords)
                                    if is_financial:
                                        financial_columns.append(col)
                                    else:
                                        stock_columns.append(col)
                                
                                # Store this information in the dataframe metadata
                                df.attrs['stock_columns'] = stock_columns
                                df.attrs['financial_columns'] = financial_columns
                                df.attrs['has_financial'] = True
                            else:
                                st.warning(f"⚠️ Finanzdaten konnten nicht zusammengeführt werden: Keine ID-Spalte gefunden (Gebäudeeigenschaften-Spalten: {df.columns.tolist()[:5]}..., Finanzdaten-Spalten: {financial_df.columns.tolist()[:5]}...)")
                                df.attrs['has_financial'] = False
                        else:
                            st.warning("⚠️ Finanzdatei konnte nicht richtig geparst werden")
                            df.attrs['has_financial'] = False
                    except Exception as e:
                        st.warning(f"⚠️ Finanzdaten konnten nicht geladen werden: {e}")
                        df.attrs['has_financial'] = False
                else:
                    df.attrs['has_financial'] = False
                
                # Display metric
                st.metric("Anzahl der Gebäude", df.shape[0])
                
                # Display interactive table with edit/delete options
                if not df.empty:
                    self._render_interactive_building_table(df, filepath, financial_properties_path, instance)
                else:
                    st.info("Keine Gebäude zum Anzeigen vorhanden.")
                
                # Add building functionality
                st.markdown("---")
                self._render_add_building_form(df, filepath, financial_properties_path, instance)
                
                # Add data management section for buildings (handles both stock and financial files)
                self._render_building_data_management_section(df, filepath, financial_properties_path)
                
            elif df is not None:
                st.warning("Gebäudeeigenschaften-Datei ist leer")
                # Still show add building form even if file is empty
                st.markdown("---")
                self._render_add_building_form(pd.DataFrame(), filepath, None, instance)
                
                # Add data management section even if empty
                self._render_building_data_management_section(pd.DataFrame(), filepath, financial_properties_path)
                
        except Exception as e:
            st.error(f"Unerwarteter Fehler beim Lesen der Gebäudeeigenschaften: {e}")
    
    def _ensure_sequential_ids(self, df):
        """Ensure building IDs are sequential starting from 0"""
        import pandas as pd
        
        # Check if there's a building_id or id column
        id_col = None
        for col_name in ['building_id', 'id', 'ID', 'Building_ID']:
            if col_name in df.columns:
                id_col = col_name
                break
        
        if id_col:
            # Reset IDs to be sequential starting from 0
            df[id_col] = range(len(df))
        else:
            # If no ID column exists, create one
            df.insert(0, 'building_id', range(len(df)))
        
        return df
    
    def _save_split_dataframes(self, df, stock_filepath, financial_filepath):
        """Split merged dataframe and save to separate CSV files"""
        import pandas as pd
        
        # If no financial filepath, just save everything to stock
        if not financial_filepath:
            df.to_csv(stock_filepath, index=False)
            return
        
        # Define which columns belong to stock properties vs financial properties
        # You can customize this based on your actual column names
        financial_keywords = ['cost', 'price', 'rent', 'income', 'expense', 'budget', 'investment', 
                             'depreciation', 'subsidy', 'tax', 'financial', 'economic']
        
        financial_cols = ['building_id'] if 'building_id' in df.columns else (['id'] if 'id' in df.columns else [])
        stock_cols = ['building_id'] if 'building_id' in df.columns else (['id'] if 'id' in df.columns else [])
        
        for col in df.columns:
            if col.lower() in ['building_id', 'id']:
                continue  # Already added
            # Check if column starts with c_comp or contains financial keywords
            is_financial = col.startswith('c_comp') or any(keyword in col.lower() for keyword in financial_keywords)
            if is_financial:
                financial_cols.append(col)
            else:
                stock_cols.append(col)
        
        # Create separate dataframes
        stock_df = df[stock_cols]
        financial_df = df[financial_cols] if len(financial_cols) > 1 else None
        
        # Save both files
        stock_df.to_csv(stock_filepath, index=False)
        if financial_df is not None and len(financial_df.columns) > 1:
            financial_df.to_csv(financial_filepath, index=False)
    
    def _render_interactive_building_table(self, df, stock_filepath, financial_filepath=None, instance=None):
        """Render an interactive table with edit/delete options for each building"""
        import pandas as pd
        
        # Ensure IDs are sequential starting from 0
        df = self._ensure_sequential_ids(df)
        
        # Split the dataframe back into stock and financial properties for saving
        self._save_split_dataframes(df, stock_filepath, financial_filepath)
        
        # Display the tables - separate by category if financial data was merged
        if df.attrs.get('has_financial', False):
            stock_columns = df.attrs.get('stock_columns', [])
            financial_columns = df.attrs.get('financial_columns', [])
            
            # Ensure ID column is in financial columns for display
            id_col = None
            for col_name in ['building_id', 'id', 'ID', 'Building_ID']:
                if col_name in df.columns:
                    id_col = col_name
                    break
            
            # Add ID column at the beginning of financial columns if not already there
            if id_col and id_col not in financial_columns:
                financial_columns = [id_col] + financial_columns
            
            # Display Energetic Parameters table
            st.markdown("**Energetische Parameter**")
            energetic_df = df[stock_columns]
            styled_energetic_df = self._style_building_dataframe(energetic_df)
            st.dataframe(
                styled_energetic_df,
                use_container_width=True,
                hide_index=True,
                height=min(400, 50 + len(energetic_df) * 35)
            )
            
            st.markdown("")  # Add some spacing
            
            # Display Financial Parameters table
            st.markdown("**Finanzielle Parameter**")
            financial_df = df[financial_columns]
            styled_financial_df = self._style_building_dataframe(financial_df)
            st.dataframe(
                styled_financial_df,
                use_container_width=True,
                hide_index=True,
                height=min(400, 50 + len(financial_df) * 35)
            )
        else:
            # Display single table if no financial data
            st.markdown("**Alle Gebäude**")
            styled_df = self._style_building_dataframe(df)
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                height=min(400, 50 + len(df) * 35)
            )
        
        st.markdown("---")
        
        # Edit Building Section
        st.markdown("#### Gebäude bearbeiten")
        
        # Get building identifiers for dropdown - use the IDs from the dataframe
        building_options = ["Gebäude auswählen"]  # Default option
        id_to_index = {}
        
        for idx, row in df.iterrows():
            # Get the building_id from the dataframe (which should be 0, 1, 2, ...)
            building_id = row.get('building_id', row.get('id', idx))
            building_label = f"Gebäude {building_id}"
            building_options.append(building_label)
            id_to_index[building_label] = idx
        
        # Dropdown to Gebäude auswählen
        selected_building = st.selectbox(
            "Wählen Sie ein Gebäude zum Bearbeiten oder Löschen:",
            options=building_options,
            index=0,  # Default to "Gebäude auswählen"
            key="building_selector"
        )
        
        # Only show edit form if a building is selected (not the default)
        if selected_building != "Gebäude auswählen":
            selected_idx = id_to_index[selected_building]
            selected_row = df.iloc[selected_idx]
            
            # Show the edit form for the selected building
            self._render_compact_edit_form(df, selected_idx, stock_filepath, financial_filepath, selected_row, instance)
    
    def _delete_building(self, df, row_idx, stock_filepath, financial_filepath=None):
        """Delete a building from the dataframe and save to CSV"""
        import pandas as pd
        
        try:
            # Drop the row
            updated_df = df.drop(index=row_idx).reset_index(drop=True)
            
            # Ensure IDs are sequential after deletion
            updated_df = self._ensure_sequential_ids(updated_df)
            
            # Save back to CSV (split if financial data exists)
            self._save_split_dataframes(updated_df, stock_filepath, financial_filepath)
            
            return True
        except Exception as e:
            st.error(f"Fehler beim Löschen des Gebäudes: {e}")
            return False
    
    def _render_compact_edit_form(self, df, row_idx, stock_filepath, financial_filepath, row_data, instance):
        """Render a compact form to edit or delete the selected building"""
        import pandas as pd
        from config.translations import get_column_translation
        
        # Determine which columns are energetic vs financial
        financial_keywords = ['cost', 'price', 'rent', 'income', 'expense', 'budget', 'investment', 
                             'depreciation', 'subsidy', 'tax', 'financial', 'economic']
        
        energetic_cols = []
        financial_cols = []
        
        for col_name in row_data.index:
            is_financial = col_name.startswith('c_comp') or any(keyword in col_name.lower() for keyword in financial_keywords)
            if is_financial:
                financial_cols.append(col_name)
            else:
                energetic_cols.append(col_name)
        
        # Create input fields for each column
        edited_data = {}
        
        # Render Energetic Parameters
        st.markdown("**Energetische Parameter**")
        
        # Use a grid layout with 3 columns for more compact display
        num_cols = 3
        
        for i in range(0, len(energetic_cols), num_cols):
            cols = st.columns(num_cols)
            
            for j in range(num_cols):
                if i + j < len(energetic_cols):
                    col_name = energetic_cols[i + j]
                    current_value = row_data[col_name]
                    
                    with cols[j]:
                        # Handle NaN values
                        if pd.isna(current_value):
                            current_value = ''
                        
                        # Determine input type based on column name
                        # Special handling for ID columns - make them read-only
                        if col_name.lower() in ['building_id', 'id']:
                            edited_data[col_name] = st.text_input(
                                get_column_translation(col_name),
                                value=str(current_value),
                                key=f"edit_compact_{row_idx}_{col_name}",
                                disabled=True,  # Make ID read-only
                                help="ID is automatically managed and cannot be edited"
                            )
                        elif col_name.lower() in ['name', 'address', 'type']:
                            edited_data[col_name] = st.text_input(
                                get_column_translation(col_name),
                                value=str(current_value),
                                key=f"edit_compact_{row_idx}_{col_name}"
                            )
                        elif col_name.lower() in ['existing', 'is_existing', 'exists']:
                            # Convert current value to boolean
                            current_bool = current_value in [True, 1, 'yes', 'Yes', 'YES', 'existing', 'Existing', 'EXISTING', 'true', 'True', 'TRUE']
                            edited_data[col_name] = st.selectbox(
                                get_column_translation(col_name),
                                options=[True, False],
                                index=0 if current_bool else 1,
                                key=f"edit_compact_{row_idx}_{col_name}"
                            )
                        elif 'year' in col_name.lower():
                            try:
                                year_value = int(float(current_value)) if current_value != '' else 2000
                                # Validate year is in reasonable range
                                if year_value < 1800 or year_value > 2100:
                                    year_value = 2000  # Reset to default if out of range
                            except:
                                year_value = 2000
                            edited_data[col_name] = st.number_input(
                                get_column_translation(col_name),
                                min_value=1800,
                                max_value=2100,
                                value=year_value,
                                step=1,
                                key=f"edit_compact_{row_idx}_{col_name}"
                            )
                        elif any(x in col_name.lower() for x in ['area', 'size', 'volume', 'height', 'units', 'floors']):
                            try:
                                num_value = float(current_value) if current_value != '' else 0.0
                            except:
                                num_value = 0.0
                            edited_data[col_name] = st.number_input(
                                get_column_translation(col_name),
                                min_value=0.0,
                                value=num_value,
                                step=1.0 if 'units' in col_name.lower() or 'floors' in col_name.lower() else 10.0,
                                key=f"edit_compact_{row_idx}_{col_name}"
                            )
                        else:
                            # Default to text input
                            edited_data[col_name] = st.text_input(
                                get_column_translation(col_name),
                                value=str(current_value),
                                key=f"edit_compact_{row_idx}_{col_name}"
                            )
        
        # Add separator and render Financial Parameters if they exist
        if financial_cols:
            st.markdown("---")  # Soft horizontal line separator
            st.markdown("**Finanzielle Parameter**")
            
            for i in range(0, len(financial_cols), num_cols):
                cols = st.columns(num_cols)
                
                for j in range(num_cols):
                    if i + j < len(financial_cols):
                        col_name = financial_cols[i + j]
                        current_value = row_data[col_name]
                        
                        with cols[j]:
                            # Handle NaN values
                            if pd.isna(current_value):
                                current_value = ''
                            
                            # Financial parameters are typically numeric
                            if any(x in col_name.lower() for x in ['cost', 'price', 'rent', 'income', 'expense', 'budget', 'investment', 'depreciation', 'subsidy', 'tax']):
                                try:
                                    num_value = float(current_value) if current_value != '' else 0.0
                                except:
                                    num_value = 0.0
                                edited_data[col_name] = st.number_input(
                                    get_column_translation(col_name),
                                    min_value=0.0,
                                    value=num_value,
                                    step=100.0,
                                    key=f"edit_compact_{row_idx}_{col_name}"
                                )
                            else:
                                # Default to text input
                                edited_data[col_name] = st.text_input(
                                    get_column_translation(col_name),
                                    value=str(current_value),
                                    key=f"edit_compact_{row_idx}_{col_name}"
                                )
        
        st.markdown("---")
        
        # Action buttons
        col1, col2, col3 = st.columns([2, 2, 6])
        
        with col1:
            if st.button("💾 Änderungen speichern", key=f"save_compact_{row_idx}", use_container_width=True, type="primary"):
                # Check for existing solution and get confirmation
                if self._check_solution_and_confirm_delete(instance, f'building_data_{row_idx}'):
                    try:
                        # Update the dataframe with edited data
                        for col_name, new_value in edited_data.items():
                            df.at[row_idx, col_name] = new_value
                        
                        # Save to CSV (split if financial data exists)
                        self._save_split_dataframes(df, stock_filepath, financial_filepath)
                        
                        st.success("✅ Änderungen erfolgreich gespeichert!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Fehler beim Speichern der Änderungen: {e}")
        
        with col2:
            if st.button("🗑️ Gebäude löschen", key=f"delete_compact_{row_idx}", use_container_width=True):
                # Confirmation in session state
                if st.session_state.get(f'confirm_delete_{row_idx}', False):
                    if self._delete_building(df, row_idx, stock_filepath, financial_filepath):
                        st.success("Gebäude erfolgreich gelöscht!")
                        st.session_state[f'confirm_delete_{row_idx}'] = False
                        st.rerun()
                else:
                    st.session_state[f'confirm_delete_{row_idx}'] = True
                    st.rerun()
        
        with col3:
            # Show confirmation message if delete was clicked once
            if st.session_state.get(f'confirm_delete_{row_idx}', False):
                st.warning("⚠️ Klicken Sie erneut auf 'Gebäude löschen', um die Löschung zu bestätigen")
    
    def _render_edit_building_form(self, df, row_idx, filepath, row_data):
        """Render form to edit an existing building"""
        import pandas as pd
        
        st.subheader(f"Gebäude bearbeiten (Zeile {row_idx})")
        
        with st.form(f"edit_form_{row_idx}"):
            # Create input fields for each column
            edited_data = {}
            
            # Use a grid layout
            num_cols = 2
            cols = st.columns(num_cols)
            
            for idx, (col_name, current_value) in enumerate(row_data.items()):
                col_idx = idx % num_cols
                
                with cols[col_idx]:
                    # Handle NaN values
                    if pd.isna(current_value):
                        current_value = ''
                    
                    # Determine input type based on column name
                    # Special handling for ID columns - make them read-only
                    if col_name.lower() in ['building_id', 'id']:
                        edited_data[col_name] = st.text_input(
                            col_name.replace('_', ' ').title(),
                            value=str(current_value),
                            key=f"edit_{row_idx}_{col_name}",
                            disabled=True,  # Make ID read-only
                            help="ID is automatically managed and cannot be edited"
                        )
                    elif col_name.lower() in ['name', 'address', 'type']:
                        edited_data[col_name] = st.text_input(
                            col_name.replace('_', ' ').title(),
                            value=str(current_value),
                            key=f"edit_{row_idx}_{col_name}"
                        )
                    elif col_name.lower() in ['existing', 'is_existing', 'exists']:
                        # Convert current value to boolean
                        current_bool = current_value in [True, 1, 'yes', 'Yes', 'YES', 'existing', 'Existing', 'EXISTING', 'true', 'True', 'TRUE']
                        edited_data[col_name] = st.selectbox(
                            col_name.replace('_', ' ').title(),
                            options=[True, False],
                            index=0 if current_bool else 1,
                            key=f"edit_{row_idx}_{col_name}"
                        )
                    elif 'year' in col_name.lower():
                        try:
                            year_value = int(float(current_value)) if current_value != '' else 2000
                            # Validate year is in reasonable range
                            if year_value < 1800 or year_value > 2100:
                                year_value = 2000  # Reset to default if out of range
                        except:
                            year_value = 2000
                        edited_data[col_name] = st.number_input(
                            col_name.replace('_', ' ').title(),
                            min_value=1800,
                            max_value=2100,
                            value=year_value,
                            step=1,
                            key=f"edit_{row_idx}_{col_name}"
                        )
                    elif any(x in col_name.lower() for x in ['area', 'size', 'volume', 'height', 'units', 'floors']):
                        try:
                            num_value = float(current_value) if current_value != '' else 0.0
                        except:
                            num_value = 0.0
                        edited_data[col_name] = st.number_input(
                            col_name.replace('_', ' ').title(),
                            min_value=0.0,
                            value=num_value,
                            step=1.0 if 'units' in col_name.lower() or 'floors' in col_name.lower() else 10.0,
                            key=f"edit_{row_idx}_{col_name}"
                        )
                    else:
                        # Default to text input
                        edited_data[col_name] = st.text_input(
                            col_name.replace('_', ' ').title(),
                            value=str(current_value),
                            key=f"edit_{row_idx}_{col_name}"
                        )
            
            # Form buttons
            col1, col2 = st.columns(2)
            with col1:
                save_button = st.form_submit_button("💾 Save Changes")
            with col2:
                cancel_button = st.form_submit_button("❌ Cancel")
            
            if save_button:
                try:
                    # Update the dataframe with edited data
                    for col_name, new_value in edited_data.items():
                        df.at[row_idx, col_name] = new_value
                    
                    # Save to CSV
                    df.to_csv(filepath, index=False)
                    
                    # Clear editing state
                    st.session_state[f'editing_row_{row_idx}'] = False
                    
                    st.success("✅ Changes saved successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error saving changes: {e}")
            
            if cancel_button:
                # Clear editing state
                st.session_state[f'editing_row_{row_idx}'] = False
                st.rerun()
    
    def _render_add_building_form(self, existing_df, stock_filepath, financial_filepath=None, instance=None):
        """Render form to add new buildings to the stock"""
        import pandas as pd
        from config.translations import get_column_translation
        
        st.markdown("#### Neues Gebäude hinzufügen")
        
        # Show solution warning if instance has a solution
        if instance and instance.has_solution:
            st.warning("⚠️ **Hinweis:** Dieser Portfolio-Datensatz hat eine bestehende Lösung. Durch das Hinzufügen eines Gebäudes wird die Lösung ungültig und beim Speichern gelöscht.")
        
        with st.expander("➕ Gebäude hinzufügen", expanded=False):
            # Get column names from existing dataframe
            if not existing_df.empty:
                columns = existing_df.columns.tolist()
            else:
                # Define default columns if file is empty
                st.warning("Keine vorhandenen Gebäude gefunden. Standardstruktur wird verwendet.")
                columns = ['building_id', 'name', 'type', 'area_m2', 'year_built', 
                          'existing', 'address', 'units']
            
            # Copy from existing building dropdown
            copy_options = ["Gebäude auswählen"]
            copy_id_to_index = {}
            
            if not existing_df.empty:
                for idx, row in existing_df.iterrows():
                    building_id = row.get('building_id', row.get('id', idx))
                    building_label = f"Gebäude {building_id}"
                    copy_options.append(building_label)
                    copy_id_to_index[building_label] = idx
                
                st.write("**Daten von bestehendem Gebäude kopieren:**")
                selected_copy_building = st.selectbox(
                    "Parameter von einem bestehenden Gebäude kopieren:",
                    options=copy_options,
                    index=0,
                    key="copy_building_selector",
                    help="Wählen Sie ein Gebäude, um dessen Parameter zu kopieren (ID wird nicht kopiert)"
                )
                
                # Get the data to copy if a building is selected
                copy_data = None
                if selected_copy_building != "Gebäude auswählen":
                    copy_idx = copy_id_to_index[selected_copy_building]
                    copy_data = existing_df.iloc[copy_idx]
                    st.info(f"📋 Parameter werden von {selected_copy_building} kopiert")
                
                st.markdown("---")
            
            # Calculate the next building ID
            next_id = len(existing_df) if not existing_df.empty else 0
            
            # Categorize columns into energetic and financial
            financial_keywords = ['cost', 'price', 'rent', 'income', 'expense', 'budget', 'investment', 
                                 'depreciation', 'subsidy', 'tax', 'financial', 'economic']
            
            energetic_cols = []
            financial_cols = []
            
            for col_name in columns:
                is_financial = col_name.startswith('c_comp') or any(keyword in col_name.lower() for keyword in financial_keywords)
                if is_financial:
                    financial_cols.append(col_name)
                else:
                    energetic_cols.append(col_name)
            
            # Create a form for adding a building
            with st.form("add_building_form"):
                # Create input fields for each column
                new_building_data = {}
                
                # Render Energetic Parameters
                st.write("**Energetische Parameter**")
                
                # Use a grid layout for better organization
                num_cols = 2
                
                for idx, col_name in enumerate(energetic_cols):
                    col_idx = idx % num_cols
                    if col_idx == 0:
                        cols = st.columns(num_cols)
                    
                    with cols[col_idx]:
                        # Get default value from copied building if available
                        default_value = ''
                        if copy_data is not None and col_name in copy_data.index:
                            default_value = copy_data[col_name]
                            # Handle NaN values
                            if pd.isna(default_value):
                                default_value = ''
                        
                        # Determine input type based on column name
                        # Special handling for ID columns - pre-fill and disable
                        if col_name.lower() in ['building_id', 'id']:
                            new_building_data[col_name] = st.text_input(
                                get_column_translation(col_name),
                                value=str(next_id),
                                key=f"input_{col_name}",
                                disabled=True,  # Make ID read-only
                                help=f"Auto-assigned ID for new building: {next_id}"
                            )
                        elif col_name.lower() in ['name', 'address', 'type']:
                            new_building_data[col_name] = st.text_input(
                                get_column_translation(col_name),
                                value=str(default_value) if default_value != '' else '',
                                key=f"input_{col_name}"
                            )
                        elif col_name.lower() in ['existing', 'is_existing', 'exists']:
                            # Get boolean default value
                            bool_default = False
                            if default_value != '':
                                bool_default = default_value in [True, 1, 'yes', 'Yes', 'YES', 'existing', 'Existing', 'EXISTING', 'true', 'True', 'TRUE']
                            new_building_data[col_name] = st.selectbox(
                                get_column_translation(col_name),
                                options=[True, False],
                                index=0 if bool_default else 1,
                                key=f"input_{col_name}"
                            )
                        elif 'year' in col_name.lower():
                            # Get year default value
                            year_default = 2000
                            if default_value != '':
                                try:
                                    year_default = int(float(default_value))
                                    # Validate range
                                    if year_default < 1800 or year_default > 2100:
                                        year_default = 2000
                                except:
                                    year_default = 2000
                            new_building_data[col_name] = st.number_input(
                                get_column_translation(col_name),
                                min_value=1800,
                                max_value=2100,
                                value=year_default,
                                step=1,
                                key=f"input_{col_name}"
                            )
                        elif any(x in col_name.lower() for x in ['area', 'size', 'volume', 'height', 'units', 'floors']):
                            # Get numeric default value
                            num_default = 0.0
                            if default_value != '':
                                try:
                                    num_default = float(default_value)
                                except:
                                    num_default = 0.0
                            new_building_data[col_name] = st.number_input(
                                get_column_translation(col_name),
                                min_value=0.0,
                                value=num_default,
                                step=1.0 if 'units' in col_name.lower() or 'floors' in col_name.lower() else 10.0,
                                key=f"input_{col_name}"
                            )
                        else:
                            # Default to text input for unknown column types
                            new_building_data[col_name] = st.text_input(
                                get_column_translation(col_name),
                                value=str(default_value) if default_value != '' else '',
                                key=f"input_{col_name}"
                            )
                
                # Add separator and render Financial Parameters if they exist
                if financial_cols:
                    st.markdown("---")  # Soft horizontal line separator
                    st.write("**Finanzielle Parameter**")
                    
                    for idx, col_name in enumerate(financial_cols):
                        col_idx = idx % num_cols
                        if col_idx == 0:
                            cols = st.columns(num_cols)
                        
                        with cols[col_idx]:
                            # Get default value from copied building if available
                            default_value = ''
                            if copy_data is not None and col_name in copy_data.index:
                                default_value = copy_data[col_name]
                                # Handle NaN values
                                if pd.isna(default_value):
                                    default_value = ''
                            
                            # Financial parameters are typically numeric
                            if any(x in col_name.lower() for x in ['cost', 'price', 'rent', 'income', 'expense', 'budget', 'investment', 'depreciation', 'subsidy', 'tax']):
                                # Get numeric default value
                                num_default = 0.0
                                if default_value != '':
                                    try:
                                        num_default = float(default_value)
                                    except:
                                        num_default = 0.0
                                new_building_data[col_name] = st.number_input(
                                    get_column_translation(col_name),
                                    min_value=0.0,
                                    value=num_default,
                                    step=100.0,
                                    key=f"input_{col_name}"
                                )
                            else:
                                # Default to text input
                                new_building_data[col_name] = st.text_input(
                                    get_column_translation(col_name),
                                    value=str(default_value) if default_value != '' else '',
                                    key=f"input_{col_name}"
                                )
                
                # Submit button
                submit_button = st.form_submit_button("Gebäude hinzufügen")
            
            # Handle form submission outside the form
            if submit_button:
                # Validate that at least some key fields are filled
                if not any(new_building_data.values()):
                    st.error("Bitte füllen Sie mindestens einige Gebäudeparameter aus.")
                else:
                    try:
                        # Delete solution if it exists
                        if instance and instance.has_solution:
                            success, message = self.instance_manager.delete_solution_files(instance)
                            if success:
                                st.info(f"✓ Lösung gelöscht: {message}")
                        
                        # Create a new row as a DataFrame
                        new_row = pd.DataFrame([new_building_data])
                        
                        # Append to existing dataframe
                        if not existing_df.empty:
                            updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                        else:
                            updated_df = new_row
                        
                        # Save back to CSV (split if financial data exists)
                        self._save_split_dataframes(updated_df, stock_filepath, financial_filepath)
                        
                        st.success(f"✅ Gebäude erfolgreich hinzugefügt!")
                        # Automatically refresh the page
                        st.rerun()
                            
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen des Gebäudes: {e}")
    
    def _render_building_data_management_section(self, merged_df, stock_filepath, financial_filepath):
        """
        Render specialized data management for building data (handles both stock and financial files)
        
        Args:
            merged_df: Merged DataFrame containing both stock and financial data
            stock_filepath: Path to stock_properties.csv
            financial_filepath: Path to financial_properties.csv
        """
        from utils.file_operations import FileImportExport
        import pandas as pd
        
        st.markdown("---")
        
        
        # ==== IMPORT SECTION (Unified for both files) ====
        st.markdown("### Gebäudedaten importieren")
        st.info("ℹ️ Laden Sie eine oder beide Dateien hoch. Wenn Sie nur eine Datei hochladen, werden Standardwerte (None) für die fehlenden Parameter verwendet.")
        
        self._render_unified_building_import(merged_df, stock_filepath, financial_filepath)
        
        # ==== EXPORT & TEMPLATE SECTIONS ====
        st.markdown("---")
        st.markdown("### Export & Vorlagen")
        
        # Stock Properties row
        st.markdown("##### Gebäudeeigenschaften (Energetische Daten)")
        col_export_stock, col_template_stock = st.columns(2)
        
        with col_export_stock:
            st.markdown("**Daten Export**")
            # Extract stock properties columns for export
            if merged_df.attrs.get('has_financial', False):
                stock_columns = merged_df.attrs.get('stock_columns', [])
                stock_df = merged_df[stock_columns] if stock_columns else merged_df
            else:
                stock_df = merged_df
            self._render_export_section('stock_properties', stock_df)
        
        with col_template_stock:
            st.markdown("**Vorlage**")
            self._render_template_section('stock_properties')
        
        # Financial Properties row
        st.markdown("---")
        st.markdown("##### Finanzdaten")
        col_export_financial, col_template_financial = st.columns(2)
        
        with col_export_financial:
            st.markdown("**Daten Export**")
            # Extract financial properties columns for export
            if merged_df.attrs.get('has_financial', False):
                financial_columns = merged_df.attrs.get('financial_columns', [])
                if financial_columns:
                    # Ensure ID column is included in export
                    id_col = None
                    for col_name in ['building_id', 'id', 'ID', 'Building_ID']:
                        if col_name in merged_df.columns:
                            id_col = col_name
                            break
                    
                    # Add ID column at the beginning if not already there
                    if id_col and id_col not in financial_columns:
                        financial_columns = [id_col] + financial_columns
                    
                    financial_df = merged_df[financial_columns]
                    self._render_export_section('financial_properties', financial_df)
                else:
                    st.info("Keine finanziellen Daten zum Exportieren")
            else:
                st.info("Keine finanziellen Daten verfügbar")
        
        with col_template_financial:
            st.markdown("**Vorlage**")
            self._render_template_section('financial_properties')
    
    def _render_unified_building_import(self, merged_df, stock_filepath, financial_filepath):
        """Render unified import interface for both stock and financial properties"""
        from utils.file_operations import FileImportExport
        import pandas as pd
        
        # Two upload fields side by side
        col1, col2 = st.columns(2)
        
        with col1:
            from config.translations import get_file_translation
            st.markdown("**Gebäudeeigenschaften CSV**")
            stock_uploaded = st.file_uploader(
                f"{get_file_translation('stock_properties.csv')} hochladen",
                type=['csv'],
                key="upload_stock_unified",
                help="CSV-Datei mit energetischen Gebäudedaten hochladen"
            )
        
        with col2:
            st.markdown("**Finanzdaten CSV**")
            financial_uploaded = st.file_uploader(
                f"{get_file_translation('financial_properties.csv')} hochladen",
                type=['csv'],
                key="upload_financial_unified",
                help="CSV-Datei mit Finanzdaten hochladen"
            )
        
        # Show messages immediately after upload
        stock_data = None
        financial_data = None
        stock_validation = None
        financial_validation = None
        
        if stock_uploaded is not None:
            stock_data, stock_validation = FileImportExport.parse_uploaded_csv(stock_uploaded, 'stock_properties')
            
            if stock_data is None:
                st.error(f"❌ Fehler bei den Gebäudeeigenschaften: {stock_validation.get('error', 'Datei konnte nicht geparst werden')}")
            else:
                # Show validation warnings for stock
                if stock_validation.get('warnings'):
                    for warning in stock_validation['warnings']:
                        st.warning(f"Stock properties: {warning}")
                
                # Check if financial is missing
                if financial_uploaded is None:
                    st.info("ℹ️ Finanzielle Eigenschaften wurden nicht bereitgestellt. Standardwerte (None) werden für fehlende finanzielle Parameter verwendet.")
        
        if financial_uploaded is not None:
            financial_data, financial_validation = FileImportExport.parse_uploaded_csv(financial_uploaded, 'financial_properties')
            
            if financial_data is None:
                st.error(f"❌ Fehler bei den finanziellen Eigenschaften: {financial_validation.get('error', 'Datei konnte nicht geparst werden')}")
            else:
                # Show validation warnings for financial
                if financial_validation.get('warnings'):
                    for warning in financial_validation['warnings']:
                        st.warning(f"Finanzielle Eigenschaften: {warning}")
                
                # Check if stock is missing
                if stock_uploaded is None:
                    st.info("ℹ️ Gebäudeeigenschaften wurden nicht bereitgestellt. Standardwerte (None) werden für fehlende energetische Parameter verwendet.")
        
        # If both files are uploaded, validate ID matching
        ids_match = True
        id_errors = []
        
        if stock_data is not None and financial_data is not None:
            # Find ID column in both dataframes
            stock_id_col = None
            for col in ['id', 'building_id', 'ID', 'Building_ID']:
                if col in stock_data.columns:
                    stock_id_col = col
                    break
            
            financial_id_col = None
            for col in ['id', 'building_id', 'ID', 'Building_ID']:
                if col in financial_data.columns:
                    financial_id_col = col
                    break
            
            if stock_id_col and financial_id_col:
                stock_ids = set(stock_data[stock_id_col].dropna().astype(int))
                financial_ids = set(financial_data[financial_id_col].dropna().astype(int))
                
                # Check for mismatches
                only_in_stock = stock_ids - financial_ids
                only_in_financial = financial_ids - stock_ids
                
                if only_in_stock or only_in_financial:
                    ids_match = False
                    if only_in_stock:
                        id_errors.append(f"IDs nur in Gebäudeeigenschaften: {sorted(only_in_stock)}")
                    if only_in_financial:
                        id_errors.append(f"IDs nur in finanziellen Eigenschaften: {sorted(only_in_financial)}")
        
        # Show ID validation errors if any
        if not ids_match:
            st.error("❌ **ID-Abweichung erkannt!**")
            for error in id_errors:
                st.error(f"  • {error}")
            st.error("**Import blockiert:** Gebäude-IDs müssen zwischen Gebäude- und Finanzdateien übereinstimmen.")
            return  # Block import
        
        # Show preview if at least one file is uploaded and valid
        if stock_data is not None or financial_data is not None:
            st.markdown("---")
            st.markdown("**Vorschau der hochgeladenen Daten:**")
            
            if stock_data is not None:
                st.write("**Gebäudeeigenschaften:**")
                st.dataframe(stock_data.head(3), use_container_width=True)
                st.write(f"Gesamtanzahl Zeilen: {len(stock_data)}")
            
            if financial_data is not None:
                st.write("**Finanzdaten:**")
                st.dataframe(financial_data.head(3), use_container_width=True)
                st.write(f"Gesamtanzahl Zeilen: {len(financial_data)}")
            
            # Import options
            st.markdown("---")
            st.info("ℹ️ **Hinzufügen**: Neue Gebäude mit fortlaufenden IDs anhängen (bestehende bleiben erhalten)\n\n**Ersetzen**: Alle bestehenden Gebäude löschen und neue importieren")
            import_action = st.radio(
                "Import-Aktion:",
                ["Concatenate", "Replace"],
                format_func=lambda x: "Hinzufügen" if x == "Concatenate" else "Ersetzen",
                key="import_action_unified"
            )
            
            # Confirm button
            if st.button("✅ Import bestätigen", key="confirm_import_unified", type="primary"):
                try:
                    self._process_unified_building_import(
                        stock_data,
                        financial_data,
                        stock_filepath,
                        financial_filepath,
                        import_action,
                        merged_df
                    )
                    
                    st.success("✅ Gebäudedaten erfolgreich importiert!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Fehler beim Importieren der Daten: {e}")
    
    def _process_unified_building_import(self, stock_data, financial_data, stock_filepath, financial_filepath, action, current_merged_df):
        """Process unified import for both stock and financial data"""
        from utils.file_operations import FileImportExport
        import pandas as pd
        
        # Get current data
        if current_merged_df.attrs.get('has_financial', False):
            stock_columns = current_merged_df.attrs.get('stock_columns', [])
            financial_columns = current_merged_df.attrs.get('financial_columns', [])
            
            # Ensure ID column is included in financial columns
            id_col = None
            for col_name in ['building_id', 'id', 'ID', 'Building_ID']:
                if col_name in current_merged_df.columns:
                    id_col = col_name
                    break
            
            if id_col and id_col not in financial_columns:
                financial_columns = [id_col] + financial_columns
            
            current_stock = current_merged_df[stock_columns] if stock_columns else current_merged_df
            current_financial = current_merged_df[financial_columns] if financial_columns else pd.DataFrame()
        else:
            current_stock = current_merged_df
            current_financial = pd.DataFrame()
        
        # Process stock data
        if stock_data is not None:
            if action == "Concatenate" and not current_stock.empty:
                final_stock = FileImportExport.concatenate_buildings(current_stock, stock_data)
            else:
                final_stock = stock_data.copy()
                # Ensure sequential IDs
                id_col = None
                for col in ['id', 'building_id', 'ID', 'Building_ID']:
                    if col in final_stock.columns:
                        id_col = col
                        break
                if id_col:
                    final_stock[id_col] = range(len(final_stock))
        else:
            # Keep existing stock data
            final_stock = current_stock if action == "Concatenate" else pd.DataFrame()
        
        # Process financial data
        if financial_data is not None:
            if action == "Concatenate" and not current_financial.empty:
                final_financial = FileImportExport.concatenate_buildings(current_financial, financial_data)
            else:
                final_financial = financial_data.copy()
                # Ensure sequential IDs matching stock
                id_col = None
                for col in ['id', 'building_id', 'ID', 'Building_ID']:
                    if col in final_financial.columns:
                        id_col = col
                        break
                if id_col:
                    final_financial[id_col] = range(len(final_financial))
        else:
            # Keep existing financial data or create empty with matching IDs
            if action == "Replace" or current_financial.empty:
                # Create default financial data with None values
                if not final_stock.empty:
                    stock_id_col = None
                    for col in ['id', 'building_id', 'ID', 'Building_ID']:
                        if col in final_stock.columns:
                            stock_id_col = col
                            break
                    if stock_id_col:
                        final_financial = pd.DataFrame({'id': final_stock[stock_id_col]})
                        # Add other financial columns with None values
                        financial_cols = FILE_FORMATS['financial_properties']['required_columns']
                        for col in financial_cols:
                            if col not in final_financial.columns:
                                final_financial[col] = None
                else:
                    final_financial = pd.DataFrame()
            else:
                final_financial = current_financial
        
        # Save both files
        if not final_stock.empty:
            final_stock.to_csv(stock_filepath, index=False, sep=',')
        
        if not final_financial.empty:
            final_financial.to_csv(financial_filepath, index=False, sep=';')
    
    def _render_data_management_section(self, file_type, current_data, filepath, allow_concat=False, financial_filepath=None):
        """
        Render Import/Export/Template buttons for data management
        
        Args:
            file_type: Type of data ('stock_properties', 'financial_properties', 'general_finances', 'portfolio_caps')
            current_data: Current DataFrame or dict
            filepath: Path to save file
            allow_concat: Whether to allow concatenation (True for buildings only)
            financial_filepath: Financial properties file path (for buildings only)
        """
        from utils.file_operations import FileImportExport
        
        st.markdown("---")
        
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Daten Import**")
            self._render_import_section(file_type, current_data, filepath, allow_concat, financial_filepath)
        
        with col2:
            st.markdown("**Daten Export**")
            self._render_export_section(file_type, current_data)
        
        with col3:
            st.markdown("**Download Vorlage**")
            self._render_template_section(file_type)
    
    def _render_import_section(self, file_type, current_data, filepath, allow_concat, financial_filepath=None):
        """Render import file uploader and processing"""
        from utils.file_operations import FileImportExport
        import pandas as pd
        
        format_spec = FILE_FORMATS.get(file_type, {})
        file_format = format_spec.get('format', 'csv')
        filename = format_spec.get('filename', f'{file_type}.{file_format}')
        
        # Import translation function
        from config.translations import get_file_translation
        
        # File uploader with translated filename
        uploaded_file = st.file_uploader(
            f"Hochladen: {get_file_translation(filename)}",
            type=[file_format],
            key=f"upload_{file_type}",
            help=f"Bitte laden Sie eine {file_format.upper()}-Datei hoch, um Daten zu importieren"
        )
        
        if uploaded_file is not None:
            # Parse the file
            if file_format == 'csv':
                imported_data, validation = FileImportExport.parse_uploaded_csv(uploaded_file, file_type)
            else:  # json
                imported_data, validation = FileImportExport.parse_uploaded_json(uploaded_file, file_type)
            
            if imported_data is None:
                st.error(validation.get('error', 'Failed to parse file'))
                return
            
            # Show validation warnings
            if validation.get('warnings'):
                for warning in validation['warnings']:
                    st.warning(warning)
            
            # Show preview
            st.write("**Vorschau der importierten Daten:**")
            if isinstance(imported_data, pd.DataFrame):
                st.dataframe(imported_data.head(5), use_container_width=True)
                st.write(f"Gesamtanzahl Zeilen: {len(imported_data)}")
            else:
                st.json(imported_data)
            
            # Import options and confirmation
            if allow_concat:
                st.info("ℹ️ **Hinzufügen**: Neue Gebäude mit fortlaufenden IDs anhängen (bestehende bleiben erhalten)\n\n**Ersetzen**: Alle bestehenden Gebäude löschen und neue importieren")
                import_action = st.radio(
                    "Import-Aktion:",
                    ["Concatenate", "Replace"],
                    format_func=lambda x: "Hinzufügen" if x == "Concatenate" else "Ersetzen",
                    key=f"import_action_{file_type}"
                )
            else:
                # Check for unsaved changes
                if file_type in ['general_finances', 'portfolio_caps']:
                    session_key = f'{file_type.replace("_", "")}_edited'
                    if session_key in st.session_state:
                        st.warning("⚠️ Sie haben ungespeicherte Änderungen. Beim Import gehen diese verloren.")
                
                import_action = st.radio(
                    "Import bestätigen:",
                    ["Replace existing data"],
                    format_func=lambda x: "Bestehende Daten ersetzen",
                    key=f"import_action_{file_type}"
                )
            
            # Confirm button
            if st.button(f"✅ Import bestätigen", key=f"confirm_import_{file_type}", type="primary"):
                try:
                    if file_format == 'csv':
                        self._process_csv_import(
                            imported_data, 
                            file_type, 
                            filepath, 
                            import_action,
                            current_data,
                            financial_filepath
                        )
                    else:  # json
                        self._process_json_import(
                            imported_data,
                            file_type,
                            filepath,
                            import_action
                        )
                    
                    st.success(f"✅ Daten erfolgreich importiert!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Fehler beim Importieren der Daten: {e}")
    
    def _process_csv_import(self, imported_df, file_type, filepath, action, current_data, financial_filepath):
        """Process CSV import based on action"""
        from utils.file_operations import FileImportExport
        import pandas as pd
        
        if action == "Concatenate" and not current_data.empty:
            # Concatenate with existing data
            final_df = FileImportExport.concatenate_buildings(current_data, imported_df)
        else:
            # Replace existing data
            final_df = imported_df.copy()
            # Ensure sequential IDs starting from 0
            id_col = None
            for col_name in ['building_id', 'id', 'ID', 'Building_ID']:
                if col_name in final_df.columns:
                    id_col = col_name
                    break
            if id_col:
                final_df[id_col] = range(len(final_df))
        
        # Save based on file type
        if file_type == 'stock_properties':
            # Save using the split method if financial data exists
            if financial_filepath:
                self._save_split_dataframes(final_df, filepath, financial_filepath)
            else:
                final_df.to_csv(filepath, index=False)
        else:  # financial_properties
            delimiter = FILE_FORMATS[file_type].get('delimiter', ';')
            final_df.to_csv(filepath, index=False, sep=delimiter)
    
    def _process_json_import(self, imported_data, file_type, filepath, action):
        """Process JSON import"""
        import json
        
        # Clear session state for this file type
        session_key_edited = f'{file_type.replace("_", "")}_edited'
        session_key_original = f'{file_type.replace("_", "")}_original'
        
        if session_key_edited in st.session_state:
            del st.session_state[session_key_edited]
        if session_key_original in st.session_state:
            del st.session_state[session_key_original]
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(imported_data, indent=2, fp=f)
    
    def _render_export_section(self, file_type, current_data):
        """Render export download button"""
        from utils.file_operations import FileImportExport
        import pandas as pd
        
        format_spec = FILE_FORMATS.get(file_type, {})
        file_format = format_spec.get('format', 'csv')
        filename = format_spec.get('filename', f'{file_type}.{file_format}')
        
        # Prepare export data
        if isinstance(current_data, pd.DataFrame):
            export_string = FileImportExport.export_csv(current_data, file_type)
            mime_type = 'text/csv'
        else:  # dict
            # Check if we have edited data in session state
            session_key = f'{file_type.replace("_", "")}_edited'
            if session_key in st.session_state:
                export_data = st.session_state[session_key]
            else:
                export_data = current_data
            
            export_string = FileImportExport.export_json(export_data, file_type)
            mime_type = 'application/json'
        
        # Download button with translated name
        from config.translations import get_file_translation
        st.download_button(
            label=f"Download {get_file_translation(filename)}",
            data=export_string,
            file_name=filename,  # Keep original filename for actual file
            mime=mime_type,
            key=f"export_{file_type}",
            use_container_width=True
        )
    
    def _render_template_section(self, file_type):
        """Render template download buttons"""
        from utils.file_operations import FileImportExport
        
        format_spec = FILE_FORMATS.get(file_type, {})
        file_format = format_spec.get('format', 'csv')
        filename = format_spec.get('filename', f'{file_type}.{file_format}')
        
        # Generate template
        if file_format == 'csv':
            template_string = FileImportExport.generate_csv_template(file_type)
            mime_type = 'text/csv'
        else:  # json
            template_string = FileImportExport.generate_json_template(file_type)
            mime_type = 'application/json'
        
        # Download button for template file with translated name
        from config.translations import get_file_translation
        st.download_button(
            label=f"Vorlage {get_file_translation(filename)}",
            data=template_string,
            file_name=filename,
            mime=mime_type,
            key=f"template_{file_type}",
            use_container_width=True
        )
        
        # Download button for README
        readme_string = FileImportExport.generate_readme()
        st.download_button(
            label="README.md",
            data=readme_string,
            file_name="README.md",
            mime="text/markdown",
            key=f"readme_{file_type}",
            use_container_width=True,
            help="Download Anleitungen für die Verwendung von Vorlagen"
        )
    
    def _render_data_summary(self, data_status):
        """Render overall data availability summary"""
        
        statuses = [data_status['building'], data_status['financial'], data_status['portfolio']]
        
        # Count status types
        green_count = statuses.count('green')
        yellow_count = statuses.count('yellow')
        red_count = statuses.count('red')
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Complete", f"{green_count}/3", delta=None)
        
        with col2:
            st.metric("Partial", f"{yellow_count}/3", delta=None)
        
        with col3:
            st.metric("Missing", f"{red_count}/3", delta=None)
        
        # Overall status
        if red_count > 0:
            overall = 'red'
            st.error("⛔ Cannot run optimization: Critical data is missing")
        elif yellow_count > 0:
            overall = 'yellow'
            st.warning("⚠️ Optimization may run with reduced functionality")
        else:
            overall = 'green'
            st.success("✅ All data available - Ready for optimization")
        
        return overall
    
    def _render_config_analysis(self, instance: InstanceMetadata):
        """Render configuration file analysis"""
        
        st.subheader("Configuration Files")
        
        from config.translations import get_file_translation
        for filename, filepath in instance.config_files.items():
            with st.expander(f"{get_file_translation(filename)}"):
                
                if not filepath.exists():
                    st.error(f"File not found: {filepath}")
                    continue
                
                # File info
                file_stat = filepath.stat()
                file_size = file_stat.st_size
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("File Size", f"{file_size:,} bytes")
                with col2:
                    from datetime import datetime
                    mod_time = datetime.fromtimestamp(file_stat.st_mtime)
                    st.metric("Modified", mod_time.strftime("%Y-%m-%d %H:%M"))
                
                # File preview
                try:
                    if filename.endswith('.csv'):
                        self._preview_csv_file(filepath)
                    elif filename.endswith('.json'):
                        self._preview_json_file(filepath)
                    else:
                        from config.translations import get_file_translation
                        st.info(f"Vorschau nicht verfügbar für {get_file_translation(filename)}")
                except Exception as e:
                    st.error(f"Error reading file: {e}")
    
    def _preview_csv_file(self, filepath):
        """Preview CSV file contents"""
        import pandas as pd
        
        try:
            df = pd.read_csv(filepath)
            
            st.write(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
            
            if not df.empty:
                # Show basic info
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Columns:**")
                    for col in df.columns:
                        st.write(f"- {col}")
                
                with col2:
                    st.write("**Data Types:**")
                    for col, dtype in df.dtypes.items():
                        st.write(f"- {col}: {dtype}")
                
                # Show preview
                st.write("**Preview (first 5 rows):**")
                st.dataframe(df.head(), use_container_width=True)
            else:
                st.warning("CSV file is empty")
                
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
    
    def _preview_json_file(self, filepath):
        """Preview JSON file contents"""
        import json
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            st.write(f"**Type:** {type(data).__name__}")
            
            if isinstance(data, dict):
                st.write(f"**Keys:** {len(data)} items")
                
                # Show keys
                st.write("**Top-level keys:**")
                for key in list(data.keys())[:10]:  # Show first 10 keys
                    value_type = type(data[key]).__name__
                    st.write(f"- {key}: {value_type}")
                
                if len(data) > 10:
                    st.write(f"... and {len(data) - 10} more")
            
            elif isinstance(data, list):
                st.write(f"**Length:** {len(data)} items")
                if data:
                    st.write(f"**Item type:** {type(data[0]).__name__}")
            
            # Show formatted JSON (limited)
            st.write("**Content preview:**")
            
            # Limit size for display
            json_str = json.dumps(data, indent=2)
            if len(json_str) > 2000:
                json_str = json_str[:2000] + "\n... (truncated)"
            
            st.code(json_str, language="json")
            
        except Exception as e:
            st.error(f"Error reading JSON: {e}")
    
    def _render_empty_building_data_template(self):
        """Render empty building data template with column headers"""
        import pandas as pd
        
        # Create empty DataFrame with all columns from FILE_FORMATS
        required_cols = FILE_FORMATS['stock_properties']['required_columns']
        optional_cols = FILE_FORMATS['stock_properties']['optional_columns']
        all_cols = required_cols + optional_cols
        
        # Create a single empty row with zeros/None
        empty_row = {}
        column_types = FILE_FORMATS['stock_properties']['column_types']
        
        for col in all_cols:
            col_type = column_types.get(col, 'str')
            if col_type == 'int':
                empty_row[col] = 0
            elif col_type == 'float':
                empty_row[col] = 0.0
            elif col_type == 'bool':
                empty_row[col] = False
            else:
                empty_row[col] = ''
        
        df = pd.DataFrame([empty_row])
        
        st.markdown("**Gebäudeeigenschaften (stock_properties.csv)**")
        st.dataframe(df, use_container_width=True, hide_index=True, height=150)
        
        # Also show financial properties template
        from config.translations import get_file_translation
        st.markdown(f"**Finanzdaten ({get_file_translation('financial_properties.csv')})**")
        fin_required_cols = FILE_FORMATS['financial_properties']['required_columns']
        fin_optional_cols = FILE_FORMATS['financial_properties']['optional_columns']
        fin_all_cols = fin_required_cols + fin_optional_cols
        
        fin_empty_row = {}
        fin_column_types = FILE_FORMATS['financial_properties']['column_types']
        
        for col in fin_all_cols:
            col_type = fin_column_types.get(col, 'str')
            if col_type == 'int':
                fin_empty_row[col] = 0
            elif col_type == 'float':
                fin_empty_row[col] = 0.0
            elif col_type == 'bool':
                fin_empty_row[col] = False
            else:
                fin_empty_row[col] = ''
        
        fin_df = pd.DataFrame([fin_empty_row])
        st.dataframe(fin_df, use_container_width=True, hide_index=True, height=150)
    
    def _render_empty_general_finances_template(self):
        """Render empty general finances template by creating the file if it doesn't exist"""
        import json
        
        # Create empty template with zeros instead of template values
        schema = FILE_FORMATS['general_finances']['schema']
        
        def create_empty_from_schema(schema_obj):
            """Recursively create empty structure from schema"""
            result = {}
            for key, value in schema_obj.items():
                if isinstance(value, dict):
                    # Nested structure
                    result[key] = create_empty_from_schema(value)
                elif value == 'int':
                    result[key] = 0
                elif value == 'float':
                    result[key] = 0.0
                elif value == 'str':
                    result[key] = ''
                elif value == 'bool':
                    result[key] = False
                else:
                    result[key] = None
            return result
        
        empty_data = create_empty_from_schema(schema)
        
        # Initialize session state for template
        if 'financial_data_original' not in st.session_state:
            st.session_state['financial_data_original'] = empty_data.copy()
        if 'financial_data_edited' not in st.session_state:
            st.session_state['financial_data_edited'] = empty_data.copy()
        
        # Display using the same method as real files
        st.info("📝 Leere Vorlage - bearbeiten und speichern, um die Datei zu erstellen")
        self._render_editable_dict_fields(st.session_state['financial_data_edited'], None, prefix="")
        
        st.markdown("---")
        st.markdown("### Download Vorlage")
        self._render_template_section('general_finances')
    
    def _render_empty_portfolio_caps_template(self):
        """Render empty portfolio caps template"""
        import json
        
        # Create empty template based on schema
        schema = FILE_FORMATS['portfolio_caps']['schema']
        
        def create_empty_from_schema(schema_obj):
            """Recursively create empty structure from schema"""
            result = {}
            for key, value in schema_obj.items():
                if isinstance(value, dict):
                    # Nested structure
                    result[key] = create_empty_from_schema(value)
                elif value == 'int':
                    result[key] = 0
                elif value == 'float':
                    result[key] = 0.0
                elif value == 'str':
                    result[key] = ''
                elif value == 'bool':
                    result[key] = False
                else:
                    result[key] = None
            return result
        
        empty_data = create_empty_from_schema(schema)
        
        # Initialize session state for template
        if 'portfolio_caps_original' not in st.session_state:
            st.session_state['portfolio_caps_original'] = empty_data.copy()
        if 'portfolio_caps_edited' not in st.session_state:
            st.session_state['portfolio_caps_edited'] = empty_data.copy()
        
        # Display using the same method as real files
        st.info("📝 Leere Vorlage - bearbeiten und speichern, um die Datei zu erstellen")
        self._render_portfolio_caps_fields(st.session_state['portfolio_caps_edited'], None)
        
        st.markdown("---")
        st.markdown("### Download Vorlage")
        self._render_template_section('portfolio_caps')

class InstanceCreatorPage:
    """Page for creating new instances"""
    
    def __init__(self, instance_manager: InstanceManager):
        self.instance_manager = instance_manager
        self.instance_creator = InstanceCreator()
    
    def render(self):
        """Render the instance creator page"""

        st.header("Neues Portfolio erstellen")
        st.markdown("Erstellen Sie neue Portfolio-Datensätze mit benutzerdefinierten Parametern und Konfigurationen.")
        
        self.instance_creator.render()
        
        # Additional future functionality placeholders
        st.markdown("---")
        st.subheader("🔮 Geplante Funktionen")
        
        st.info("""
        **Geplante Funktionalitäten:**
        - Interaktiver Parameter-Editor
        - Gebäudebestandskonfiguration
        - Finanzparameter-Einrichtung
        - Portfolioeinschränkungsdefinition
        - Vorlagenbasierte Instanzerstellung
        - Instanzklonen und -modifikation
        """)

class ComparisonPage:
    """Page for comparing multiple instances"""
    
    def __init__(self, instance_manager: InstanceManager):
        self.instance_manager = instance_manager
    
    def render(self):
        """Render the comparison page"""

        st.header("Vergleich der Ergebnisse")
        st.markdown("Vergleichen Sie die Optimierungsergebnisse mehrerer Instanzen.")

        st.info("Die Funktionalität zum Vergleich mehrerer Instanzen wird in einer zukünftigen Version implementiert.")

        # Placeholder for future functionality
        st.subheader("🔮 Geplante Funktionen")
        
        st.markdown("""
        **# Vergleichsmöglichkeiten:**
        - Side-by-side Ergebnisvergleich
        - Technologieportfolio-Unterschiede
        - Kosten-Nutzen-Analyse
        - Performance Vergleich
        - Detaillierte Vergleichsberichte
        - Vergleichsexportoptionen
        """)
