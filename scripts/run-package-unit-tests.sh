#!/bin/bash
# ABOUTME: Pre-commit hook script that runs unit tests for changed packages
# ABOUTME: Detects which packages have changes and runs only unit tests (not integration)

set -e

# Get list of changed files in packages directory
changed_files=$(git diff --cached --name-only | grep "^packages/" || true)

if [ -z "$changed_files" ]; then
    echo "No changes in packages directory, skipping tests"
    exit 0
fi

# Extract unique package names from changed files
packages=$(echo "$changed_files" | cut -d'/' -f2 | sort -u)

echo "Changed packages: $packages"

# Run unit tests for each changed package
for package in $packages; do
    echo "Running unit tests for package: $package"

    # Check if package has tests directory
    if [ ! -d "packages/$package/tests" ]; then
        echo "No tests directory found for $package, skipping"
        continue
    fi

    # Run unit tests only (exclude integration, manual, and audio tests)
    echo "  uv run --package $package pytest packages/$package/tests/ -m 'not integration and not manual and not audio' --tb=short -q"
    if ! uv run --package "$package" pytest "packages/$package/tests/" -m "not integration and not manual and not audio" --tb=short -q; then
        echo "Unit tests failed for package: $package"
        exit 1
    fi

    echo "Unit tests passed for $package ✓"
done

echo "All unit tests passed for changed packages ✓"
