"""
Portfolio-specific configuration settings.

This module contains all settings related to the building portfolio optimization,
including time horizons, financial parameters, objective function settings,
and emission modeling.
"""

PORTFOLIO_SETTINGS = {
    # Time horizon settings
    "optimization_years":  [2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038, 2039, 2040, 2041, 2042, 2043, 2044, 2045],  # List of optimization periods
    "last_observation_year": 2045,  # Last year of the optimization horizon including length of last period

    # Objective function settings
    "phi_eq": 1,  # objective weighting for equity
    "phi_em": 0,  # objective weighting for emissions
    "phi_obj": 1,  # Weighting factor for multi-objective optimization (0 = cost only, 1 = emissions only)  # TODO: this is wrong
    "cost_emission_scaling": 15,  # Scaling factor to bring cost and emissions to same magnitude in multi-objective optimization
    
    # Two-stage optimization settings
    "phis_obj_two_stage": [0.0, 0.25, 0.5, 0.75, 1.0],  # Phi values for two-stage objective weighting (M4K mode)
    "phi_simplex_N": 5,  # Grid density N for OptiPort phi-triple simplex (OptiPort mode); N=4 gives 15 triples
    "phi_simplex_N_heuristic": 5,  # Grid density N for Phase 5 heuristic solve loop (None = use phi_simplex_N)
    "sols_for_second_stage": "mixed",  # Solution mode: "free", "restricted", or "mixed"
    "use_epsilon_weights": True,

    # Building selection
    "buildings": "all",  # List of building IDs to consider, or "all" for all buildings in the portfolio
    
    # Emissions modeling
    "dynamic_emissions": False,  # Whether to use time-varying emission factors
    
    # Financial parameters
    "VAT": 0.19,  # Value-added tax rate (e.g., 0.19 = 19%)
    "interest_rate": 0.06,  # Discount rate for economic calculations (e.g., 0.06 = 6%)
    "avg_construction_price_increase": 0.026561,
    "year_of_price_origin": 2023,  # Reference year for price data
    
    # District heating settings
    "initialize_dh_cap_automatically": False,  # Whether to automatically initialize district heating capacity

    # Building envelope quality requirements
    "max_u_values": {
        "wall": 0.24,  # Maximum U-value for walls (W/m²K)
        "roof": 0.24,  # Maximum U-value for roofs (W/m²K)
        "win": 1.30,   # Maximum U-value for windows (W/m²K)
    },
    
    # Regulatory constraints
    "geg_required": True,  # Whether GEG (German Building Energy Act) constraints are required
}
