# Basic Project Template

## 0. Create Fork
- Fork this project into either a client specific folder if its for client work or into the shared tools folder if it would be used across multiple clients.
- Discuss with the team your idea for a shared tool to ensure something doesn't already exist.
- Update forked project to default merge into itself rather than back to the template
  - Select Settings > Merge requests.
  - In the Target project section, select the option you want to use for your default target project.
  - Select Save changes.
- Create branch protections
  - Settings > Repository > Protected Branches

| Branch | Allowed to Merge        | Allowed to Push |
|--------|-------------------------|-----------------|
| Main   | Maintainers             | No one          |
| Dev    | Developers and maintainers | No one      |

  - Default branch should be Dev
- Delete this section of the template.

## 1. CI/CD Setup
This section describes how to setup the package initially for automated code checking and testing.
As standard it runs all the tests in the `testing` folder and runs black/ruff and MyPy with MyPy being allowed to fail.

To get this running initially, turn on Project CI/CD setting:
- Go to Settings -> General -> Visibility, project features, permissions
- Tick the CI/CD option and press save

### 1.1. Keyring Values
If secrets are required for testing/using the package these can be set up as CI/CD variables with the following naming convention
({keyring-name} represents a set of credentials e.g. InternalSnowflake or InternalMarketo):
- KEYRING_{keyring-name}_KEEPER: the Keeper ID for the credentials
- KEYRING_{keyring-name}_{secret}: the value of the secret where {secret} is the secret name

**Example Variables:**
- `KEYRING_MARKETO_KEEPER`: `EXAMPLEKEEPERID`
- `KEYRING_MARKETO_URL`: `https://marketo.com`
- `KEYRING_MARKETO_CLIENT_ID`: `sdgklsdngjnadgadnvljkad`

## 2. Getting Started
1. Follow the instructions in Notion to get poetry set up on your computer.
2. Install the pre-commit hook with `pre-commit install`.
3. Install requirements with `poetry install`. (this will probably have run automatically)
4. To add a new requirement, use `poetry add {package}`.
5. Copy `config_example.py` to `config.py`, and adjust the project file path for your machine.
  - avoid using the `config.py` file to store secrets. Instead use the Credentials Manager package.
6. The `clevertouch-internal-tools` package will be installed by default, currently version 0.0.1. To upgrade this run
the following command `poetry add clevertouch-internal-tools==0.0.1 --source gitlab_v2` where 0.0.1 is replaced with the
version you would like. Versions can be found here: [Gitlab Packages](https://gitlab.clever-touch.com/data-and-insights/shared-tools/clevertouch-internal-tools/-/packages)

## 3. Background
 - Write a short description of the project and the problem it solves.

## 4. Workfront tasks
 - List the workfront tasks that are related to this project.

## 5. Project Structure
 - Describe the project structure and the purpose of each folder.

## 6. Branches
 - Describe the branches that are used in this project.

### 6.1. main
 - The Main Branch contains the latest working code that has passed all tests and can be used for running flows for production.
 - The Main Branch is protected and can only be merged into from the dev Branch.

### 6.2. dev
- The Dev branch is where all development work is merged and tested. Should be used for running flows for testing.
- The Dev Branch is protected and can only be merged into from feature branches.

### 6.3. feature branches
- Feature branches are created for each new feature that is being worked on.
- Feature branches are created from the dev branch and merged back into the dev branch once the feature is complete.
- Feature branches should be deleted once they have been merged into the dev branch.
- Feature branches should be named using the following convention: feature/feature_name
