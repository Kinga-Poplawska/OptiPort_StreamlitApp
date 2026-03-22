"""
Main Streamlit application for OptiPort MILP Optimization Interface
"""
import streamlit as st
import logging
import sys
import warnings
from pathlib import Path

# Force black fonts on all Plotly charts while keeping Streamlit's theme
_original_plotly_chart = st.plotly_chart
def _plotly_chart_black_font(fig, *args, **kwargs):
    if hasattr(fig, "update_layout"):
        fig.update_layout(
            font=dict(color="black"),
            xaxis=dict(title_font_color="black", tickfont_color="black"),
            yaxis=dict(title_font_color="black", tickfont_color="black"),
        )
        if hasattr(fig, "for_each_xaxis"):
            fig.for_each_xaxis(
                lambda axis: axis.update(title_font_color="black", tickfont_color="black")
            )
        if hasattr(fig, "for_each_yaxis"):
            fig.for_each_yaxis(
                lambda axis: axis.update(title_font_color="black", tickfont_color="black")
            )
        if getattr(fig.layout, "annotations", None):
            fig.update_annotations(font=dict(color="black"))
    return _original_plotly_chart(fig, *args, **kwargs)
st.plotly_chart = _plotly_chart_black_font
# Bedingte PyCharm Remote Debugger Verbindung
try:
    import pydevd_pycharm
    # Teste ob der Remote Debugger verfügbar ist
    pydevd_pycharm.settrace('localhost', port=8502, stdout_to_server=True, stderr_to_server=True, suspend=False)
    print("🐛 Mit PyCharm Remote Debugger verbunden")
except ImportError:
    # pydevd_pycharm nicht installiert - normaler Betrieb
    pydevd_pycharm = None  # noqa: F841
except ConnectionRefusedError:
    # Remote Debugger nicht aktiv - normaler Betrieb
    print("ℹ️ PyCharm Remote Debugger nicht aktiv - normaler Betrieb")
except Exception as e:
    # Andere Fehler - normaler Betrieb
    print(f"ℹ️ Debug-Verbindung fehlgeschlagen: {e}")

# Suppress Streamlit warnings when running without streamlit run
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")
warnings.filterwarnings("ignore", message=".*Session state does not function.*")

# Configure logging to suppress Streamlit runtime warnings
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.state.session_state_proxy").setLevel(logging.ERROR)

# Add current directory to Python path to fix import issues
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import application components
from config.app_config import APP_TITLE, APP_ICON, LAYOUT, INITIAL_SIDEBAR_STATE
from core.instance_manager import UseCaseManager
from components.sidebar import Sidebar
from components.pages.about import AboutPage
from components.pages.instance_overview import InstanceOverviewPage
from components.pages.optimization_results import OptimizationResultsPage


