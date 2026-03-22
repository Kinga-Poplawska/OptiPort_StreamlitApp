"""
Data models for processed JSON optimization results.
Replaces the old .sol-based models entirely.
"""
from dataclasses import dataclass
from typing import Dict, List
from pathlib import Path


@dataclass
class UseCaseMetadata:
    """Metadata for a discovered use case with processed results."""
    name: str
    path: Path
    results_path: Path
    building_ids: List[int]


@dataclass
class ProcessedBuildingResult:
    """
    Mirrors the top-level structure of building_{id}_results.json exactly.

    Keys inside the sub-dicts follow the conventions from process_results.py:
      - Period keys: "t0", "t2", ... (str)  → use parse_period_dict() to convert to int
      - Measure×period keys: "{measure}_t{i}" (str)
    """
    building_id: int
    building_type: str
    construction_year: int

    # Step 1 – transformation_pathway
    transformation_pathway: Dict  # keys: available_measures, installed_measures,
                                  #       available_hull_measures, boni_by_period,
                                  #       investment_by_measure, om_costs_by_measure,
                                  #       costs_investment, om_costs,
                                  #       embodied_by_measure, emissions_embodied

    # Step 2 – operational_data
    operational_data: Dict        # keys: costs_operational, emissions_operational,
                                  #       emissions_operational_fossil

    # Step 3 – totals
    totals: Dict                  # keys: costs_total, emissions_total

    # Step 4 – optiport_data  (empty dict {} when optiport_model was False)
    optiport_data: Dict           # keys: bonus_per_measure, net_cost_per_measure,
                                  #       net_cost_sub_per_measure, credits,
                                  #       depreciation_per_measure,
                                  #       depreciation_existing_per_measure,
                                  #       bonus, interest,
                                  #       repayment, installation_costs,
                                  #       uninstallation_costs, subsidies,
                                  #       availability_costs, co2_costs, energy_costs,
                                  #       rent, modernization_costs,
                                  #       modernization_costs_heat,
                                  #       liquidity,
                                  #       equity, debt,
                                  #       emissions_energy, emissions_fossil,
                                  #       emissions_fossil_shares,
                                  #       co2_group_assignment,
                                  #       total_emissions_optiport,
                                  #       geg_compliance, z_mod_cap, z_max


@dataclass
class ProcessedPortfolioResult:
    """
    Mirrors the structure of portfolio_results.json exactly.
    All period-keyed dicts use string keys ("t0", "t2", …).
    Use parse_period_dict() to get int-keyed versions for plotting.
    """
    total_buildings: int
    building_ids: List[int]

    # Capacity aggregates  – measure×period flat keys e.g. "eh_t0"
    capacity_available_total: Dict[str, float]
    capacity_installed_total: Dict[str, float]
    capacity_available_count: Dict[str, int]
    capacity_installed_count: Dict[str, int]

    # Investment by measure – flat keys "c_inv_{measure}_t{period}", summed across buildings
    investment_by_measure_total: Dict[str, float]

    # Cost / emission per period  – period keys "t0", "t2", …
    costs_investment: Dict[str, float]
    costs_operational: Dict[str, float]
    costs_total: Dict[str, float]
    emissions_embodied: Dict[str, float]
    emissions_operational: Dict[str, float]
    emissions_total: Dict[str, float]
    thermal_demand: Dict[str, float]

    # OptiPort financial aggregates  – period keys
    rent_total: Dict[str, float]
    energy_costs_total: Dict[str, float]
    modernization_costs_total: Dict[str, float]
    emissions_energy_total: Dict[str, float]
    emissions_fossil_total: Dict[str, float]
    liquidity: Dict[str, float]
    liquidity_critical: Dict[str, float]
    equity: Dict[str, float]
    debt: Dict[str, float]
    total_emissions_optiport: float
    credits_total: Dict[str, float]

    # Warm rent aggregated across buildings per period
    warm_rent_total: Dict[str, float]

    # Grand totals (scalars)
    costs_investment_total: float
    costs_operational_total: float
    costs_total_all: float
    emissions_embodied_total: float
    emissions_operational_total: float
    emissions_total_all: float
    thermal_demand_total: float

    # Constraint parameters (bounds for reference lines)
    constraint_params: Dict
