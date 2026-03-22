"""
About / Landing page – Über das Projekt OptiPort.
"""
import streamlit as st


class AboutPage:
    """Read-only landing page with project description and tool overview."""

    def render(self):
        st.markdown(
            """
            <style>
            .block-container { padding-top: 1rem !important; }
            </style>
            <h2 style="margin-top:0.5rem; margin-bottom:0.1rem;">Über das Projekt OptiPort</h2>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # ── Section 1: Tool overview ──────────────────────────────────
        st.markdown("### 🖥️ OptiPort WebApp – Ihr digitales Planungswerkzeug")
        st.markdown(
            """
            Die OptiPort WebApp unterstützt Wohnungsunternehmen bei der strukturierten Entwicklung
            von Modernisierungsfahrplänen für ihren gesamten Gebäudebestand. Das Tool bietet folgende
            Kernfunktionalitäten:
            """
        )

        col1, col2, col3 = st.columns(3, gap="medium")

        with col1:
            st.markdown(
                """
                <div style="background-color:#f0f7ff; border-left:4px solid #2563eb;
                            padding:1rem 1.25rem; border-radius:0.375rem; height:100%;">
                <b>📂 Portfolio-Verwaltung</b><br><br>
                Laden und verwalten Sie Bestands-, Finanz- und Kapazitätsdaten Ihres
                Wohnungsportfolios. Definieren Sie individuelle Rahmenbedingungen wie maximale
                Investitionsbudgets und Emissionsgrenzen.
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                """
                <div style="background-color:#f0fdf4; border-left:4px solid #16a34a;
                            padding:1rem 1.25rem; border-radius:0.375rem; height:100%;">
                <b>⚙️ Optimierungsplanung</b><br><br>
                Auf Basis Ihrer Portfoliodaten berechnet OptiPort einen optimierten
                Modernisierungsfahrplan, der technische, ökonomische und ökologische Anforderungen
                simultan berücksichtigt – zugeschnitten auf die spezifischen Bedingungen Ihres
                Unternehmens.
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                """
                <div style="background-color:#fefce8; border-left:4px solid #ca8a04;
                            padding:1rem 1.25rem; border-radius:0.375rem; height:100%;">
                <b>📊 Ergebnisanalyse</b><br><br>
                Visualisieren Sie die optimierten Modernisierungsmaßnahmen je Gebäude und Jahr,
                verfolgen Sie die Entwicklung von CO₂-Emissionen, Investitionskosten sowie weiteren Bewertungsgrößen und vergleichen Sie verschiedene Szenarien miteinander.
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            "<br> Das Tool ist für unterschiedliche Bestandsdatenqualitäten ausgelegt und wird "
            "kontinuierlich weiterentwickelt.",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # ── Section 2: Project description ───────────────────────────
        st.markdown("### 📋 Projektbeschreibung")
        st.markdown(
            """
            Wohnungsunternehmen spielen eine entscheidende Rolle bei der Erreichung eines
            klimaneutralen Gebäudebestandes. Anders als private Akteure haben sie bei der
            energetischen Modernisierung und beim Wechsel von Heizungsanlagen stets den gesamten
            Bestand im Blick, gehen bei der Entwicklung einer Modernisierungsstrategie aber bislang
            oft wenig strukturiert vor. Bestehende Tools am Markt sind nur wenig praxisnah und
            beziehen Spezifika der Unternehmen nur unzureichend ein.

            Im Projekt **OptiPort** soll gemeinsam mit der Wohnungswirtschaft ein Tool entwickelt
            werden, um für Mehrfamilienhaus-Portfolien einen optimierten Modernisierungsfahrplan zu
            erstellen, der die unternehmensspezifischen Rahmenbedingungen berücksichtigt. Das Tool
            soll praxisnahe Ergebnisse liefern, für unterschiedliche Bestandsdatenqualitäten und
            langfristig nutzbar sein. Die entwickelten Modernisierungsfahrpläne werden nach
            (sozio-)ökonomischen und ökologischen Gesichtspunkten sowie hinsichtlich der
            Robustheit gegenüber Unsicherheiten bewertet. Ein Stakeholder-Prozess identifiziert
            Hemmnisse und Lösungsansätze für die Umsetzung.

            Durch Aufstellung von Modernisierungsfahrplänen wird die Entscheidungsfindung unterstützt und ein geeigneter Umsetzungszeitpunkt von Modernisierungsmaßnahmen in Gebäudeportfolios unter Berücksichtigung begrenzter Ressourcen, wie Investitionsbudgets und Handwerksverfügbarkeit, identifiziert. 
            Ziel ist die Steigerung von Effizienz- und Beschleunigungspotentialen bei der Modernisierung von Mehrfamilienhäuser-Gebäudeportfolios.
            """
        )

        st.markdown("---")
        st.caption("OptiPort WebApp Prototyp · RWTH Aachen")

