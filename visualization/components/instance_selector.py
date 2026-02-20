"""
Instance selector component for choosing optimization instances
"""
import streamlit as st
from typing import List, Optional, Callable
import pandas as pd

from core.data_models import InstanceMetadata
from core.instance_manager import InstanceManager

class InstanceSelector:
    """Component for selecting optimization instances"""
    
    def __init__(self, instance_manager: InstanceManager):
        self.instance_manager = instance_manager
        
    def render(self, show_management_sections: bool = False) -> Optional[InstanceMetadata]:
        """Render instance selector and return selected instance
        
        Args:
            show_management_sections: If True, show creation/deletion sections below
        """
        
        st.subheader("Aktuelle Auswahl")
        
        # Get available instances
        instances = self.instance_manager.discover_instances()
        
        if not instances:
            st.warning("Keine Instanzen im angegebenen Verzeichnis gefunden.")
            st.info("Bitte stellen Sie sicher, dass Instanzen im Verzeichnis `/run/use_cases/` existieren")
            # Show creation options even if no instances exist
            if show_management_sections:
                st.markdown("---")
                self._render_instance_creation_section(instances)
            return None
        
        # Instance selection
        instance_names = [inst.name for inst in instances]
        
        # Check if a newly created instance should be selected
        default_index = 0
        if 'newly_created_instance' in st.session_state:
            new_instance_name = st.session_state.newly_created_instance
            if new_instance_name in instance_names:
                default_index = instance_names.index(new_instance_name)
            # Clear the flag after using it
            del st.session_state.newly_created_instance
        
        selected_name = st.selectbox(
            "Verfügbare Portfolio-Datensätze:",
            instance_names,
            index=default_index,
            key="instance_selector"
        )
        
        if not selected_name:
            return None
        
        # Find selected instance
        selected_instance = next(
            (inst for inst in instances if inst.name == selected_name), 
            None
        )
        
        if selected_instance:
            # Display instance information
            self._display_instance_info(selected_instance)
            
        return selected_instance
    
    def _render_instance_creation_section(self, existing_instances: List[InstanceMetadata]):
        """Render the instance creation and copy section"""
        
        st.subheader("Neue Portfolio-Datensätze")
        
        # Create two columns for the two options
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Portfolio-Datensatz erstellen")
            with st.form("create_new_instance_form", clear_on_submit=False):
                new_instance_name = st.text_input(
                    "Name des neuen Portfolio-Datensatzes",
                    key="new_instance_name",
                    help="Geben Sie einen eindeutigen Namen für den neuen Portfolio-Datensatz ein (nur alphanumerische Zeichen, Bindestriche und Unterstriche)"
                )

                create_button = st.form_submit_button("Neuen Portfolio-Datensatz erstellen", use_container_width=True)

                if create_button:
                    if new_instance_name:
                        success, message, new_instance = self.instance_manager.create_new_instance(new_instance_name)
                        
                        if success:
                            st.success(message)
                            st.info(f"Portfolio-Datensatz erstellt unter: `{new_instance.path}`")
                            # Set the newly created instance to be selected after rerun
                            st.session_state.newly_created_instance = new_instance.name
                            # Trigger a rerun to update the instance list
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("Bitte geben Sie einen Namen für den neuen Portfolio-Datensatz ein")
        
        with col2:
            st.markdown("##### Existierenden Portfolio-Datensatz kopieren")
            
            if existing_instances:
                with st.form("copy_instance_form", clear_on_submit=False):
                    # Source instance selection
                    source_instance_names = [inst.name for inst in existing_instances]
                    source_instance_name = st.selectbox(
                        "Kopieren von",
                        source_instance_names,
                        key="source_instance_selector"
                        )
                    
                    # New name for the copy
                    copy_instance_name = st.text_input(
                            "Neuer Name des Portfolio-Datensatzes",
                            key="copy_instance_name",
                            help="Geben Sie einen eindeutigen Namen für den neuen Portfolio-Datensatz ein"
                        )
                    
                    # Option to include solution
                    include_solution = st.checkbox(
                        "Lösungsdateien einbeziehen",
                        value=False,
                        key="include_solution_checkbox",
                        help="Lösungsdateien zusammen mit den Konfigurationsdateien kopieren"
                    )

                    copy_button = st.form_submit_button("Portfolio-Datensatz kopieren", use_container_width=True)

                    # Handle form submission outside the form
                    if copy_button:
                        if copy_instance_name:
                            # Store copy request in session state for confirmation
                            st.session_state.pending_copy = {
                                'source_name': source_instance_name,
                                'new_name': copy_instance_name,
                                'include_solution': include_solution
                            }
                            st.rerun()
                        else:
                            st.warning("Bitte geben Sie einen Namen für den neuen Portfolio-Datensatz ein")
                    
                    # Show confirmation dialog if there's a pending copy
                    if 'pending_copy' in st.session_state:
                        pending = st.session_state.pending_copy
                        st.warning(f"⚠️ Sie sind dabei, '{pending['source_name']}' zu '{pending['new_name']}' zu kopieren.")
                        
                        col_confirm1, col_confirm2 = st.columns(2)
                        
                        with col_confirm1:
                            if st.button("✅ Bestätigen", key="confirm_copy_btn", use_container_width=True):
                                # Find the source instance
                                source_instance = next(
                                    (inst for inst in existing_instances if inst.name == pending['source_name']),
                                    None
                                )
                                
                                if source_instance:
                                    success, message, new_instance = self.instance_manager.copy_instance(
                                        source_instance,
                                        pending['new_name'],
                                        include_solution=pending['include_solution']
                                    )
                                    
                                    if success:
                                        # Set the newly copied instance to be selected after rerun
                                        st.session_state.newly_created_instance = new_instance.name
                                        # Clear pending copy
                                        del st.session_state.pending_copy
                                        st.success(message)
                                        # Trigger a rerun to update the instance list
                                        st.rerun()
                                    else:
                                        st.error(message)
                                        del st.session_state.pending_copy
                        
                        with col_confirm2:
                            if st.button("❌ Abbrechen", key="cancel_copy_btn", use_container_width=True):
                                del st.session_state.pending_copy
                                st.rerun()
            else:
                st.info("Kein Portfolio-Datensatz zum Kopieren verfügbar")
    
    def _render_delete_instance_section(self, selected_instance: Optional[InstanceMetadata], existing_instances: List[InstanceMetadata]):
        """Render the delete instance section with confirmation"""
        
        st.subheader("Portfolio-Datensatz löschen")
        
        if not selected_instance:
            st.info("Kein Portfolio-Datensatz ausgewählt")
            return
        
        st.warning(f"⚠️ Portfolio-Datensatz löschen: **{selected_instance.name}**")
        
        # Check if there's a pending delete confirmation
        if 'pending_delete' in st.session_state and st.session_state.pending_delete == selected_instance.name:
            st.error(f"🗑️ Sind Sie sicher, dass Sie '{selected_instance.name}' dauerhaft löschen möchten? Dies kann nicht rückgängig gemacht werden!")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Löschen bestätigen", key="confirm_delete_btn", use_container_width=True):
                    success, message = self.instance_manager.delete_instance(selected_instance)
                    
                    if success:
                        # Clear the pending delete
                        del st.session_state.pending_delete
                        st.success(message)
                        # Trigger a rerun to update the instance list
                        st.rerun()
                    else:
                        st.error(message)
                        del st.session_state.pending_delete
            
            with col2:
                if st.button("❌ Abbrechen", key="cancel_delete_btn", use_container_width=True):
                    del st.session_state.pending_delete
                    st.rerun()
        else:
            if st.button(f"🗑️'{selected_instance.name}' löschen", key="delete_instance_btn", use_container_width=False):
                # Store delete request in session state for confirmation
                st.session_state.pending_delete = selected_instance.name
                st.rerun()
    
    def _display_instance_info(self, instance: InstanceMetadata):
        """Display detailed information about the selected instance"""
        
        st.write(f"**Pfad**: `{instance.path}`")
        st.write(f"**Optimierungsergebnis**: {'✅ Verfügbar' if instance.has_solution else '❌ Nicht verfügbar'}")
    
    def _render_instance_summary(self, instances: List[InstanceMetadata]):
        """Render a simple summary of instances without expander"""
        
        # Create summary dataframe
        data = []
        for inst in instances:
            validation = self.instance_manager.validate_instance(inst)
            
            data.append({
                "Name": inst.name,
                "Buildings": inst.num_buildings or "Unknown",
                "Time Periods": inst.num_time_periods or "Unknown", 
                "Has Solution": "✅" if inst.has_solution else "❌",
                "Complete": "✅" if validation["is_complete"] else "❌",
                "Modified": inst.modified_date.strftime("%Y-%m-%d") if inst.modified_date else "Unknown"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    def _render_instances_table(self, instances: List[InstanceMetadata]):
        """Render a table overview of all instances"""
        
        # Create summary dataframe  
        data = []
        for inst in instances:
            validation = self.instance_manager.validate_instance(inst)
            
            data.append({
                "Name": inst.name,
                "Buildings": inst.num_buildings or "Unknown",
                "Time Periods": inst.num_time_periods or "Unknown", 
                "Has Solution": "✅" if inst.has_solution else "❌",
                "Complete": "✅" if validation["is_complete"] else "❌",
                "Modified": inst.modified_date.strftime("%Y-%m-%d") if inst.modified_date else "Unknown"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    def _render_instance_details(self, instance: InstanceMetadata):
        """Render detailed information about the selected instance"""
        
        st.subheader(f"Instance: {instance.name}")
        
        # Basic info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Buildings", instance.num_buildings or "Unknown")
            
        with col2:
            st.metric("Time Periods", instance.num_time_periods or "Unknown")
            
        with col3:
            status = "✅ Available" if instance.has_solution else "❌ Missing"
            st.metric("Solution", status)
        
        # Validation status
        validation = self.instance_manager.validate_instance(instance)
        
        st.subheader("Instance Validation")
        val_col1, val_col2 = st.columns(2)
        
        with val_col1:
            st.write("**Directory exists:**", "✅" if validation["has_directory"] else "❌")
            st.write("**Has config files:**", "✅" if validation["has_config_files"] else "❌")
            
        with val_col2:
            st.write("**Has required files:**", "✅" if validation["has_required_files"] else "❌")
            st.write("**Instance complete:**", "✅" if validation["is_complete"] else "❌")
        
        # Configuration files
        if instance.config_files:
            with st.expander("📄 Konfigurationsdateien", expanded=False):
                from config.translations import get_file_translation
                for filename, filepath in instance.config_files.items():
                    file_size = filepath.stat().st_size if filepath.exists() else 0
                    translated_name = get_file_translation(filename)
                    st.write(f"- **{translated_name}**: {file_size:,} bytes")
        
        # Description and metadata
        if instance.description:
            st.info(f"**Description:** {instance.description}")
        
        # Path information
        with st.expander("File Paths", expanded=False):
            st.code(f"Instance path: {instance.path}")
            if instance.solution_path:
                st.code(f"Solution path: {instance.solution_path}")

class InstanceCreator:
    """Component for creating new instances (placeholder for future implementation)"""
    
    def render(self):
        """Render the instance creator (placeholder)"""
        st.subheader("Neuen Portfolio-Datensatz erstellen")
        st.info("Die Funktion zur Erstellung von Portfolio-Datensätzen wird in einer zukünftigen Version implementiert.")

        with st.form("instance_creator"):
            name = st.text_input("Name des Portfolio-Datensatzes")
            description = st.text_area("Beschreibung")
            
            col1, col2 = st.columns(2)
            with col1:
                num_buildings = st.number_input("Anzahl der Gebäude", min_value=1, value=1)
            with col2:
                num_periods = st.number_input("Zeiträume", min_value=1, value=3)
            
            submitted = st.form_submit_button("Erstelle Portfolio-Datensatz")
            
            if submitted:
                st.warning("Die Erstellung von Portfolio-Datensätzen ist noch nicht implementiert. Diese Funktion wird in einer zukünftigen Version verfügbar sein.")
