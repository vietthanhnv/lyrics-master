# Project Structure

This workspace is currently empty and ready for project organization.

## Current Structure

```
.
├── .kiro/
│   └── steering/
│       ├── product.md
│       ├── tech.md
│       └── structure.md
```

## Recommended Organization

When setting up the project, consider this general structure:

```
.
├── .kiro/                  # Kiro configuration and steering
├── src/                    # Source code
├── tests/                  # Test files
├── docs/                   # Documentation
├── config/                 # Configuration files
├── scripts/                # Build and utility scripts
├── assets/                 # Static assets (images, etc.)
├── .gitignore             # Git ignore rules
├── README.md              # Project documentation
└── [build-config]         # Build configuration (package.json, etc.)
```

## Naming Conventions

- Use lowercase with hyphens for directory names when possible
- Use descriptive, clear names for files and folders
- Group related functionality together
- Separate concerns (source, tests, docs, config)

## File Organization

- Keep related files close together
- Use index files for clean imports/exports
- Maintain consistent directory depth
- Avoid deeply nested folder structures when possible

## Documentation

- Include README.md in root directory
- Document complex modules and functions
- Keep documentation close to relevant code
- Update documentation when code changes
