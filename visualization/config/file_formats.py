"""
File format specifications and templates for data import/export
"""

FILE_FORMATS = {
    'stock_properties': {
        'format': 'csv',
        'delimiter': ',',
        'encoding': 'utf-8',
        'filename': 'stock_properties.csv',
        'required_columns': [
            'id', 'type', 'year', 'location', 'region', 'num', 'area', 'num_floors', 
            'num_flats', 'persons_per_apartment'
        ],
        'optional_columns': [
            'ex_sto', 'ex_wall', 'ex_win', 'ex_roof', 'ex_pv', 'ex_dis', 'roofs', 
            'rad_area', 'always_available', 'ex_heat_prim', 'cap_heat_prim', 
            'ex_heat_sec', 'cap_heat_sec', 'ex_sto.1', 'area_solar', 'cap_solar', 
            'cap_sto', 'cap_dhw_sto', 'sup_temp', 'ex_wall_u', 'ex_win_u', 'ex_roof_u', 
            'yearly_el_demand', 'wall_age', 'windows_age', 'roof_age', 'heat_age', 
            'dhw_age', 'solar_age', 'storage_age', 'rad_age', 'c_misc', 'c_misc_ten', 
            'p_loss', 'tense_market'
        ],
        'column_types': {
            'id': 'int',
            'type': 'str',
            'year': 'int',
            'location': 'str',
            'region': 'int',
            'num': 'int',
            'area': 'float',
            'num_floors': 'int',
            'num_flats': 'int',
            'persons_per_apartment': 'float',
            'ex_sto': 'str',
            'ex_wall': 'str',
            'ex_win': 'str',
            'ex_roof': 'str',
            'ex_pv': 'str',
            'ex_dis': 'str',
            'roofs': 'str',
            'rad_area': 'float',
            'always_available': 'bool',
            'ex_heat_prim': 'str',
            'cap_heat_prim': 'float',
            'ex_heat_sec': 'str',
            'cap_heat_sec': 'float',
            'ex_sto.1': 'str',
            'area_solar': 'float',
            'cap_solar': 'float',
            'cap_sto': 'float',
            'cap_dhw_sto': 'float',
            'sup_temp': 'float',
            'ex_wall_u': 'float',
            'ex_win_u': 'float',
            'ex_roof_u': 'float',
            'yearly_el_demand': 'float',
            'wall_age': 'int',
            'windows_age': 'int',
            'roof_age': 'int',
            'heat_age': 'int',
            'dhw_age': 'int',
            'solar_age': 'int',
            'storage_age': 'int',
            'rad_age': 'int',
            'c_misc': 'float',
            'c_misc_ten': 'float',
            'p_loss': 'float',
            'tense_market': 'bool'
        },
        'template_data': [
            {
                'id': 0,
                'type': 'residential',
                'year': 1985,
                'location': 'urban',
                'region': 1,
                'num': 1,
                'area': 850.0,
                'num_floors': 4,
                'num_flats': 8,
                'persons_per_apartment': 2.5,
                'ex_sto': 'existing',
                'ex_wall': 'moderate',
                'ex_win': 'old',
                'ex_roof': 'moderate',
                'ex_pv': 'none',
                'ex_dis': 'existing',
                'roofs': 'flat',
                'rad_area': 250.0,
                'always_available': True,
                'ex_heat_prim': 'gas_boiler',
                'cap_heat_prim': 50.0,
                'ex_heat_sec': 'none',
                'cap_heat_sec': 0.0,
                'ex_sto.1': 'existing',
                'area_solar': 0.0,
                'cap_solar': 0.0,
                'cap_sto': 500.0,
                'cap_dhw_sto': 300.0,
                'sup_temp': 70.0,
                'ex_wall_u': 1.2,
                'ex_win_u': 2.8,
                'ex_roof_u': 0.8,
                'yearly_el_demand': 3500.0,
                'wall_age': 38,
                'windows_age': 25,
                'roof_age': 15,
                'heat_age': 12,
                'dhw_age': 12,
                'solar_age': 0,
                'storage_age': 12,
                'rad_age': 38,
                'c_misc': 5000.0,
                'c_misc_ten': 2000.0,
                'p_loss': 15.0,
                'tense_market': False
            },
            {
                'id': 1,
                'type': 'commercial',
                'year': 2005,
                'location': 'suburban',
                'region': 2,
                'num': 2,
                'area': 1200.0,
                'num_floors': 3,
                'num_flats': 12,
                'persons_per_apartment': 2.0,
                'ex_sto': 'existing',
                'ex_wall': 'good',
                'ex_win': 'good',
                'ex_roof': 'good',
                'ex_pv': 'small',
                'ex_dis': 'existing',
                'roofs': 'pitched',
                'rad_area': 400.0,
                'always_available': True,
                'ex_heat_prim': 'heat_pump',
                'cap_heat_prim': 75.0,
                'ex_heat_sec': 'none',
                'cap_heat_sec': 0.0,
                'ex_sto.1': 'existing',
                'area_solar': 50.0,
                'cap_solar': 10.0,
                'cap_sto': 800.0,
                'cap_dhw_sto': 500.0,
                'sup_temp': 55.0,
                'ex_wall_u': 0.35,
                'ex_win_u': 1.3,
                'ex_roof_u': 0.25,
                'yearly_el_demand': 5200.0,
                'wall_age': 18,
                'windows_age': 18,
                'roof_age': 18,
                'heat_age': 8,
                'dhw_age': 8,
                'solar_age': 5,
                'storage_age': 8,
                'rad_age': 18,
                'c_misc': 8000.0,
                'c_misc_ten': 3500.0,
                'p_loss': 10.0,
                'tense_market': True
            },
            {
                'id': 2,
                'type': 'mixed',
                'year': 1998,
                'location': 'urban',
                'region': 1,
                'num': 3,
                'area': 950.0,
                'num_floors': 5,
                'num_flats': 10,
                'persons_per_apartment': 2.2,
                'ex_sto': 'existing',
                'ex_wall': 'moderate',
                'ex_win': 'moderate',
                'ex_roof': 'good',
                'ex_pv': 'none',
                'ex_dis': 'district_heating',
                'roofs': 'flat',
                'rad_area': 190.0,
                'always_available': True,
                'ex_heat_prim': 'district',
                'cap_heat_prim': 60.0,
                'ex_heat_sec': 'none',
                'cap_heat_sec': 0.0,
                'ex_sto.1': 'existing',
                'area_solar': 0.0,
                'cap_solar': 0.0,
                'cap_sto': 600.0,
                'cap_dhw_sto': 400.0,
                'sup_temp': 65.0,
                'ex_wall_u': 0.7,
                'ex_win_u': 1.8,
                'ex_roof_u': 0.3,
                'yearly_el_demand': 4100.0,
                'wall_age': 25,
                'windows_age': 15,
                'roof_age': 10,
                'heat_age': 15,
                'dhw_age': 15,
                'solar_age': 0,
                'storage_age': 15,
                'rad_age': 25,
                'c_misc': 6500.0,
                'c_misc_ten': 2800.0,
                'p_loss': 12.0,
                'tense_market': False
            }
        ]
    },
    
    'financial_properties': {
        'format': 'csv',
        'delimiter': ';',
        'encoding': 'utf-8',
        'filename': 'financial_properties.csv',
        'required_columns': [
            'id', 'c_comp', 'c_comp_increase', 'rent-1', 'rent-2', 'rent-3',
            'cap_rent', 'cap_warm_rent', 'En_Gas_cost', 'En_HP_cost', 'En_El_cost'
        ],
        'optional_columns': [],
        'column_types': {
            'id': 'int',
            'c_comp': 'float',
            'c_comp_increase': 'float',
            'rent-1': 'float',
            'rent-2': 'float',
            'rent-3': 'float',
            'cap_rent': 'float',
            'cap_warm_rent': 'float',
            'En_Gas_cost': 'float',
            'En_HP_cost': 'float',
            'En_El_cost': 'float'
        },
        'template_data': [
            {
                'id': 0,
                'c_comp': 85000.0,
                'c_comp_increase': 0.02,
                'rent-1': 8.5,
                'rent-2': 9.2,
                'rent-3': 10.0,
                'cap_rent': 12.0,
                'cap_warm_rent': 15.0,
                'En_Gas_cost': 0.08,
                'En_HP_cost': 0.25,
                'En_El_cost': 0.30
            },
            {
                'id': 1,
                'c_comp': 120000.0,
                'c_comp_increase': 0.025,
                'rent-1': 12.0,
                'rent-2': 13.5,
                'rent-3': 15.0,
                'cap_rent': 18.0,
                'cap_warm_rent': 22.0,
                'En_Gas_cost': 0.08,
                'En_HP_cost': 0.25,
                'En_El_cost': 0.30
            },
            {
                'id': 2,
                'c_comp': 95000.0,
                'c_comp_increase': 0.022,
                'rent-1': 9.5,
                'rent-2': 10.5,
                'rent-3': 11.5,
                'cap_rent': 14.0,
                'cap_warm_rent': 17.0,
                'En_Gas_cost': 0.08,
                'En_HP_cost': 0.25,
                'En_El_cost': 0.30
            }
        ]
    },
    
    'general_finances': {
        'format': 'json',
        'filename': 'general_finances.json',
        'schema': {
            'equity': {
                'initial_equity': 'float',
                'minimal_equity': 'float',
                'minimum_equity_quota': 'float'
            },
            'liquidity': {
                'initial_liquidity': 'float',
                'minimal_liquidity': 'float',
                'liquidity_rate': 'float'
            },
            'liabilities': {
                'initial_liabilities': 'float',
                'remaining_credit_years': 'int',
                'debt_interest_rate': 'float'
            },
            'rates': {
                'credit_rate': 'float',
                'interest_rate': 'float',
                'inflation_rate': 'float',
                'avg_construction_price_increase': 'float',
                'credit_type': 'str'
            },
            'alpha_credit': 'float',
            'VAT': 'float',
            'BKI_development': 'float',
            'year_of_price_origin': 'int'
        },
        'template_data': {
            'equity': {
                'initial_equity': None,
                'minimal_equity': None,
                'minimum_equity_quota': None
            },
            'liquidity': {
                'initial_liquidity': None,
                'minimal_liquidity': None,
                'liquidity_rate': None
            },
            'liabilities': {
                'initial_liabilities': None,
                'remaining_credit_years': None,
                'debt_interest_rate': None
            },
            'rates': {
                'credit_rate': None,
                'interest_rate': None,
                'inflation_rate': None,
                'avg_construction_price_increase': None,
                'credit_type': None
            },
            'alpha_credit': None,
            'VAT': None,
            'BKI_development': None,
            'year_of_price_origin': None
        }
    },
    
    'portfolio_caps': {
        'format': 'json',
        'filename': 'portfolio_caps.json',
        'schema': {
            'num_measures': {
                'boi_gas': {
                    'start': 'int',
                    'end': 'int'
                }
            },
            'labor': {
                'start': 'int',
                'end': 'int'
            },
            'energy': {
                'gas': {
                    'start': 'int',
                    'end': 'int'
                },
                'pel': {
                    'start': 'int',
                    'end': 'int'
                }
            },
            'emissions': {
                'start': 'int',
                'end': 'int'
            },
            'district_heating': {
                'start': 'int',
                'end': 'int'
            }
        },
        'template_data': {
            'num_measures': {
                'boi_gas': {
                    'start': None,
                    'end': None
                }
            },
            'labor': {
                'start': None,
                'end': None
            },
            'energy': {
                'gas': {
                    'start': None,
                    'end': None
                },
                'pel': {
                    'start': None,
                    'end': None
                }
            },
            'emissions': {
                'start': None,
                'end': None
            },
            'district_heating': {
                'start': None,
                'end': None
            }
        }
    }
}

