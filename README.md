# Client Project Name

## Overview
*Replace this with a concise description of the project and the problem it solves.*

### Quick Start Examples
The project includes several quickstart examples to help you get started:

- **Snowflake Connect and SQL**: [Link](quickstarts/snowflake_quickstart.py)
- **Marketo API Requests**: [Link](quickstarts/marketo_api_quickstart.py)

*Related Workfront tasks:*
- *WF-12345: Initial project setup*
- *WF-12346: Feature implementation*

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
2. Close the Local Terminal and then open a new one
2. Install requirements with `poetry install` (this will probably have run automatically)
3. Install the pre-commit hook with `pre-commit install`
4. To add a new requirement, use `poetry add {package}`
5. Copy `config_example.py` to `config.py`, and adjust the project file path for your machine
   - Avoid using the `config.py` file to store secrets. Instead, use the Credentials Manager package
6. The `clevertouch-internal-tools` package will be installed by default. To upgrade this run:
   ```
   poetry add clevertouch-internal-tools==1.1.0 --source gitlab_v2
   ```
   Versions can be found here: [Gitlab Packages](https://gitlab.clever-touch.com/data-and-insights/shared-tools/clevertouch-internal-tools/-/packages)

## Project Structure
The project follows a modular structure with clear separation of concerns:

```
project-root/
├── config_example.py           # Template for configuration settings
├── data/                       # Data files and resources
├── filepaths.py                # File path definitions
├── gitlab_prep/                # GitLab CI/CD related scripts
├── main.py                     # Main entry point for the application
├── quickstarts/                # Example code for quick starts
├── snowflake/                  # Snowflake SQL files and resources
│   ├── snowflake_setup/        # Schema setup scripts
│   ├── snowflake_static_files/ # Static data files for Snowflake
│   └── snowflake_views/        # SQL view definitions
├── src/                        # Source code
│   └── example_group/         # Functional modules
└── testing/                    # Test files mirroring the src structure
```

## Usage
*Add instructions on how to use the project here.*

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