class OptiPortApp:
    """Main application class for the OptiPort visualization interface"""
    
    def __init__(self):
        self.use_case_manager = UseCaseManager()
        self.sidebar = Sidebar(APP_TITLE, APP_ICON)

        # Initialize pages
        self.about_page = AboutPage()
        self.instance_overview_page = InstanceOverviewPage(self.use_case_manager)
        self.results_page = OptimizationResultsPage(self.use_case_manager)

        # Session state initialization
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Initialize Streamlit session state variables"""
        if "current_page" not in st.session_state:
            st.session_state.current_page = "Über das Projekt"

        if "selected_instance" not in st.session_state:
            st.session_state.selected_instance = None


    def run(self):
        """Run the main application"""
        
        # Get the current page name for the title
        current_page = st.session_state.get("current_page", "Portfolio-Übersicht")
        
        # Configure Streamlit page with dynamic title
        st.set_page_config(
            page_title=f"{current_page} | {APP_TITLE}",
            page_icon=APP_ICON,
            layout=LAYOUT,
            initial_sidebar_state=INITIAL_SIDEBAR_STATE
        )
        
        # Custom CSS for better styling
        self._apply_custom_css()
        
        # Render sidebar and get selected page
        selected_page = self.sidebar.render()

        # Only update current_page from sidebar if user explicitly clicked the radio.
        # Programmatic navigation (buttons) sets current_page before rerun, so we
        # must not overwrite it with the (now-synced) sidebar value.
        if selected_page != st.session_state.current_page:
            st.session_state.current_page = selected_page
            st.rerun()
        
        # Route to appropriate page
        self._render_page(st.session_state.current_page)
    
    def _apply_custom_css(self):
        """Apply custom CSS styling"""
        st.markdown("""
        <style>
        /* Main container styling */
        .main > div {
            padding-top: 2rem;
        }
        
        /* Metrics styling */
        [data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #d0d7de;
            padding: 0.75rem;
            border-radius: 0.375rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            color: #1f2937;
        }
        
        [data-testid="metric-container"] label {
            color: #374151 !important;
            font-weight: 500;
        }
        
        [data-testid="metric-container"] [data-testid="metric-value"] {
            color: #111827 !important;
            font-weight: 600;
        }
        
        /* Button styling */
        .stButton > button {
            width: 100%;
            border-radius: 0.375rem;
            border: 1px solid #d1d5db;
            transition: all 0.3s;
            background-color: #ffffff;
            color: #374151 !important;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateY(-1px);
            background-color: #f9fafb;
            border-color: #9ca3af;
        }
        
        .stButton > button:focus {
            outline: 2px solid #3b82f6;
            outline-offset: 2px;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 0.375rem;
            color: #475569 !important;
        }
        
        .streamlit-expanderHeader:hover {
            background-color: #f1f5f9;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background-color: #f8fafc;
        }
        
        /* General text contrast improvements */
        .stMarkdown, .stText {
            color: #1f2937;
        }
        
        .stSelectbox label, .stTextInput label, .stNumberInput label {
            color: #374151 !important;
            font-weight: 500;
        }
        
        /* Data frame styling */
        .stDataFrame {
            background-color: #ffffff;
        }
        
        .stDataFrame table {
            background-color: #ffffff !important;
            color: #1f2937 !important;
        }
        
        .stDataFrame th {
            background-color: #f8fafc !important;
            color: #374151 !important;
            font-weight: 600;
            border-bottom: 2px solid #e2e8f0;
        }
        
        .stDataFrame td {
            color: #1f2937 !important;
            border-bottom: 1px solid #f1f5f9;
        }
        
        .stDataFrame tr:hover {
            background-color: #f8fafc !important;
        }
        
        /* Subheader and header styling */
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #111827 !important;
            font-weight: 600;
        }
        
        /* Info, warning, success, error message styling */
        .stSuccess, .stError, .stWarning, .stInfo {
            padding: 0.75rem;
            border-radius: 0.375rem;
            margin: 0.5rem 0;
            color: #1f2937 !important;
        }
        
        .stSuccess {
            background-color: #f0fdf4 !important;
            border: 1px solid #bbf7d0 !important;
        }
        
        .stError {
            background-color: #fef2f2 !important;
            border: 1px solid #fecaca !important;
        }
        
        .stWarning {
            background-color: #fffbeb !important;
            border: 1px solid #fed7aa !important;
        }
        
        .stInfo {
            background-color: #eff6ff !important;
            border: 1px solid #bfdbfe !important;
        }
        
        /* Download button and special button styling */
        .stDownloadButton > button {
            background-color: #3b82f6 !important;
            color: white !important;
            border: none !important;
        }
        
        .stDownloadButton > button:hover {
            background-color: #2563eb !important;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding-left: 20px;
            padding-right: 20px;
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 0.375rem 0.375rem 0px 0px;
            color: #475569 !important;
            font-weight: 500;
        }
        
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: #ffffff;
            border-bottom: 1px solid #ffffff;
            color: #1e293b !important;
            font-weight: 600;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #f1f5f9;
            color: #334155 !important;
        }
        
        /* Success/Error message styling - enhanced version above */
        </style>
        """, unsafe_allow_html=True)
    
    def _render_page(self, page_name: str):
        """Render the selected page"""

        try:
            if page_name == "Über das Projekt":
                self.about_page.render()

            elif page_name == "Portfolio-Übersicht":
                selected_use_case = self.instance_overview_page.render()
                if selected_use_case:
                    st.session_state["selected_use_case"] = selected_use_case

            elif page_name == "Optimierungsergebnisse":
                selected_use_case = st.session_state.get("selected_use_case", None)
                self.results_page.render(selected_use_case)


            else:
                st.error(f"Unbekannte Seite: {page_name}")

        except Exception as e:
            logger.error(f"Error rendering page {page_name}: {e}")
            st.error(f"Fehler beim Rendern der Seite: {e}")
            st.exception(e)

def main():
    """Main entry point for the application"""
    
    # Create and run the application
    app = OptiPortApp()
    app.run()

if __name__ == "__main__":
    main()
