# AWS Cost and Usage Report (CUR) Analytics with Rill

This project provides a comprehensive, automated solution for analyzing AWS Cost and Usage Reports (CUR). It takes raw CUR data exported in Parquet format, processes it, and dynamically generates a powerful, interactive dashboard using [Rill](https://www.rilldata.com/).

## Goal

The primary goal is to significantly lower the barrier to gaining deep insights from complex AWS cost data. Manually building dashboards for CUR data is challenging due to:

- **Complex Schemas:** CUR files have many columns, and schemas can change.
- **Nested Data:** Key information like resource tags is often nested in MAP columns, making it difficult to use in BI tools.
- **Dynamic Nature of Tags:** The set of resource tags and their values are unique to every organization and change over time. A static dashboard cannot effectively visualize them.

This project automates the entire pipeline from raw data to a rich, interactive analytics experience, providing "best-practice" visualizations out-of-the-box.

## How It Works

The process is orchestrated by the `run.sh` script and consists of two main stages:

### 1. Data Normalization (`scripts/normalize.py`)

This script prepares the raw CUR data for analysis.

- It reads all Parquet files from the specified `INPUT_DATA_DIR`. It uses DuckDB's `UNION_BY_NAME` capability to gracefully handle multiple files that may have slightly different schemas, which is common with CUR exports over time.
- Its key function is to **flatten nested MAP columns**. AWS often stores resource tags (e.g., `resource_tags_user_cost_center`) and other attributes as MAP types. The script automatically expands these into standard columns (e.g., `resource_tags_user_cost_center_finance`, `resource_tags_user_cost_center_engineering`), making them directly available for filtering and grouping.
- The final, clean, and flattened dataset is written to a single `normalized.parquet` file in the `NORMALIZED_DATA_DIR`.

### 2. Dynamic Dashboard Generation (`scripts/rill_project_generator.py`)

This is the core logic that inspects the schema of the `normalized.parquet` file and generates a complete Rill project tailored to the available data.

- **Dynamic Model Creation:** It creates Rill source and metrics view files (`sources/aws_cost_source.yml`, `metrics/aws_cost_metrics.yml`). The generator defines several useful derived metrics, such as `total_effective_cost` and `cost_per_unit`, but only if the necessary base columns exist in the data.

- **Intelligent Canvas Generation:** This is a key innovation of the project. The script uses a sophisticated chart selection algorithm (`scripts/utils/dimension_chart_selector.py`) to create dedicated dashboards for different groups of dimensions (like resource tags, product attributes, etc.). For each group (e.g., columns prefixed with `resource_tags_`), it generates a custom canvas:

  1.  It analyzes each column to determine if it's "worth charting" based on cost coverage and cardinality.
  2.  It applies a "dominant slice" rule: if one or two values account for a majority of the spend, they are highlighted as KPIs.
  3.  It selects the best chart type (Pie, Bar Chart, or Leaderboard) for the remaining values based on their cardinality.

  This results in dashboard pages that are perfectly customized to your organization's unique data, generated dynamically from the `templates/map_canvas_template.yml.j2` template.

## How to Use

### 1. Prerequisites

- Python 3.x
- [Rill](https://docs.rilldata.com/install) CLI installed.

### 2. Setup

```bash
# Clone the repository if you haven't already
cd aws-cost-tracker

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

- Create a `.env` file in the `aws-cost-tracker` directory.
- Add the following variables to your `.env` file, replacing the example paths with your actual paths:

  ```
  # Path to the directory containing your raw Parquet CUR files
  INPUT_DATA_DIR=./data/input

  # Path where the intermediate normalized Parquet file will be stored
  NORMALIZED_DATA_DIR=./data/normalized

  # Path to the Rill project directory that will be generated
  RILL_PROJECT_PATH=./rill_project
  ```

- Place your AWS CUR Parquet files inside the `INPUT_DATA_DIR`.

### 4. Run

The `run.sh` script is the main entrypoint. It now accepts command-line arguments to customize the generated dashboard.

```bash
# Basic run, will prompt for cost column
./run.sh

# Specify the main cost column to use
./run.sh --cost-col line_item_blended_cost

# Generate separate dashboards for resource tags and product columns
./run.sh --tag-prefixes "resource_tags_,product_"
```

You can see all available options by running:

```bash
./run.sh --help
```

The script will normalize your data, generate the Rill project based on your configuration, and automatically launch the Rill UI in your browser.

## Project Structure

- `run.sh`: Main execution script. It parses command-line arguments and orchestrates the workflow.
- `scripts/`: Contains the core Python logic.
  - `normalize.py`: Flattens and cleans raw CUR data.
  - `generate_rill_yaml.py`: A thin command-line wrapper that passes arguments to the generator.
  - `rill_project_generator.py`: The core library for generating the Rill project YAML.
  - `utils/dimension_chart_selector.py`: The intelligent logic for selecting charts for dynamic canvases.
- `templates/`: Jinja2 templates for the Rill YAML files.
- `data/`: Recommended location for input and normalized data.
- `rill_project/`: The generated Rill project (populated by the script).

## Known Issues & Future Work

- **Dynamic Metrics:** The generation of derived metrics in the `metrics_view` (e.g. `total_unblended_cost`) is currently based on a series of `if/else` blocks in the Jinja template. This works for common cost columns but is not a fully elegant or scalable solution. A more robust system would dynamically define these metrics based on the selected `--cost-col` and available columns without hardcoding.
- **Argument Support:** While the script now accepts various arguments, the interaction between them is still being refined. For example, the `cost_measure` used in the dynamic canvases relies on a simple heuristic to guess the final measure name. This may not work correctly for all user-selected cost columns.

## Acknowledgements

A special thanks to [Dan Goldin](https://www.linkedin.com/in/dgoldin/) for the initial idea and inspiration for this project.