TEMPLATE_README = """# OptiPort Instance Data Templates

This folder contains template files for importing data into OptiPort instances.

## Files Overview

### stock_properties.csv
Building stock energetic and structural properties (45 columns total).

**Required Columns:**
- `id` (int): Unique identifier for the building
- `type` (str): Building type (e.g., residential, commercial, mixed)
- `year` (int): Construction year
- `location` (str): Location category (e.g., urban, suburban, rural)
- `region` (int): Region identifier
- `num` (int): Building number in portfolio
- `area` (float): Total floor area in m²
- `num_floors` (int): Number of floors
- `num_flats` (int): Number of apartments/units
- `persons_per_apartment` (float): Average persons per apartment

**Optional Columns (Structural):**
- `roofs` (str): Roof type (flat, pitched, etc.)
- `rad_area` (float): Radiator area in m²
- `always_available` (bool): Building always available for measures

**Optional Columns (Existing Conditions - ex_*):**
- `ex_sto` (str): Existing storage status
- `ex_wall` (str): Existing wall condition
- `ex_win` (str): Existing window condition
- `ex_roof` (str): Existing roof condition
- `ex_pv` (str): Existing PV system
- `ex_dis` (str): Existing district heating connection
- `ex_heat_prim` (str): Existing primary heating system
- `ex_heat_sec` (str): Existing secondary heating system
- `ex_sto.1` (str): Existing storage system (duplicate column)

**Optional Columns (Capacities - cap_*):**
- `cap_heat_prim` (float): Primary heating capacity in kW
- `cap_heat_sec` (float): Secondary heating capacity in kW
- `cap_solar` (float): Solar thermal capacity in kW
- `cap_sto` (float): Thermal storage capacity in liters
- `cap_dhw_sto` (float): DHW storage capacity in liters

**Optional Columns (Areas):**
- `area_solar` (float): Solar collector area in m²

**Optional Columns (Thermal Properties - _u):**
- `ex_wall_u` (float): Wall U-value in W/(m²K)
- `ex_win_u` (float): Window U-value in W/(m²K)
- `ex_roof_u` (float): Roof U-value in W/(m²K)
- `sup_temp` (float): Supply temperature in °C

**Optional Columns (Energy):**
- `yearly_el_demand` (float): Annual electricity demand in kWh

**Optional Columns (Component Ages - _age):**
- `wall_age` (int): Wall age in years
- `windows_age` (int): Window age in years
- `roof_age` (int): Roof age in years
- `heat_age` (int): Heating system age in years
- `dhw_age` (int): DHW system age in years
- `solar_age` (int): Solar system age in years
- `storage_age` (int): Storage system age in years
- `rad_age` (int): Radiator age in years

**Optional Columns (Costs & Other):**
- `c_misc` (float): Miscellaneous costs
- `c_misc_ten` (float): Tenant miscellaneous costs
- `p_loss` (float): Power loss percentage
- `tense_market` (bool): Tense housing market indicator

### financial_properties.csv
Financial parameters for each building.

**Note:** This file uses semicolon (;) as delimiter!

**Required Columns:**
- `id` (int): Building ID (must match stock_properties.csv)
- `c_comp` (float): Component renovation costs
- `c_comp_increase` (float): Annual cost increase rate (0-1)
- `rent-1` (float): Rent level 1 (€/m² per month)
- `rent-2` (float): Rent level 2 (€/m² per month)
- `rent-3` (float): Rent level 3 (€/m² per month)
- `cap_rent` (float): Maximum achievable cold rent (€/m² per month)
- `cap_warm_rent` (float): Maximum achievable warm rent (€/m² per month)
- `En_Gas_cost` (float): Gas energy cost (€/kWh)
- `En_HP_cost` (float): Heat pump energy cost (€/kWh)
- `En_El_cost` (float): Electricity cost (€/kWh)

### general_finances.json
Portfolio-wide financial parameters (JSON format).

**Structure:**
```json
{
  "equity": {
    "initial_equity": null,
    "minimal_equity": null,
    "minimum_equity_quota": null
  },
  "liquidity": {
    "initial_liquidity": null,
    "minimal_liquidity": null,
    "liquidity_rate": null
  },
  "liabilities": {
    "initial_liabilities": null,
    "remaining_credit_years": null,
    "debt_interest_rate": null
  },
  "rates": {
    "credit_rate": null,
    "interest_rate": null,
    "inflation_rate": null,
    "avg_construction_price_increase": null,
    "credit_type": null
  },
  "alpha_credit": null,
  "VAT": null,
  "BKI_development": null,
  "year_of_price_origin": null
}
```

### portfolio_caps.json
Portfolio-wide capacity constraints (JSON format).

**Structure:**
```json
{
  "num_measures": {
    "boi_gas": {"start": null, "end": null}
  },
  "labor": {"start": null, "end": null},
  "energy": {
    "gas": {"start": null, "end": null},
    "pel": {"start": null, "end": null}
  },
  "emissions": {"start": null, "end": null},
  "district_heating": {"start": null, "end": null}
}
```

## Import Instructions

1. **Building Data**: Use separate import sections for stock and financial properties
   - Stock Properties: Energetic and structural building data (45 columns)
   - Financial Properties: Economic building parameters (11 columns)
   
2. **Import Mode**:
   - **Concatenate**: Adds new buildings to existing data (IDs auto-incremented)
   - **Replace**: Completely replaces existing building data

3. **Validation**: 
   - Warnings shown for missing expected columns or unknown columns
   - Imports proceed even with warnings (soft validation)
   - Ensure ID consistency between stock and financial files

4. **File Format**:
   - Stock properties: Comma-separated (,)
   - Financial properties: Semicolon-separated (;)
   - JSON files: Standard JSON format with nested structure

## Export Instructions

- Export preserves the correct delimiters and formatting
- Stock and financial properties exported separately
- JSON files maintain nested structure
- Exported files can be directly re-imported

## Template Usage

Templates are provided with all values set to `null` (empty cells in JSON) or empty strings (for CSV text fields).
This ensures a clean starting point for entering your portfolio data.

Fill in the template with your actual building and financial data before importing.

## Notes

- Building IDs must be unique and consistent across stock and financial files
- All cost values are in the currency unit configured for the instance (€)
- Boolean values: True/False (CSV) or true/false (JSON)
- Missing optional columns will use default values from the system
- Energy costs in financial_properties match the energy carrier types
"""
