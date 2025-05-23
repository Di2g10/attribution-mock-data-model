# Junie AI Agent Guidelines for Code Generation and Project Conventions

This document provides specific guidelines for Junie, the AI agent, to ensure generated code and interactions conform to the client project standards and conventions.

## General Principles

- Always prioritise code clarity, maintainability, and alignment with existing coding patterns in the project.
- Ensure generated code is consistent with Python 3.11 style and uses type annotations where applicable.
- Follow client project structure conventions: new functionality belongs in the correct package/module, matching the existing pattern.
- Never introduce external package managers or install methods other than Poetry. Use `poetry add {package}` when dependencies must be mentioned.
- Preserve existing public APIs; avoid breaking changes unless explicitly instructed.

## Project Structure

- The project follows a modular structure with clear separation of concerns.
- Source code is organized in the `src` directory with appropriate subdirectories for different functional areas.
- Tests are placed in the `testing` directory, mirroring the structure of the source code.
- Snowflake-related SQL files are organized in the `snowflake` directory.
- Configuration and utility scripts are placed in the project root or appropriate subdirectories.
- Follow existing patterns when adding new files or modules.

## Coding Style

- Use Black and Ruff compatible formatting; prioritise readability and PEP-8 compliance.
- Follow ruff, mypy, and black guidelines as outlined in the project's toml file.
- Use the latest Python style guidelines consistent with Python 3.12.
- Write code in British English spelling conventions.
- Generate a Sphinx-style docstring using :param:, :raises: and :returns: directives.
- Include type hints for all public functions and classes.
- Keep functions small with less than 50 lines and maintain low branching complexity.
- Avoid complex nested logic; prefer simple, testable units.
- Access nested module functions through the respective `__init__.py` exports, when appropriate.
- Inline error handling with clear exception messages aligned with project patterns.
- Never use a bare except.
- Use snake_case for functions and variables, PascalCase for classes, and UPPER_SNAKE_CASE for constants.

## Testing

- Use the built-in `unittest` framework for all test code.
- Test the correctness of the solution before submitting.
- Keep tests simple, clear, and concise.
- Place tests in the appropriate test folder following existing package test structures.
- Cover relevant edge cases and typical scenarios.
- Ensure tests align with the project's existing testing style.

## Static Analysis and Type Checking

- MyPy type checking is required; ensure generated code passes MyPy validation with strictness fitting the project.
- Adhere to type annotations consistently throughout the codebase.

## Credentials and Secrets

- Never hard-code secrets or credentials in the code.
- Reference credentials according to Keyring conventions if necessary for example code.
- Use `KEYRING_{keyring-name}_{secret}` naming conventions when referring to environment variables or CI/CD variables.

## Documentation and Readability

- Add or update README snippets if the generated code influences user-facing functionality or usage patterns.
- Link to relevant project documentation or READMEs when introducing new packages or APIs.
- Use consistent Markdown style in documentation sections.
