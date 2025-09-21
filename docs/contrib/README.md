# kdevops Contribution Analysis

This directory contains contribution visualization tools and generated reports for the kdevops project.

## Overview

The contribution analysis provides comprehensive insights into kdevops development patterns, contributor activity, and project health over time. These visualizations help understand:

- **Contributor Activity**: Who is actively contributing to the project
- **Development Patterns**: When and how frequently contributions occur
- **Project Health**: Overall activity levels and contributor diversity
- **Timeline Analysis**: How the project has evolved over time

## Quick Start

Generate contribution graphs using the built-in make target:

```bash
# Generate graphs for a specific year
make contrib-graph YEAR=2025

# Generate graphs for all project history
make contrib-graph
```

## Generated Files

The visualization tool creates comprehensive 6-panel dashboards saved as:

### For Specific Year
- `kdevops_contributions_YYYY.png` - High-resolution image (300 DPI)
- `kdevops_contributions_YYYY.pdf` - Vector format for scalability

### For All Time
- `kdevops_contributions_all_time.png` - High-resolution image
- `kdevops_contributions_all_time.pdf` - Vector format

## Visualization Components

Each generated dashboard includes six analytical panels:

### 1. Total Commits Bar Chart
Shows the overall contribution ranking by commit count. Names are automatically shortened for contributors with fewer commits to prevent overlapping labels.

### 2. Contribution Distribution Pie Chart
Displays the percentage distribution of contributions among top contributors, with smaller contributors grouped as "Others" for clarity.

### 3. Monthly Activity Heatmap
Visual representation of when contributors are most active throughout the year. Intensity indicates commit volume.

### 4. Monthly Timeline Graph
Line graph showing total project activity over time, with actual commit counts labeled on data points.

### 5. Top Contributors Timeline
Individual activity patterns for the top 3 contributors, showing their monthly contribution patterns.

### 6. Statistics Summary
Key metrics including:
- Total commits and contributors
- Average commits per person
- Most active month
- Top contributor
- Analysis period and generation timestamp

## Technical Details

### Date Handling
- **Smart Filtering**: Only shows data up to the current date (no future commits)
- **Period Accuracy**: Respects actual time boundaries (e.g., if run on July 31, 2025, won't show August-December data)
- **Validation**: Prevents analysis of invalid years (too early or future years)

### Data Sources
All data is extracted directly from the git repository using:
- `git log` for commit history
- Author information from git commit metadata
- Date filtering for accurate time period analysis
- No synthetic or fabricated data

### Dependencies
The visualization tool requires:
- Python 3.x
- matplotlib
- seaborn
- pandas
- numpy

These are automatically installed via system packages when running the tool.

## Usage Examples

### Annual Review
```bash
# Generate 2025 contribution report
make contrib-graph YEAR=2025
```

### Project History
```bash
# Generate complete project history
make contrib-graph
```

### Specific Year Analysis
```bash
# Analyze any specific year
make contrib-graph YEAR=2024
make contrib-graph YEAR=2023
```

## Error Handling

The tool includes comprehensive error checking:

- **Future Years**: Prevents analysis of years beyond current date
- **Invalid Years**: Validates year format and reasonable ranges
- **Git Repository**: Ensures tool is run from within a git repository
- **Empty Data**: Handles periods with no commits gracefully

## Integration

The contribution analysis is integrated into the kdevops build system:

- **Makefile Target**: `make contrib-graph`
- **Parameter Support**: Optional `YEAR=YYYY` parameter
- **Output Location**: Files saved to `docs/contrib/`
- **Style Compliance**: Follows kdevops coding standards

## Interpretation Guide

### High Activity Periods
- **March Surge**: Often indicates major development phases
- **Consistent Activity**: Shows healthy, sustained development
- **Seasonal Patterns**: May reflect developer availability/schedules

### Contributor Patterns
- **Core Contributors**: High commit counts, consistent activity
- **Occasional Contributors**: Lower counts, sporadic activity
- **New Contributors**: Recent activity increase

### Project Health Indicators
- **Growing Contributor Base**: More contributors over time
- **Sustained Activity**: Regular commits throughout periods
- **Balanced Contributions**: Activity from multiple contributors

## Files in This Directory

- `README.md` - This documentation
- `kdevops_contributions_*.png` - Generated visualization images
- `kdevops_contributions_*.pdf` - Generated vector graphics
- Historical contribution reports (accumulate over time)

## Troubleshooting

### Common Issues

**"No contributions found"**
- Check that you're in a git repository
- Verify the specified year has commits
- Ensure date range is valid

**"Year is in the future"**
- The tool prevents analysis of future dates
- Use current or past years only

**Missing dependencies**
- Run `sudo apt install python3-matplotlib python3-seaborn python3-pandas python3-numpy`
- Or let the Makefile handle dependency installation

### Getting Help

For issues with the contribution analysis tool:
1. Check that all dependencies are installed
2. Verify you're in the kdevops git repository root
3. Review error messages for specific guidance
4. Consult the main project documentation

## Contributing

The contribution analysis tool itself can be improved:

- **Source**: `scripts/contrib_graph.py`
- **Integration**: Makefile target definition
- **Standards**: Follow kdevops coding and documentation standards
- **Testing**: Verify with multiple years and edge cases

Suggestions for enhancements are welcome through the standard kdevops contribution process.
