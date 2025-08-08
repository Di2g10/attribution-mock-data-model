# BT Attribution Mock Data Generator

## Overview
A comprehensive mock data generator for BT marketing attribution analysis. This tool creates realistic, interconnected datasets that model marketing attribution relationships, customer interactions, and sales data for testing and development purposes.

The generator produces CSV files with consistent relationships between entities such as companies, people, marketing campaigns, interactions, and orders - allowing for realistic attribution modeling and analysis.

## Quick Start

### Installation
1. Clone the repository
2. Install dependencies with Poetry:
   ```
   poetry install
   pre-commit install
   ```

### Running the Generator
To generate a complete set of mock data:

```bash
python main.py
```

This will:
1. Read the structure definition from the Excel file in `data/input/`
2. Generate all required datasets in the correct order
3. Save CSV files to the `mock_output/` directory

### Quickstart Example
The project includes a quickstart example to help you get started:

```bash
python quickstarts/mock_data_quickstart.py
```

This example:
- Generates a smaller set of mock data for faster execution
- Performs basic analysis on the attribution data
- Shows how to use the generated data programmatically

## Project Setup

### Initial Repository Setup
- Fork this project into the client-specific folder if it's for client work. Make sure it includes the client's name at the beginning of the project name (makes it easier to find in PyCharm)
- Update forked project to default merge into itself rather than back to the template
  - Select Settings > Merge requests
  - At the bottom, in the Target project section, choose the new project as the default target project
  - Select Save changes
- Create branch protections
  - Settings > Repository > Protected Branches

| Branch | Allowed to Merge        | Allowed to Push |
|--------|-------------------------|-----------------|
| Main   | Maintainers             | No one          |
| Dev    | Developers and maintainers | No one      |

