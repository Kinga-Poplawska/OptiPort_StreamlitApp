"""
New Portfolio page – explains how to set up a new use case for OptiPort.
This is an informational page guiding users through the process.
"""
import streamlit as st
from config.app_config import USE_CASES_PATH, get_processed_results_path


class NewPortfolioPage:
    """Informational page explaining how to create a new use case / portfolio."""

    def render(self):
        st.header("📁 Neues Portfolio")
        st.markdown(
            "Laden Sie hier eine CSV-Datei hoch, um ein neues Portfolio zu erstellen."
        )
        st.markdown("---")

        # File uploader for CSV
        uploaded_file = st.file_uploader(
            "Portfolio CSV-Datei hochladen",
            type=["csv"],
            help="Wählen Sie eine CSV-Datei mit Ihrem Portfolio aus"
        )

        if uploaded_file is not None:
            st.info(
                "ℹ️ Diese Funktion wird in Zukunft verfügbar sein. "
                "Die Möglichkeit, Portfolios über CSV-Upload zu erstellen, "
                "befindet sich derzeit in Entwicklung."
            )


