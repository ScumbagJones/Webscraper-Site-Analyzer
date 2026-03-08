"""
Verification script to ensure stress test suite is properly configured

This script:
1. Checks all imports
2. Verifies data directory exists
3. Tests basic Pyppeteer functionality
4. Provides troubleshooting guidance
"""

import sys
from pathlib import Path


def check_imports():
    """Verify all required imports"""
    print("🔍 Checking imports...")

    required_modules = {
        'pyppeteer': 'pip install pyppeteer',
        'asyncio': 'Built-in (should always work)',
        'json': 'Built-in',
        'datetime': 'Built-in'
    }

    missing = []

    for module, install_cmd in required_modules.items():
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError:
            print(f"   ❌ {module} - Install with: {install_cmd}")
            missing.append(module)

    return len(missing) == 0


def check_data_directory():
    """Ensure data directory exists"""
    print("\n📂 Checking data directory...")

    data_dir = Path('data')
    if not data_dir.exists():
        print(f"   ⚠️  Creating data directory...")
        data_dir.mkdir(exist_ok=True)
        print(f"   ✅ Created: {data_dir}")
    else:
        print(f"   ✅ Exists: {data_dir}")

    return True


def check_scripts():
    """Verify all script files exist"""
    print("\n📄 Checking script files...")

    required_files = [
        'stress_test_architectures.py',
        'phenomenology_dashboard.py',
        'run_full_stress_test.py'
    ]

    all_exist = True

    for filename in required_files:
        filepath = Path(filename)
        if filepath.exists():
            print(f"   ✅ {filename}")
        else:
            print(f"   ❌ {filename} - Missing!")
            all_exist = False

    return all_exist


async def test_pyppeteer():
    """Test basic Pyppeteer functionality"""
    print("\n🌐 Testing Pyppeteer...")

    try:
        from pyppeteer import launch

        browser = await launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )

        page = await browser.newPage()
        await page.goto('https://example.com')

        title = await page.title()
        print(f"   ✅ Successfully loaded page: {title}")

        await browser.close()
        return True

    except Exception as e:
        print(f"   ❌ Pyppeteer test failed: {e}")
        print(f"\n   Troubleshooting:")
        print(f"   1. Install chromium: pyppeteer-install")
        print(f"   2. Try running with sudo if permission issues")
        print(f"   3. Check if Chrome/Chromium is installed")
        return False


def print_next_steps(all_passed: bool):
    """Print next steps based on verification results"""
    print("\n" + "="*70)

    if all_passed:
        print(" ✅ VERIFICATION PASSED")
        print("="*70)
        print("\nYour stress test suite is ready to use!\n")
        print("Next steps:")
        print("  1. Run default tests:")
        print("     python run_full_stress_test.py")
        print("\n  2. Run with custom URLs:")
        print("     python run_full_stress_test.py --custom")
        print("\n  3. Run single test:")
        print("     python run_full_stress_test.py --test persistent_state")
        print("\n  4. Read full documentation:")
        print("     cat STRESS_TEST_README.md")

    else:
        print(" ❌ VERIFICATION FAILED")
        print("="*70)
        print("\nPlease fix the issues above before running the stress tests.")
        print("\nCommon fixes:")
        print("  • Install Pyppeteer: pip install pyppeteer")
        print("  • Install Chromium: pyppeteer-install")
        print("  • Ensure all script files are present")


async def run_verification():
    """Run all verification checks"""
    print("\n" + "="*70)
    print(" 🧪 STRESS TEST SUITE VERIFICATION")
    print("="*70 + "\n")

    checks = [
        ("Imports", check_imports()),
        ("Data Directory", check_data_directory()),
        ("Script Files", check_scripts()),
        ("Pyppeteer", await test_pyppeteer())
    ]

    all_passed = all(result for _, result in checks)

    print_next_steps(all_passed)

    return all_passed


if __name__ == "__main__":
    import asyncio

    try:
        result = asyncio.run(run_verification())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted")
        sys.exit(1)