### Development Environment Setup
1. Create a new branch to start working in
2. Close the Local Terminal (if it's currently open) and then open a new one
3. Install requirements with `poetry install` (this will probably have run automatically)
4.  Install the pre-commit hook with `pre-commit install`
5. To add a new requirement, use `poetry add {package}`
6. Copy `config_example.py` to `config.py`, and adjust the project file path for your machine
   - Avoid using the `config.py` file to store secrets. Instead, use the Credentials Manager package
7. The `clevertouch-internal-tools` package will be installed by default. To upgrade this run:
   ```
   poetry add clevertouch-internal-tools==1.1.0 --source gitlab_v2
   ```
   Versions can be found here: [Gitlab Packages](https://gitlab.clever-touch.com/data-and-insights/shared-tools/clevertouch-internal-tools/-/packages)

## Project Structure
The project follows a modular structure with clear separation of concerns:

```
bt-attribution-mock-data/
├── config_example.py           # Template for configuration settings
├── data/                       # Data files and resources
│   └── input/                  # Input files defining data structure
├── filepaths.py                # File path definitions
├── gitlab_prep/                # GitLab CI/CD related scripts
├── main.py                     # Main entry point for the application
├── mock_output/                # Generated CSV output files
├── src/                        # Source code
│   ├── generators/             # Data generator modules
│   ├── config_loader.py        # Configuration loading utilities
│   ├── orchestrator.py         # Coordinates the data generation process
│   ├── random_utils.py         # Utilities for random data generation
│   ├── schema_registry.py      # Manages schema definitions
│   └── validation.py           # Data validation utilities
└── testing/                    # Test files mirroring the src structure
```

## Generated Datasets
The generator produces the following CSV files in the `mock_output/` directory:

| File | Description |
|------|-------------|
| Attribution Linking Table.csv | Links between marketing activities and outcomes |
| Audience.csv | Target audience definitions |
| Campaigns.csv | Marketing campaign details |
| Channels.csv | Marketing channels (email, social, etc.) |
| Company.csv | Company/account information |
| Date Dimension.csv | Date reference data |
| Facilitation Tool.csv | Tools used in marketing activities |
| Interactions.csv | Customer interactions with marketing assets |
| Marketing Activity.csv | Marketing activities and events |
| Marketing Assets.csv | Marketing content and assets |
| Orders.csv | Sales orders and transactions |
| Person Company Role.csv | Relationships between people and companies |
| Person.csv | Individual contact information |
| Products.csv | Product catalog information |

## Data Generation Process
The data generation follows a specific order to maintain referential integrity:

1. Base entities (Companies, People, Products, etc.) are generated first
2. Relationship entities (Person-Company roles, etc.) are generated next
3. Marketing entities (Campaigns, Assets, Activities) follow
4. Interaction data is generated based on the marketing entities
5. Orders and attribution data are generated last, referencing all previous entities

Each generator maintains relationships with previously generated entities to ensure data consistency.

## Performance Considerations
The generator is optimized for performance when creating large datasets:

### Vectorized Operations
- Uses NumPy's vectorized random operations instead of individual random calls
- Generates batches of random values at once rather than in loops
- Pre-generates and reuses values where appropriate

### Memory Efficiency
- Limits the generation of expensive objects (like Faker instances)
- Uses sampling pools for frequently accessed random values
- Optimizes data structures to reduce memory usage during generation

### Tips for Large Datasets
- For very large datasets (>100,000 rows), consider generating in smaller batches
- Monitor memory usage when generating extremely large datasets
- The first few objects (especially Company and Person) may take longer to generate due to their role as foundation entities

### Performance Optimizations
The code includes several specific optimizations:
- Vectorized random sampling in `make_ids_with_duplicates`
- Pre-generation of industry mappings in the company generator
- Limited pool of locations to reduce expensive Faker calls
- Efficient handling of None values in ID generation

## Usage
To generate mock data, simply run the main script:

```bash
python main.py
```

The script will:
1. Load the structure definition from the Excel file in the data/input directory
2. Generate all datasets in the correct order to maintain relationships
3. Write CSV files to the mock_output directory

You can modify the generation parameters by editing the Excel structure file.

## CI/CD Pipeline
The project includes a GitLab CI/CD pipeline that automates code quality checks, testing, and deployment. The pipeline includes:

1. **Validation**: Ensures merge requests to main come from the dev branch
2. **Code Quality**: Runs Black, Ruff, SQL Fluff, and MyPy
3. **Testing**: Runs unit tests with coverage reporting for Python 3.10 and 3.11
4. **Build and Deploy**: Handles Snowflake deployments to dev and prod environments

### Keyring Values
If secrets are required for testing/using the package, these can be set up as CI/CD variables with the following naming convention:

- `KEYRING_{keyring-name}_KEEPER`: the Keeper ID for the credentials
- `KEYRING_{keyring-name}_{secret}`: the value of the secret where {secret} is the secret name

**Example Variables:**
- `KEYRING_MARKETO_KEEPER`: `EXAMPLEKEEPERID`
- `KEYRING_MARKETO_URL`: `https://marketo.com`
- `KEYRING_MARKETO_CLIENT_ID`: `sdgklsdngjnadgadnvljkad`

### Snowflake Environment Setup
To set up this project to work with the Snowflake environments managed by GitLab:

1. Configure the `gitlab_prep/snowflake_schema_setup.json` file with your project-specific settings
2. Set the required Keeper Credentials in the CI/CD Variables:
   - `USERNAME`: the username for logging in
   - `PASSWORD`: the password for logging in
   - `ACCOUNT`: the account from the URL, e.g., 'am20982.europe-west2.gcp'

## Branch Structure and Workflow

### main
- Contains the latest working code that has passed all tests
- Used for running flows in production
- Protected and can only be merged into from the dev branch

### dev
- Where all development work is merged and tested
- Used for running flows in testing environments
- Protected and can only be merged into from feature branches

### feature branches
- Created for each new feature or bugfix
- Always branch from dev, not from other feature branches
- Merge back into dev once the feature is complete
- Should be deleted after merging
- Naming convention: `feature/descriptive-name` or `bugfix/issue-description`
- Keep feature branches short-lived and focused on a single task
- Regularly pull changes from dev to avoid merge conflicts
- Merge requests should be created to merge this into the dev branch
