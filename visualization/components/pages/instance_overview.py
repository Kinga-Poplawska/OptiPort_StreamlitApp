"""
Portfolio overview page – use-case selection + data overview tabs.
"""
import streamlit as st
from typing import List, Optional

from core.instance_manager import UseCaseManager
from core.data_models import UseCaseMetadata, ProcessedBuildingResult, ProcessedPortfolioResult
from config.translations import get_column_translation, get_technology_translation, TECHNOLOGY_TRANSLATIONS


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _format_de_number(value, decimals: int = 0) -> str:
    """Format numbers in German style (1.234,56)."""
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    formatted = f"{number:,.{decimals}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _translate_credit_type(value: str) -> str:
    mapping = {"repayment_loan": "Tilgungsdarlehen"}
    return mapping.get(value, value)


def _translate_financial_field(field_name: str) -> str:
    """Translate financial_properties column names to readable German labels."""
    mapping = {
        "id":               "Gebäude-ID",
        "building_id":      "Gebäude-ID",
        "rent-1 in €/m2":           "Miete im Vorjahr (€/m²)",
        "rent-2 in €/m2":           "Miete vor zwei Jahren (€/m²)",
        "rent-3 in €/m2":           "Miete vor drei Jahren (€/m²)",
        "cap_rent in €/m2":         "Kappungsgrenze der Kaltmiete (€/m²)",
        "cap_warm_rent in €/m2":    "Kappungsgrenze der Warmmiete (€/m²)",
        "c_comp in €/m2":           "Vergleichsmiete (€/m²)",
        "c_comp_increase in -":     "Jährliche prozentuale Steigerung Vergleichsmiete (%)",
        "en_gas_cost in €/wh":      "Energiekosten für Gasbezug (€/Wh)",
        "en_hp_cost in €/wh":       "Energiekosten Wärmepumpen-Strombezug (€/Wh)",
        "en_el_cost in €/wh":       "Energiekosten für Allgemeinstrom (€/Wh)",
        "c_misc in €":              "Sonstige Kosten (€)",
        "c_misc_ten in €/m2":       "Sonstige Mieter-Kosten (€/m²)",
        "p_loss in -":              "Mietausfallquote (%)",
        "tense_market (bool)":      "Angespannter Wohnungsmarkt (ja/nein)",
    }
    if field_name in mapping:
        return mapping[field_name]

    normalized = str(field_name).strip().lower()
    if normalized in mapping:
        return mapping[normalized]

    cleaned = str(field_name).replace("_", " ").replace("-", " ").strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else str(field_name)


def _parse_tense_market(value) -> str:
    """Format tense market indicator for display (0/1 -> nein/true)."""
    if value is None:
        return "—"
    if str(value).strip() == "":
        return "—"

    try:
        number = float(value)
        if abs(number - 1.0) < 1e-9:
            return "ja"
        if abs(number) < 1e-9:
            return "nein"
    except (TypeError, ValueError):
        pass

    return str(value)


# Columns whose cell values should be translated via get_technology_translation
_TECH_TRANSLATE_COLS = {"ex_heat_prim", "ex_heat_sec", "ex_sto", "ex_dhw_sto", "ex_dis"}

# ---------------------------------------------------------------------------
# Curated measure list for installation-rate limits.
#
# Rules:
#   - No connection measures (contain "connection")
#   - No private-prefix keys (start with "_")
#   - No synonym/alias keys that duplicate a canonical key
#     (gas_boiler, oil_boiler, pellet_boiler, heat_pump, district,
#      district_heating, radiator, underfloor_heating, boiler,
#      insulation, window, storage, battery)
#   - Envelope classes (wall_1/2/3, roof_1/2/3, win_1/2/3) collapsed into
#     one entry each; these get "(Anzahl Gebäude)" appended to their label
# ---------------------------------------------------------------------------

# Keys to exclude entirely (aliases / synonyms covered by canonical keys above)
_MEASURE_EXCLUDE = {
    "gas_boiler", "oil_boiler", "pellet_boiler", "heat_pump",
    "district", "district_heating", "none",
    "radiator", "underfloor_heating",
    "boiler", "insulation", "window", "storage", "battery",
    # envelope class variants – we keep only one representative per group
    "wall_2", "wall_3",
    "roof_2", "roof_3",
    "win_2", "win_3",
}

