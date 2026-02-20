"""
Sidebar navigation component
"""
import streamlit as st
from typing import Dict, List

class Sidebar:
    """Main sidebar navigation component"""
    
    def __init__(self, app_title: str, app_icon: str):
        self.app_title = app_title
        self.app_icon = app_icon
        
    def render(self) -> str:
        """Render sidebar and return selected page"""
        
        with st.sidebar:
            # App header
            st.title(f"{self.app_icon} {self.app_title}")
            st.markdown("---")
            
            # Navigation menu
            st.subheader("Navigation")
            
            page = st.radio(
                "Wähle eine Seite:",
                [
                    "Portfolio-Übersicht",
                    "Optimierungsergebnisse", 
                    "Neues Portfolio"
                ],
                key="navigation_radio"
            )
            
            # Footer
            st.markdown("---")
            st.caption("OptiPort WebApp Prototyp")
            
        return page

class StatusIndicator:
    """Component for showing status indicators"""
    
    @staticmethod
    def render_solution_status(has_solution: bool, solution_status: str = None):
        """Render solution status indicator"""
        if has_solution:
            if solution_status == "OPTIMAL":
                st.success("✅ Optimale Lösung gefunden")
            elif solution_status == "FEASIBLE":
                st.warning("⚠️ Zulässige Lösung gefunden")
            else:
                st.info("ℹ️ Lösung verfügbar")
        else:
            st.error("❌ Keine Lösung verfügbar")
    
    @staticmethod
    def render_instance_status(validation: Dict[str, bool]):
        """Render instance validation status"""
        if validation.get("is_complete", False):
            st.success("✅ Instanz ist vollständig und bereit")
        else:
            missing = []
            if not validation.get("has_directory", True):
                missing.append("Verzeichnis")
            if not validation.get("has_config_files", True):
                missing.append("Konfigurationsdateien")
            if not validation.get("has_required_files", True):
                missing.append("erforderliche Dateien")
                
            st.warning(f"⚠️ Fehlende Instanzteile: {', '.join(missing)}")

class MetricsDisplay:
    """Component for displaying key metrics"""
    
    @staticmethod
    def render_solution_metrics(solution):
        """Render key solution metrics"""
        if not solution:
            st.warning("Keine Lösungsdaten verfügbar")
            return
            
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.metric(
                "Zielfunktionswert",
                f"{solution.objective_value:,.0f} k€",
                help="Gesamter Optimierungszielfunktionswert"
            )
            
        with col2:
            # More informative solution status display
            status = solution.solution_status
            
            if status == "OPTIMAL":
                st.success("✅ **Status: OPTIMAL**")
                st.caption("Lösung erfüllt alle Nebenbedingungen am globalen Optimum")
            elif status == "FEASIBLE":
                st.warning("⚠️ **Status: ZULÄSSIG**")
                st.caption("Lösung erfüllt alle Nebenbedingungen, Optimalität nicht garantiert")
            else:
                st.info("ℹ️ **Status: VERFÜGBAR**")
                st.caption("Lösung verfügbar, Optimalitätsstatus unbekannt")
