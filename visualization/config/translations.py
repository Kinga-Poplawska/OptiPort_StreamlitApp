"""
Column name translations for data display
"""

# Map of English column names to German translations
COLUMN_TRANSLATIONS = {
    # Building properties
    'id': 'Gebäude-ID',
    'building_id': 'Gebäude-ID',
    'type': 'Gebäudetyp',
    'year': 'Baujahr',
    'location': 'Standort',
    'region': 'Region',
    'num': 'Anzahl',
    'area': 'Fläche (m²)',
    'num_floors': 'Stockwerke',
    'num_flats': 'Wohnungen',
    'persons_per_apartment': 'Personen pro Wohnung',
    'persons_per_appartment': 'Personen pro Wohnung',
    
    # Envelope components
    'ex_wall': 'Wandklasse',
    'ex_win': 'Fensterklasse',
    'ex_roof': 'Dachklasse',
    'ex_wall_u': 'U-Wert Wand',
    'ex_win_u': 'U-Wert Fenster',
    'ex_roof_u': 'U-Wert Dach',
    'wall_age': 'Alter Wand',
    'windows_age': 'Alter Fenster',
    'roof_age': 'Alter Dach',
    
    # Technical systems
    'ex_pv': 'Bestehende PV',
    'ex_dis': 'Bestehendes Verteilsystem',
    'roofs': 'Dachfläche',
    'rad_area': 'Heizkörperfläche',
    'always_available': 'Immer verfügbar',
    'ex_heat_prim': 'Primärheizung',
    'cap_heat_prim': 'Leistung Primärheizung (kW)',
    'ex_heat_sec': 'Sekundärheizung',
    'cap_heat_sec': 'Leistung Sekundärheizung (kW)',
    'ex_sto': 'Bestehender Speicher',
    'area_solar': 'Solarfläche (m²)',
    'cap_solar': 'Solarleistung (kW)',
    'cap_sto': 'Speicherkapazität (m³)',
    'cap_dhw_sto': 'Warmwasserspeicher (m³)',
    'ex_dhw_sto': 'Bestehender Warmwasserspeicher',
    'sup_temp': 'Vorlauftemperatur (°C)',
    'yearly_el_demand': 'Jährlicher Strombedarf (kWh)',
    'heat_age': 'Alter Heizung',
    'dhw_age': 'Alter Warmwasserspeicher',
    'solar_age': 'Alter Solaranlage',
    'storage_age': 'Alter Speicher',
    'rad_age': 'Alter Heizkörper',
    
    # Financial properties
    'c_misc': 'Sonstige Kosten',
    'c_misc_ten': 'Sonstige Mieterkosten',
    'p_loss': 'Mietausfall-Wahrscheinlichkeit',
    'tense_market': 'Angespannter Markt',
    'rent': 'Miete',
    'rent_increase': 'Mieterhöhung',
    'investment': 'Investition',
    'c_comp_wall': 'Kosten Wandkomponenten',
    'c_comp_win': 'Kosten Fensterkomponenten',
    'c_comp_roof': 'Kosten Dachkomponenten',
    'c_comp_heat': 'Kosten Heizungskomponenten',
    
    # Additional financial properties
    'rent-1': 'Kaltmiete Jahr -1',
    'rent-2': 'Kaltmiete Jahr -2',
    'rent-3': 'Kaltmiete Jahr -3',
    'cap_rent': 'Max. Kaltmiete (€/m² Monat)',
    'cap_warm_rent': 'Max. Warmmiete (€/m² Monat)',
    'c_comp': 'Vergleichsmiete (€/m² Monat)',
    'c_comp_increase': 'Jährliche Vergleichsmieterhöhung',
    'En_Gas_cost': 'Gaskosten (€/kWh)',
    'En_HP_cost': 'Wärmepumpenkosten (€/kWh)',
    'En_El_cost': 'Stromkosten (€/kWh)',
    
    # General terms
    'cost': 'Kosten',
    'price': 'Preis',
    'income': 'Einnahmen',
    'expense': 'Ausgaben',
    'budget': 'Budget',
    'depreciation': 'Abschreibung',
    'subsidy': 'Förderung',
    'tax': 'Steuer',
    'financial': 'Finanziell',
    'economic': 'Wirtschaftlich'
}

# File translations for display
FILE_TRANSLATIONS = {
    'stock_properties.csv': 'Gebäudebestandseigenschaften.csv',
    'financial_properties.csv': 'Finanzielle_Gebäudeeigenschaften.csv',
    'building_constraints.csv': 'Gebäudeeinschränkungen.csv',
    'general_finances.json': 'Allgemeine_Finanzen.json',
    'portfolio_caps.csv': 'Portfolio-Kapazitäten.csv',
    'portfolio_caps.json': 'Portfolio-Kapazitäten.json'
}

