# OptiPort MILP Optimization Visualization Interface

A comprehensive Streamlit-based visualization application for analyzing Mixed Integer Linear Programming (MILP) optimization results from the OptiPort building energy optimization framework.

## 🎯 Features

### Core Functionality
- **Instance Management**: Browse and select optimization instances from `run/use_cases/` and `data/instances/`
- **Solution Analysis**: Parse and visualize `.sol` files from MILP optimizations
- **Interactive Visualizations**: Multiple chart types for different aspects of the optimization results
- **Modular Architecture**: Extensible structure for adding new visualizations and features

### Current Visualizations
- **Investment Timeline**: Technology adoption decisions across time periods
- **Technology Portfolio**: Analysis of technology mix and capacity distribution
- **Building-Level Analysis**: Detailed view of individual building solutions
- **Financial Metrics**: Cost analysis and objective value breakdown

### Instance Features
- **Automatic Discovery**: Scan directories for available optimization instances
- **Validation**: Check instance completeness and configuration
- **Configuration Preview**: View and analyze CSV/JSON configuration files
- **Solution Status**: Real-time solution availability and status

## 🏗️ Architecture

```
visualization/
├── main.py                    # Main Streamlit application
├── config/                    # Configuration settings
├── core/                      # Core functionality (parsers, managers)
├── components/                # Reusable UI components
├── pages/                     # Application pages
├── visualizations/            # Specific visualization modules
├── utils/                     # Utility functions
└── requirements.txt           # Dependencies
```

## 📦 Installation

### Prerequisites
- Python 3.8+
- OptiPort project structure with optimization instances

### Dependencies Installation
```bash
cd visualization
pip install -r requirements.txt
```

Required packages:
- streamlit>=1.28.0
- plotly>=5.15.0
- pandas>=2.0.0
- numpy>=1.24.0
- seaborn>=0.12.0
- matplotlib>=3.7.0
- altair>=5.0.0
- pydantic>=2.0.0

## 🚀 Usage

### Launch the Application
```bash
cd visualization
streamlit run main.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Navigation
1. **Instance Overview**: Start by selecting an optimization instance
2. **Optimization Results**: View detailed analysis and visualizations
3. **Create Instance**: (Future) Create new optimization scenarios
4. **Compare Results**: (Future) Compare multiple instances

### Workflow
1. **Select Instance**: Choose from available instances in the sidebar
2. **Validate**: Check instance completeness and configuration
3. **Analyze Results**: Explore different visualization tabs
4. **Export**: Download results and charts (where available)

## 📊 Supported Data Formats

### Solution Files (.sol)
The application parses MILP solution files with variables in formats:
- `X_in_building_timeperiod_technology`: Binary installation decisions
- `E_in_building_timeperiod_technology`: Energy capacity variables
- `P_*`: Power flow variables
- `Q_*`: Additional operational variables

### Configuration Files
- `building_constraints.csv`: Building-specific constraints
- `financial_properties.csv`: Financial parameters
- `general_finances.json`: General financial settings
- `portfolio_caps.csv/json`: Portfolio constraints
- `stock_properties.csv`: Building stock properties

### Instance Structure
Expected instance directory structure:
```
instance_name/
├── building_constraints.csv
├── financial_properties.csv
├── general_finances.json
├── portfolio_caps.csv
├── stock_properties.csv
└── results/
    └── instance_name.sol
```

## 🎨 Visualizations

### Investment Analysis
- **Timeline View**: Technology installations over time periods
- **Heatmap**: Investment intensity by technology and time
- **Hierarchy**: Sunburst chart of category → technology → installation

### Technology Mix
- **Portfolio Distribution**: Pie chart of technology categories
- **Individual Technologies**: Bar chart of specific technology counts
- **Capacity Analysis**: Energy capacity breakdown by technology

### Data Views
- **Raw Data**: Filterable table of all optimization variables
- **Summary Statistics**: Key metrics and performance indicators
- **Export Options**: Download results in various formats

## 🔧 Configuration

### Application Settings
Modify `config/app_config.py` for:
- File paths and patterns
- Technology categorizations
- Color schemes
- Variable type definitions

### Visualization Settings
Adjust `config/visualization_config.py` for:
- Chart dimensions and styling
- Export settings
- Dashboard layout parameters

## 📈 Extending the Application

### Adding New Visualizations
1. Create a new class inheriting from `BaseVisualization`
2. Implement the `create_figure()` method
3. Add to the appropriate page's tab structure

### Adding New Pages
1. Create page class in `pages/`
2. Add navigation option in `components/sidebar.py`
3. Register in `main.py` routing

### Custom Data Processing
Add new utilities in `utils/data_processing.py` for:
- Variable parsing logic
- Data aggregation functions
- Statistical calculations

## 🐛 Troubleshooting

### Common Issues

**No instances found**
- Ensure instances exist in `run/use_cases/` or `data/instances/`
- Check directory structure and file permissions

**Solution parsing errors**
- Verify `.sol` file format and location
- Check for special characters or encoding issues

**Visualization errors**
- Ensure all required data is available
- Check variable naming conventions

**Performance issues**
- Large solution files may take time to parse
- Consider filtering data for better performance

### Debugging
Enable detailed logging by setting:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🔮 Future Enhancements

### Planned Features
- **Instance Creation**: GUI for building new optimization scenarios
- **Real-time Optimization**: Run optimizations from the interface
- **Advanced Analytics**: Machine learning insights and sensitivity analysis
- **Multi-instance Comparison**: Side-by-side result comparison
- **Export Capabilities**: PDF reports and presentation-ready charts
- **Data Validation**: Input parameter checking and consistency validation

### Architecture Improvements
- **Caching**: Redis/file-based caching for large datasets
- **Database Integration**: Store results in structured databases
- **API Integration**: RESTful API for external tool integration
- **Authentication**: User management and access control

## 📝 Contributing

### Development Guidelines
1. Follow the modular architecture pattern
2. Add comprehensive docstrings and type hints
3. Include error handling and logging
4. Test with various instance types and sizes
5. Update documentation for new features

### Code Style
- Follow PEP 8 conventions
- Use meaningful variable and function names
- Comment complex logic and algorithms
- Maintain consistent import organization

## 📄 License

This visualization interface is part of the OptiPort project. Please refer to the main project license for terms and conditions.

## 🤝 Support

For questions, issues, or feature requests:
1. Check existing documentation and troubleshooting guides
2. Review the codebase for similar implementations
3. Contact the OptiPort development team
4. Submit issues with detailed reproduction steps

---

**Happy Optimizing! 🏭📊**
