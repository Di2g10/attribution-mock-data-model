# Basic Project Template


## 1. Getting started

- Create Venv if one doesn't already exist.
- Activate Venv if neccessary '\venv\Scripts\activate.ps1'
- Install Requirements 'pip install -r requirements.txt'
- Copy config_example.py into config.py
  - Add passwords to config.py
  - Check project file path matches for you machine and the relevant folders are synced locally.
- Activate the precommit hook with 'pre-commit install' in the terminal

## 2. Background
 - Write a short description of the project and the problem it solves.

## 3. Workfront tasks
 - List the workfront tasks that are related to this project.

## 4. Project Structure
 - Describe the project structure and the purpose of each folder.

## 5. Branches
 - Describe the branches that are used in this project.

### 5.1. main
 - The Main Branch contains the latest working code that has passed all tests and can be used for running flows for production.
 - The Main Branch is protected and can only be merged into from the dev Branch.

### 5.2. dev
- The Dev branch is where all development work is merged and tested. Should be used for running flows for testing.
- The Dev Branch is protected and can only be merged into from feature branches.

### 5.3. feature branches
- Feature branches are created for each new feature that is being worked on.
- Feature branches are created from the dev branch and merged back into the dev branch once the feature is complete.
- Feature branches should be deleted once they have been merged into the dev branch.
- Feature branches should be named using the following convention: feature/feature_name