# Technology component translations
TECHNOLOGY_TRANSLATIONS = {
    # Heating systems
    'boi_gas': 'Gaskessel',
    'boi_ga': 'Gaskessel',  # Abbreviated variant
    'boi_oil': 'Ölkessel',
    'boi_oi': 'Ölkessel',   # Abbreviated variant
    'boi_pel': 'Pelletkessel',
    'hp_air': 'Luft-Wärmepumpe',
    'hp_geo_probe': 'Erdwärmepumpe (Sonde)',
    'hp_geo_col': 'Erdwärmepumpe (Kollektor)',
    'chp': 'Blockheizkraftwerk',
    'eh': 'Elektrischer Heizer',
    'dh': 'Fernwärme',
    'el_converter': 'Strom-Converter',
    
    # Building envelope
    'wall_1': 'Wanddämmung Klasse 1',
    'wall_2': 'Wanddämmung Klasse 2',
    'wall_3': 'Wanddämmung Klasse 3',
    'roof_1': 'Dachdämmung Klasse 1',
    'roof_2': 'Dachdämmung Klasse 2',
    'roof_3': 'Dachdämmung Klasse 3',
    'win_1': 'Fenster Klasse 1',
    'win_2': 'Fenster Klasse 2',
    'win_3': 'Fenster Klasse 3',
    'hull_1': 'Gebäudehülle Klasse 1',
    'hull_2': 'Gebäudehülle Klasse 2',
    'hull_3': 'Gebäudehülle Klasse 3',
    
    # Distribution systems
    'rad_11': 'Heizkörpertyp 11',
    'rad_22': 'Heizkörpertyp 22',
    'rad_33': 'Heizkörpertyp 33',
    'ufh': 'Fußbodenheizung',
    
    # Storage systems
    'tes': 'Pufferspeicher',
    'tes_dhw': 'Trinkwarmwasserspeicher',
    'bat': 'Batterie',
    
    # Renewables
    'pv_0': 'Photovoltaik',
    'stc_vt_0': 'Solarthermie (Vakuumröhren)',
    'stc_fp_0': 'Solarthermie (Flachkollektor)',
    
    # Connections
    '_connection': 'Netzanschluss',
    'boi_gas_connection': 'Anschluss Gaskessel',
    'boi_oil_connection': 'Anschluss Ölkessel',
    'boi_pel_connection': 'Anschluss Pelletkessel',
    'hp_air_connection': 'Anschluss Luft-Wärmepumpe',
    'hp_geo_probe_connection': 'Anschluss Erdwärmepumpe (Sonde)',
    'hp_geo_col_connection': 'Anschluss Erdwärmepumpe (Kollektor)',
    'chp_connection': 'Anschluss BHKW',
    'dh_connection': 'Anschluss Fernwärme',
    'eh_connection': 'Anschluss Elektroheizung',
    
    # System descriptions
    'gas_boiler': 'Gaskessel',
    'oil_boiler': 'Ölkessel',
    'pellet_boiler': 'Pelletkessel',
    'heat_pump': 'Wärmepumpe',
    'district': 'Fernwärme',
    'district_heating': 'Fernwärme',
    'none': 'Keine',
    'radiator': 'Heizkörper',
    'underfloor_heating': 'Fußbodenheizung',
    
    # Additional technology types
    'boiler': 'Heizkessel',
    'insulation': 'Dämmung',
    'window': 'Fenster',
    'storage': 'Speicher',
    'battery': 'Batterie'
}

# Energy carrier translations
ENERGY_CARRIER_TRANSLATIONS = {
    'gas': 'Erdgas',
    'biogas': 'Biogas',
    'el_grid': 'Netzstrom',
    'el_hp_grid': 'Strom (Wärmepumpe)',
    'el_pv_grid': 'PV-Einspeisung',
    'el_chp_grid': 'KWK-Einspeisung',
    'oil': 'Heizöl',
    'pel': 'Pellets',
    'sol': 'Solarthermie',
    'th_dh': 'Fernwärme',
}

def get_column_translation(column_name):
    """Get German translation for a column name"""
    return COLUMN_TRANSLATIONS.get(column_name, column_name)
    
def get_file_translation(file_name):
    """Get German translation for a file name"""
    return FILE_TRANSLATIONS.get(file_name, file_name)
    
def get_technology_translation(tech_name):
    """Get German translation for a technology component name"""
    # Special case for None values - return just the dash character
    if tech_name is None or tech_name.lower() == 'none' or tech_name.strip() == '':
        return '—'  # Unicode em dash
    return TECHNOLOGY_TRANSLATIONS.get(tech_name, tech_name)


def get_energy_carrier_translation(carrier_name):
    """Get German translation for an energy carrier name."""
    if carrier_name is None:
        return '—'
    return ENERGY_CARRIER_TRANSLATIONS.get(carrier_name, carrier_name)