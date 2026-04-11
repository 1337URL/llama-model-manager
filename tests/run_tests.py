#!/usr/bin/env python3
"""
Test runner script for the llama-model-manager tests.
Supports different test modes: unit, integration, and all tests with coverage.
"""
import subprocess
import sys


def run_tests(mode='all', coverage=False):
    """
    Run tests in the specified mode.

    Modes:
    - 'all': Run all test files
    - 'auth': Run only authentication tests
    - 'api': Run only API tests
    - 'error': Run only error handling tests
    - 'integration': Run integration tests
    - 'module': Run module tests
    - 'templates': Run template tests

    Args:
        mode: Test mode to run
        coverage: Whether to include coverage report
    """
    # Test file mapping
    test_modes = {
        'all': None,  # Run all
        'auth': 'test_auth.py',
        'api': 'test_api.py',
        'error': 'test_error_handling.py',
        'integration': 'test_integration.py',
        'module': 'test_app_module.py',
        'templates': 'test_templates.py',
    }

    if mode != 'all' and mode in test_modes:
        selected_file = test_modes[mode]
        print(f"\n=== Running {mode} tests ({selected_file}) ===\n")
    else:
        print(f"\n=== Running all tests ===\n")

    # Run pytest with appropriate options
    if coverage:
        cmd = [
            'pytest',
            '-v',
            '--cov=app',
            '--cov-report=term-missing',
            '--cov-report=html:coverage_report',
            '--cov-report=xml:coverage.xml'
        ]
        if mode != 'all':
            cmd.extend(['--ignore=tests/test_app_module.py'])  # Skip module tests for coverage
    else:
        cmd = ['pytest', '-v']
        if mode != 'all':
            cmd.extend(['--ignore=tests/test_app_module.py'])  # Skip module tests for speed

    cmd.append('tests/')

    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd, cwd='/', check=False)

    return result.returncode


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Run tests for llama-model-manager')
    parser.add_argument(
        '-m', '--mode',
        choices=['all', 'auth', 'api', 'error', 'integration', 'module', 'templates'],
        default='all',
        help='Test mode to run (default: all)'
    )
    parser.add_argument(
        '-c', '--coverage',
        action='store_true',
        help='Generate coverage report'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress output'
    )

    args = parser.parse_args()

    if not args.quiet:
        print("Llama Model Manager - Test Runner")
        print("=" * 60)

    return run_tests(mode=args.mode, coverage=args.coverage)


if __name__ == '__main__':
    sys.exit(main())