# Override display names for the collapsed envelope representatives
_MEASURE_LABEL_OVERRIDE = {
    "wall_1": "Außenwanddämmung (Anzahl Gebäude)",
    "roof_1": "Dachdämmung (Anzahl Gebäude)",
    "win_1":  "Fenstertausch (Anzahl Gebäude)",
}

_AVAILABLE_MEASURES = sorted(
    k for k in TECHNOLOGY_TRANSLATIONS.keys()
    if "connection" not in k
    and not k.startswith("_")
    and k not in _MEASURE_EXCLUDE
)

_PLANNING_YEARS = list(range(2026, 2046))


# ---------------------------------------------------------------------------
# Page class
# ---------------------------------------------------------------------------

class InstanceOverviewPage:
    """Page for selecting a use case and showing a data overview."""

    def __init__(self, use_case_manager: UseCaseManager):
        self.use_case_manager = use_case_manager

    # -----------------------------------------------------------------------
    # Entry point
    # -----------------------------------------------------------------------

    def render(self) -> Optional[str]:
        """Render the portfolio overview page. Returns selected use-case name or None."""

        st.markdown(
            """
            <style>
            .block-container { padding-top: 1rem !important; }
            </style>
            <h2 style="margin-top:1rem; margin-bottom:0.25rem;">Portfolio-Übersicht</h2>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("Wählen Sie einen Use Case aus, um die Optimierungsergebnisse zu analysieren.")

        try:
            use_cases = self.use_case_manager.discover_use_cases()
        except RuntimeError as e:
            st.error(str(e))
            return None

        if not use_cases:
            st.warning("Keine Use Cases gefunden. Bitte stellen Sie sicher, dass mindestens ein Use-Case-Ordner unter 'run/use_cases/' vorhanden ist.")
            return None

        use_case_names = [uc.name for uc in use_cases]
        default_index = 0
        if "selected_use_case" in st.session_state:
            try:
                default_index = use_case_names.index(st.session_state["selected_use_case"])
            except ValueError:
                default_index = 0

        selected_name = st.selectbox(
            "Verfügbare Use Cases:",
            use_case_names,
            index=default_index,
            key="use_case_selector",
        )
        if not selected_name:
            return None

        st.session_state["selected_use_case"] = selected_name
        selected_uc: UseCaseMetadata = next(uc for uc in use_cases if uc.name == selected_name)

        st.markdown("---")


        self._render_overview_tabs(selected_uc)

        return selected_name

    # -----------------------------------------------------------------------
    # Tab container
    # -----------------------------------------------------------------------

    def _render_overview_tabs(self, selected_uc: UseCaseMetadata):
        """Show detail tabs — no result loading here."""
        use_case_name = selected_uc.name

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Übersicht",
            "Gebäudedaten",
            "Finanzdaten",
            "Portfolio Kapazitäten",
            "Neues Portfolio",
        ])

        with tab1:
            self._render_overview_tab(use_case_name)
        with tab2:
            self._render_building_data_tab(use_case_name, [])
        with tab3:
            self._render_financial_data_tab(use_case_name, None)
        with tab4:
            self._render_portfolio_resources_tab(use_case_name, [])
        with tab5:
            self._render_new_portfolio_tab()

    # =======================================================================
    # Tab 1: Übersicht
    # =======================================================================

    def _render_overview_tab(self, use_case_name: str):
        from pathlib import Path
        st.subheader("Überblick: Datenvollständigkeit des Portfolios")

        base = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "run" / "use_cases" / use_case_name / "data" / "input"
        )

        data_status = {
            "building":  "green" if (base / "stock_properties.csv").exists() else "red",
            "financial": "green" if (
                (base / "financial_properties.csv").exists()
                and (base / "general_finances.json").exists()
            ) else "red",
            "portfolio": "green" if (base / "portfolio_caps.json").exists() else "yellow",
        }

        self._render_data_overview_table(data_status)
        st.markdown("---")
        overall_status = self._render_overall_status(data_status)

        st.markdown("---")
        st.subheader("Aktionen")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("→ Ergebnisse anzeigen", key="overview_goto_results"):
                st.session_state["current_page"] = "Optimierungsergebnisse"
                st.rerun()
        with col2:
            if overall_status != "red":
                if st.button("Optimierung starten", key="start_opt_btn"):
                    st.info("Das Feature wird Ihnen in einer zukünftigen Version bereitgestellt.")
            else:
                st.button(
                    "Optimierung starten",
                    disabled=True,
                    key="start_opt_btn_disabled",
                    help="Kritische Eingabedaten fehlen.",
                )

    def _render_data_overview_table(self, data_status: dict):
        import pandas as pd

        status_list = [
            data_status["building"],
            data_status["financial"],
            data_status["portfolio"],
        ]
        df = pd.DataFrame({
            "Daten":  ["Gebäudedaten", "Finanzdaten", "Portfolio Kapazitäten"],
            "Status": [self._get_status_display(s) for s in status_list],
        })

        def _color(row):
            s = status_list[row.name]
            if s == "green":  return ["background-color:#d4edda;color:#155724"] * 2
            if s == "yellow": return ["background-color:#fff3cd;color:#856404"] * 2
            return                   ["background-color:#f8d7da;color:#721c24"] * 2

        st.dataframe(df.style.apply(_color, axis=1), use_container_width=True, hide_index=True)

    def _get_status_display(self, code: str) -> str:
        return {
            "green":  "✅ Vollständig",
            "yellow": "⚠️ Teilweise",
            "red":    "❌ Fehlend",
        }.get(code, "❓ Unbekannt")

    def _render_overall_status(self, data_status: dict) -> str:
        statuses = list(data_status.values())
        if "red" in statuses:
            st.error("⛔ Optimierung kann nicht gestartet werden: Kritische Daten fehlen")
            return "red"
        if "yellow" in statuses:
            st.warning("⚠️ Optimierung kann gestartet werden – Einige Daten unvollständig, Standardwerte werden verwendet")
            return "yellow"
        st.success("✅ Alle Daten vollständig – Bereit für die Optimierung")
        return "green"

    # =======================================================================
    # Tab 2: Gebäudedaten
    # =======================================================================

    def _render_building_data_tab(self, use_case_name: str, buildings: List[ProcessedBuildingResult]):
        import pandas as pd
        from pathlib import Path

        stock_props_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "run" / "use_cases" / use_case_name / "data" / "input" / "stock_properties.csv"
        )

        if not stock_props_path.exists():
            st.warning("stock_properties.csv nicht gefunden")
            return

        try:
            try:
                df = pd.read_csv(stock_props_path, sep=None, engine="python")
            except Exception:
                try:
                    df = pd.read_csv(stock_props_path, sep=";")
                except Exception:
                    df = pd.read_csv(stock_props_path, sep=",", encoding="latin1")

            if len(df.columns) == 1 and ";" in str(df.columns[0]):
                df = pd.read_csv(stock_props_path, sep=";")

            df = df.dropna(how="all")
            df = df[~df.apply(lambda row: row.astype(str).str.strip().eq("").all(), axis=1)]

            # Strip BOM / whitespace from column names
            df = df.rename(columns={c: str(c).replace("\ufeff", "").strip() for c in df.columns})

            # Translate technology cell values (Heizung, Speicher, etc.)
            for tech_col in _TECH_TRANSLATE_COLS:
                if tech_col in df.columns:
                    df[tech_col] = df[tech_col].apply(
                        lambda v: get_technology_translation(str(v)) if pd.notna(v) else v
                    )

            # Build display DataFrame with translated column headers
            display_df = df.copy()
            display_df.columns = [get_column_translation(c) for c in df.columns]

            st.data_editor(
                display_df,
                use_container_width=True,
                height=min(520, 50 + len(display_df) * 35),
                hide_index=True,
                key="building_data_editor",
            )

        except Exception as e:
            st.error(f"Fehler beim Lesen von stock_properties.csv: {e}")

        st.markdown("---")
        if st.button("💾 Änderungen speichern", key="save_building"):
            st.info("Die Funktionalität, Ihren Gebäudebestand in der App anzupassen, wird Ihnen in Zukunft zur Verfügung gestellt.")

    # =======================================================================
    # Tab 3: Finanzdaten
    # =======================================================================

    def _render_financial_data_tab(self, use_case_name: str, portfolio: Optional[ProcessedPortfolioResult]):
        import pandas as pd
        import json
        from pathlib import Path

        base = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "run" / "use_cases" / use_case_name / "data" / "input"
        )

        subtab1, subtab2 = st.tabs(["Allgemeine Finanzkennwerte", "Finanzübersicht je Gebäude"])

        # ── Sub-tab 1: General finances ───────────────────────────────
        with subtab1:
            gen_fin_path = base / "general_finances.json"
            if not gen_fin_path.exists():
                st.info("general_finances.json nicht gefunden.")
            else:
                try:
                    with open(gen_fin_path, "r", encoding="utf-8") as f:
                        fin_data = json.load(f)

                    rows = []

                    equity = fin_data.get("equity", {})
                    rows += [
                        {"Kennzahl": "Anfangskapital (€)",    "Wert": _format_de_number(equity.get("initial_equity", 0), 0)},
                        {"Kennzahl": "Minimalkapital (€)",    "Wert": _format_de_number(equity.get("minimal_equity", 0), 0)},
                        {"Kennzahl": "Eigenkapital-Mindestquote (%)",      "Wert": _format_de_number(float(equity.get("minimum_equity_quota", 0)) * 100, 1)},
                    ]

                    liquidity = fin_data.get("liquidity", {})
                    rows += [
                        {"Kennzahl": "Anfangsliquidität (€)",  "Wert": _format_de_number(liquidity.get("initial_liquidity", 0), 0)},
                        {"Kennzahl": "Minimalliquidität (€)",  "Wert": _format_de_number(liquidity.get("minimal_liquidity", 0), 0)},
                        {"Kennzahl": "Verzinsung liquider Mittel (%)",    "Wert": _format_de_number(float(liquidity.get("liquidity_rate", 0)) * 100, 1)},
                    ]

                    liabilities = fin_data.get("liabilities", {})
                    rows += [
                        {"Kennzahl": "Fremdkapital: Ausgangsschuld (€)",        "Wert": _format_de_number(liabilities.get("initial_liabilities", 0), 0)},
                        {"Kennzahl": "Verbleibende Kreditjahre der Ausgangsschuld (Jahre)",  "Wert": _format_de_number(liabilities.get("remaining_credit_years", 0), 0)},
                        {"Kennzahl": "Zinssatz der Bestandskredite (%)",            "Wert": _format_de_number(float(liabilities.get("debt_interest_rate", 0)) * 100, 1)},
                    ]

                    rates = fin_data.get("rates", {})
                    rows += [
                        {"Kennzahl": "Zinssatz für neue Kredite (%)",       "Wert": _format_de_number(float(rates.get("credit_rate", 0)) * 100, 1)},
                        {"Kennzahl": "Kredittyp",            "Wert": _translate_credit_type(rates.get("credit_type", "N/A"))},
                        {"Kennzahl": "Kredit-Anteil pro Maßnahme bei Fremdkapitl-Bezahlung (%)",  "Wert": _format_de_number(fin_data.get("alpha_credit", 1)*100, 1)},
                    ]

                    st.data_editor(
                        pd.DataFrame(rows),
                        hide_index=True,
                        use_container_width=True,
                        height=min(600, 50 + len(rows) * 35),
                        key="gen_fin_editor",
                    )
                except Exception as e:
                    st.warning(f"Fehler beim Lesen von general_finances.json: {e}")

        st.markdown("---")
        if st.button("💾 Änderungen speichern", key="save_finance"):
            st.info("Die Funktionalität, Ihren Gebäudebestand in der App anzupassen, wird Ihnen in Zukunft zur Verfügung gestellt.")

            # ── Sub-tab 2: Per-building finances ──────────────────────────
        with subtab2:
            fin_props_path = base / "financial_properties.csv"
            if not fin_props_path.exists():
                st.info("financial_properties.csv nicht gefunden.")
            else:
                try:
                    try:
                        fin_df = pd.read_csv(fin_props_path, sep=None, engine="python")
                    except Exception:
                        try:
                            fin_df = pd.read_csv(fin_props_path, sep=";")
                        except Exception:
                            fin_df = pd.read_csv(fin_props_path, sep=",", encoding="latin1")

                    if len(fin_df.columns) == 1 and ";" in str(fin_df.columns[0]):
                        fin_df = pd.read_csv(fin_props_path, sep=";")

                    fin_df = fin_df.dropna(how="all")
                    fin_df = fin_df[~fin_df.apply(lambda r: r.astype(str).str.strip().eq("").all(), axis=1)]
                    fin_df = fin_df.rename(columns={c: str(c).replace("\ufeff", "").strip() for c in fin_df.columns})

                    id_candidates = ["id", "building_id", "buildingid"]
                    norm_map = {str(c).strip().lower(): c for c in fin_df.columns}
                    id_col = next((norm_map[k] for k in id_candidates if k in norm_map), None)

                    if id_col is None:
                        display = fin_df.copy()
                        for col in display.columns:
                            col_norm = str(col).strip().lower()
                            if col_norm in {"c_comp_increase in -", "p_loss in -"}:
                                nums = pd.to_numeric(display[col], errors="coerce")
                                display[col] = display[col].where(
                                    nums.isna(),
                                    (nums * 100).apply(lambda x: _format_de_number(x, 1))
                                )
                            if col_norm in {"tense_market (bool)", "tense_market"}:
                                display[col] = display[col].apply(_parse_tense_market)
                        display = display.rename(columns=lambda c: _translate_financial_field(c))
                        st.data_editor(
                            display,
                            use_container_width=True,
                            hide_index=True,
                            height=min(400, 50 + len(display) * 35),
                            key="fin_table_full",
                        )
                    else:
                        building_ids = sorted(fin_df[id_col].dropna().astype(str).unique())
                        sel = st.selectbox(
                            "Gebäude auswählen:",
                            building_ids,
                            key="financial_building_selector",
                        )
                        row = fin_df[fin_df[id_col].astype(str) == sel].iloc[0]
                        rows = []
                        for col in fin_df.columns:
                            v = row[col]
                            col_norm = str(col).strip().lower()
                            if pd.isna(v):
                                disp = "—"
                            elif col_norm in {"tense_market (bool)", "tense_market"}:
                                disp = _parse_tense_market(v)
                            else:
                                num = pd.to_numeric(pd.Series([v]), errors="coerce").iloc[0]
                                if pd.isna(num):
                                    disp = str(v)
                                else:
                                    if col_norm in {"c_comp_increase in -", "p_loss in -"}:
                                        num = float(num) * 100
                                        disp = _format_de_number(num, 1)
                                    else:
                                        is_int = abs(float(num) - round(float(num))) < 1e-9
                                        disp = _format_de_number(num, 0 if is_int else 2)
                            rows.append({"Kennzahl": _translate_financial_field(col), "Wert": disp})

                        st.data_editor(
                            pd.DataFrame(rows),
                            hide_index=True,
                            use_container_width=True,
                            height=min(600, 50 + len(rows) * 35),
                            key="fin_building_editor",
                        )
                except Exception as e:
                    st.warning(f"Fehler beim Lesen von financial_properties.csv: {e}")

    # =======================================================================
    # Tab 4: Portfolio Kapazitäten
    # =======================================================================

    def _render_portfolio_resources_tab(self, use_case_name: str, buildings: List[ProcessedBuildingResult]):
        import json
        from pathlib import Path

        caps_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "run" / "use_cases" / use_case_name / "data" / "input" / "portfolio_caps.json"
        )

        existing: dict = {}
        if caps_path.exists():
            try:
                with open(caps_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass

        st.subheader("Maximales jährliches Investitionsbudget in €")
        self._render_year_value_editor("inv", existing.get("investment", {}), "€")

        st.markdown("---")

        st.markdown("### Maximale jährliche Emissionen in t<sub>CO₂</sub>", unsafe_allow_html=True)
        self._render_year_value_editor("em", existing.get("emissions", {}), "t<sub>CO₂</sub>")

        st.markdown("---")

        st.subheader("Maximale Einbauraten je Maßnahme in Stück pro Jahr")
        self._render_installation_rate_editor(existing.get("installation_rates", {}))

        st.markdown("---")
        if st.button("💾 Änderungen speichern", key="save_caps"):
            st.info("Die Funktionalität, die Portfolio Restriktionen in der App anzupassen, wird Ihnen in Zukunft zur Verfügung gestellt.")

    def _render_year_value_editor(self, key_prefix: str, existing: dict, unit: str):
        """Year-selector + value inputs for an investment or emissions cap."""
        unit_has_html = "<" in unit and ">" in unit

        mode = st.radio(
            "Modus:",
            ["Konstanter Grenzwert", "Jahreswerte"],
            horizontal=True,
            key=f"{key_prefix}_mode",
        )

        if mode == "Konstanter Grenzwert":
            existing_const = next(
                (int(round(float(v))) for k, v in existing.items() if str(k).isdigit()),
                0,
            )
            if unit_has_html:
                st.markdown(f"Konstanter Grenzwert ({unit})", unsafe_allow_html=True)
            st.number_input(
                f"Konstanter Grenzwert ({unit})" if not unit_has_html else "Konstanter Grenzwert",
                min_value=0,
                value=existing_const,
                step=1000 if unit == "€" else 1,
                key=f"{key_prefix}_const",
                label_visibility="visible" if not unit_has_html else "collapsed",
            )
        else:
            default_years = [
                int(k) for k in existing.keys()
                if str(k).isdigit() and int(k) in _PLANNING_YEARS
            ]
            selected_years = st.multiselect(
                "Jahre auswählen:",
                options=_PLANNING_YEARS,
                default=default_years,
                key=f"{key_prefix}_years",
            )
            if selected_years:
                if unit_has_html:
                    st.markdown(f"<strong>Grenzwerte je Jahr ({unit}):</strong>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**Grenzwerte je Jahr ({unit}):**")
                n_cols = min(4, len(selected_years))
                cols = st.columns(n_cols)
                for i, yr in enumerate(sorted(selected_years)):
                    default_val = int(round(float(existing.get(str(yr), existing.get(yr, 0.0)))))
                    with cols[i % n_cols]:
                        st.number_input(
                            str(yr),
                            min_value=0,
                            value=default_val,
                            step=1000 if unit == "€" else 1,
                            key=f"{key_prefix}_val_{yr}",
                        )
                if len(selected_years) > 1:
                    st.checkbox(
                        "Zwischenjahre interpolieren",
                        value=bool(existing.get("interpolate", False)),
                        key=f"{key_prefix}_interpolate",
                    )

    def _render_installation_rate_editor(self, existing: dict):
        """Per-measure installation rate editor."""
        measure_labels = {
            m: _MEASURE_LABEL_OVERRIDE.get(m, get_technology_translation(m))
            for m in _AVAILABLE_MEASURES
        }
        label_to_measure = {v: k for k, v in measure_labels.items()}
        sorted_labels = sorted(measure_labels.values())

        selected_labels = st.multiselect(
            "Maßnahmen auswählen:",
            options=sorted_labels,
            default=[],
            key="inst_rate_measures",
        )

        for label in selected_labels:
            measure = label_to_measure[label]
            measure_existing = existing.get(measure, {})

            st.markdown(f"**{label}**")

            mode = st.radio(
                "Modus:",
                ["Konstanter Grenzwert", "Jahreswerte"],
                horizontal=True,
                key=f"inst_{measure}_mode",
            )

            if mode == "Konstanter Grenzwert":
                existing_const = next(
                    (int(round(float(v))) for k, v in measure_existing.items() if str(k).isdigit()),
                    0,
                )
                st.number_input(
                    "Konstante maximale Einbaurate (Stück pro Jahr)",
                    min_value=0,
                    value=existing_const,
                    step=1,
                    key=f"inst_{measure}_const",
                )
            else:
                default_years = [
                    int(k) for k in measure_existing.keys()
                    if str(k).isdigit() and int(k) in _PLANNING_YEARS
                ]
                selected_years = st.multiselect(
                    "Jahre auswählen:",
                    options=_PLANNING_YEARS,
                    default=default_years,
                    key=f"inst_{measure}_years",
                )
                if selected_years:
                    st.markdown("Einbauraten je Jahr (Stück/Jahr):")
                    n_cols = min(4, len(selected_years))
                    cols = st.columns(n_cols)
                    for i, yr in enumerate(sorted(selected_years)):
                        default_val = int(round(float(
                            measure_existing.get(str(yr), measure_existing.get(yr, 0.0))
                        )))
                        with cols[i % n_cols]:
                            st.number_input(
                                str(yr),
                                min_value=0,
                                value=default_val,
                                step=1,
                                key=f"inst_{measure}_val_{yr}",
                            )
                    if len(selected_years) > 1:
                        st.checkbox(
                            "Zwischenjahre interpolieren",
                            value=bool(measure_existing.get("interpolate", False)),
                            key=f"inst_{measure}_interpolate",
                        )

            st.markdown("---")

    # =======================================================================
    # Tab 5: Zielgrößen auswählen
    # =======================================================================

    def _render_objective_weights_tab(self, use_case_name: str):
        """Scenario picker + objective weight sliders."""
        scenarios = self.use_case_manager.discover_scenarios(use_case_name)

        st.subheader("Szenario auswählen")

        if not scenarios:
            st.info("Noch kein Szenario vorhanden. Szenarien werden beim Ausführen der Optimierung angelegt.")
        else:
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                selected_scenario = st.selectbox(
                    "Szenario:",
                    scenarios,
                    key="obj_scenario_selector",
                )
            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕ Neues Szenario", key="new_scenario_btn"):
                    st.info(
                        "Die Funktionalität, verschiedene Szenarien in der App zu konfigurieren, "
                        "wird Ihnen in Zukunft zur Verfügung gestellt."
                    )

            if selected_scenario:
                run_settings = self.use_case_manager.load_run_settings(
                    use_case_name, selected_scenario
                )
                port_settings = run_settings.get("portfolio_settings", {})

                st.markdown("---")
                st.subheader("Zielgewichtungen")
                st.markdown(
                    "Definieren Sie die Gewichtungen der Zielfunktion für die Optimierung. "
                    "Priorisieren Sie Ihre Bewertungsgrößen, um die optimale Modernisierungsentscheidung für Ihr Gebäudeportfolio zu treffen:"
                )

                phi_eq = st.slider(
                    "Maximales Eigenkapital (%)",
                    min_value=0, max_value=100,
                    value=int(port_settings.get("phi_eq", 0.33) * 100),
                    step=25,
                    key="slider_phi_eq",
                )
                phi_em = st.slider(
                    "Minimale Emissionen (%)",
                    min_value=0, max_value=100,
                    value=int(port_settings.get("phi_em", 0.33) * 100),
                    step=25,
                    key="slider_phi_em",
                )
                phi_warm = st.slider(
                    "Minimale Warmmiete (%)",
                    min_value=0, max_value=100,
                    value=int(port_settings.get("phi_warm", 0.34) * 100),
                    step=25,
                    key="slider_phi_warm",
                )

                weight_sum = phi_eq + phi_em + phi_warm
                if weight_sum != 100:
                    st.error(
                        f"⚠️ Summe der Gewichte ist **{weight_sum} %** — "
                        f"muss genau **100 %** sein."
                    )
                elif phi_eq == 0 and phi_em == 0 and phi_warm == 0:
                    st.warning("⚠️ Alle Gewichtungen sind 0 – die Zielfunktion hat keinen Einfluss.")

                st.markdown("---")
                save_disabled = weight_sum != 100
                if st.button(
                    "💾 Einstellungen speichern",
                    key="save_phi_btn",
                    disabled=save_disabled,
                ):
                    st.info(
                        "Die Funktionalität, verschiedene Szenarien in der App zu konfigurieren, "
                        "wird Ihnen in Zukunft zur Verfügung gestellt."
                    )

    # =======================================================================
    # Tab 6: Neues Portfolio
    # =======================================================================

    def _render_new_portfolio_tab(self):
        st.markdown("Laden Sie hier Dateien hoch, um ein neues Portfolio zu erstellen.")

        uploaded = st.file_uploader(
            "Dateien Hochladen",
            type=["csv", "json", "xlsx"],
            accept_multiple_files=True,
            key="new_portfolio_uploader",
        )
        if uploaded:
            st.info("Das Feature wird Ihnen in einer zukünftigen Version bereitgestellt.")

    # =======================================================================
    # Legacy helpers
    # =======================================================================

    def _validate_building_data(self, buildings: List[ProcessedBuildingResult]):
        if not buildings:
            return {"status": "red", "message": "❌ Kritische Daten fehlen"}
        all_complete = all(
            br.building_id and br.building_type and br.construction_year
            for br in buildings
        )
        return {
            "status":  "green" if all_complete else "yellow",
            "message": "✅ Gebäudedaten vollständig" if all_complete else "⚠️ Teilweise unvollständig",
        }

    def _validate_portfolio_resources(self, buildings: List[ProcessedBuildingResult]):
        if not buildings:
            return {"status": "yellow", "message": "⚠️ Standardwerte werden verwendet"}
        optiport_count = sum(1 for br in buildings if br.optiport_data)
        if optiport_count == len(buildings):
            return {"status": "green", "message": "✅ Portfolio-Kapazitätsdaten vollständig"}
        return {
            "status":  "yellow",
            "message": f"⚠️ Teilweise vorhanden ({optiport_count}/{len(buildings)} Gebäude)",
        }

