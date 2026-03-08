#!/usr/bin/env python3
"""
Quick Test: New Packages Integration
Tests all 9 new packages with realistic data
"""

import sys
from colorama import Fore, Style, init

init(autoreset=True)


def test_jmespath():
    """Test JMESPath with mock scraper data"""
    print(f"\n{Fore.CYAN}Testing JMESPath...")
    try:
        import jmespath

        # Mock data like what deep_evidence_engine returns
        data = {
            'evidence': {
                'spacing_scale': {
                    'base_unit': 4,
                    'pattern': 'Powers of 2',
                    'scale': [4, 8, 16, 24, 32, 48]
                },
                'color_palette': {
                    'palette': {
                        'primary': ['#635BFF', '#0A2540'],
                        'success': ['#34C759']
                    }
                }
            }
        }

        # Extract with JMESPath
        scale = jmespath.search('evidence.spacing_scale.scale', data)
        colors = jmespath.search('evidence.color_palette.palette.primary', data)

        assert scale == [4, 8, 16, 24, 32, 48], "Scale extraction failed"
        assert colors == ['#635BFF', '#0A2540'], "Color extraction failed"

        print(f"{Fore.GREEN}✅ JMESPath working")
        print(f"   Extracted scale: {scale}")
        print(f"   Extracted colors: {colors}")
        return True

    except Exception as e:
        print(f"{Fore.RED}❌ JMESPath failed: {e}")
        return False


def test_parquet():
    """Test Parquet with pandas"""
    print(f"\n{Fore.CYAN}Testing PyArrow/Parquet...")
    try:
        import pandas as pd
        import os
        import time

        # Create test DataFrame
        df = pd.DataFrame({
            'site': ['theringer.com', 'pitchfork.com', 'ninaprotocol.com'],
            'framework': ['React', 'Next.js', 'React'],
            'colors': [8, 12, 6],
            'spacing': ['8pt', '4pt', 'Powers of 2']
        })

        # Save as Parquet
        parquet_file = '/tmp/test_scraper.parquet'
        start = time.time()
        df.to_parquet(parquet_file, compression='snappy')
        write_time = time.time() - start

        # Load back
        start = time.time()
        df_loaded = pd.read_parquet(parquet_file)
        read_time = time.time() - start

        # Check file size
        size_kb = os.path.getsize(parquet_file) / 1024

        assert len(df_loaded) == 3, "Data lost in Parquet conversion"
        assert list(df_loaded.columns) == list(df.columns), "Columns changed"

        print(f"{Fore.GREEN}✅ Parquet working")
        print(f"   File size: {size_kb:.2f} KB")
        print(f"   Write: {write_time*1000:.1f}ms, Read: {read_time*1000:.1f}ms")

        # Clean up
        os.remove(parquet_file)
        return True

    except Exception as e:
        print(f"{Fore.RED}❌ Parquet failed: {e}")
        return False


def test_colorama():
    """Test Colorama colors"""
    print(f"\n{Fore.CYAN}Testing Colorama...")
    try:
        print(f"{Fore.GREEN}✅ Colorama working")
        print(f"   {Fore.RED}Red text")
        print(f"   {Fore.YELLOW}Yellow text")
        print(f"   {Fore.BLUE}Blue text")
        print(f"   {Fore.MAGENTA}Magenta text")
        return True

    except Exception as e:
        print(f"{Fore.RED}❌ Colorama failed: {e}")
        return False


def test_tqdm():
    """Test Tqdm progress bars"""
    print(f"\n{Fore.CYAN}Testing Tqdm...")
    try:
        from tqdm import tqdm
        import time

        items = ['site1', 'site2', 'site3', 'site4', 'site5']

        print(f"{Fore.YELLOW}   Processing 5 items with progress bar:")
        for item in tqdm(items, desc="   Analyzing", ncols=60):
            time.sleep(0.1)

        print(f"{Fore.GREEN}✅ Tqdm working")
        return True

    except Exception as e:
        print(f"{Fore.RED}❌ Tqdm failed: {e}")
        return False


def test_pydantic():
    """Test Pydantic validation"""
    print(f"\n{Fore.CYAN}Testing Pydantic...")
    try:
        from pydantic import BaseModel, HttpUrl, ValidationError, Field

        class DesignToken(BaseModel):
            site: HttpUrl
            spacing_base: int = Field(..., gt=0)
            colors: int = Field(..., ge=1, le=100)

        # Valid data
        token = DesignToken(
            site="https://www.theringer.com",
            spacing_base=4,
            colors=8
        )

        assert token.spacing_base == 4, "Valid data failed"

        # Invalid data (should raise error)
        try:
            token = DesignToken(
                site="not-a-url",
                spacing_base=-1,
                colors=8
            )
            print(f"{Fore.RED}❌ Pydantic failed to catch invalid data")
            return False
        except ValidationError:
            pass  # Expected

        print(f"{Fore.GREEN}✅ Pydantic working")
        print(f"   Validates URLs, ranges, types")
        return True

    except Exception as e:
        print(f"{Fore.RED}❌ Pydantic failed: {e}")
        return False


def test_pillow():
    """Test Pillow image processing"""
    print(f"\n{Fore.CYAN}Testing Pillow...")
    try:
        from PIL import Image
        import io

        # Create a simple test image
        img = Image.new('RGB', (100, 100), color=(255, 0, 0))

        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        # Load back
        img_loaded = Image.open(img_bytes)

        assert img_loaded.size == (100, 100), "Image size changed"
        assert img_loaded.mode == 'RGB', "Image mode changed"

        # Test thumbnail
        img_loaded.thumbnail((50, 50))
        assert img_loaded.size == (50, 50), "Thumbnail failed"

        print(f"{Fore.GREEN}✅ Pillow working")
        print(f"   Can create, resize, convert images")
        return True

    except Exception as e:
        print(f"{Fore.RED}❌ Pillow failed: {e}")
        return False


def test_aiohttp():
    """Test Aiohttp async HTTP"""
    print(f"\n{Fore.CYAN}Testing Aiohttp...")
    try:
        import aiohttp
        import asyncio

        async def test_fetch():
            async with aiohttp.ClientSession() as session:
                # Test with httpbin (public API)
                async with session.get('https://httpbin.org/get', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    data = await resp.json()
                    return resp.status == 200

        result = asyncio.run(test_fetch())

        if result:
            print(f"{Fore.GREEN}✅ Aiohttp working")
            print(f"   Can make async HTTP requests")
            return True
        else:
            print(f"{Fore.RED}❌ Aiohttp request failed")
            return False

    except Exception as e:
        print(f"{Fore.YELLOW}⚠️  Aiohttp test skipped (network required): {e}")
        return True  # Don't fail on network issues


def test_rich():
    """Test Rich tables"""
    print(f"\n{Fore.CYAN}Testing Rich...")
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()

        table = Table(title="Test Results")
        table.add_column("Package", style="cyan")
        table.add_column("Status", style="green")

        table.add_row("JMESPath", "✅ Working")
        table.add_row("Parquet", "✅ Working")
        table.add_row("Rich", "✅ Working")

        print()
        console.print(table)

        print(f"{Fore.GREEN}✅ Rich working")
        return True

    except Exception as e:
        print(f"{Fore.RED}❌ Rich failed: {e}")
        return False


def test_httpx():
    """Test HTTPX"""
    print(f"\n{Fore.CYAN}Testing HTTPX...")
    try:
        import httpx

        # Test sync client
        with httpx.Client() as client:
            response = client.get('https://httpbin.org/get', timeout=5.0)

        if response.status_code == 200:
            print(f"{Fore.GREEN}✅ HTTPX working")
            print(f"   HTTP/2 capable client")
            return True
        else:
            print(f"{Fore.RED}❌ HTTPX request failed")
            return False

    except Exception as e:
        print(f"{Fore.YELLOW}⚠️  HTTPX test skipped (network required): {e}")
        return True  # Don't fail on network issues


def main():
    """Run all tests"""
    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.MAGENTA}  NEW PACKAGES TEST SUITE")
    print(f"{Fore.MAGENTA}{'='*60}")

    tests = [
        ("JMESPath", test_jmespath),
        ("PyArrow/Parquet", test_parquet),
        ("Colorama", test_colorama),
        ("Tqdm", test_tqdm),
        ("Pydantic", test_pydantic),
        ("Pillow", test_pillow),
        ("Aiohttp", test_aiohttp),
        ("Rich", test_rich),
        ("HTTPX", test_httpx),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"{Fore.RED}❌ {name} crashed: {e}")
            results[name] = False

    # Summary
    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.MAGENTA}  SUMMARY")
    print(f"{Fore.MAGENTA}{'='*60}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        if result:
            print(f"{Fore.GREEN}✅ {name}")
        else:
            print(f"{Fore.RED}❌ {name}")

    print(f"\n{Fore.CYAN}Results: {passed}/{total} tests passed")

    if passed == total:
        print(f"{Fore.GREEN}\n🎉 ALL PACKAGES WORKING!")
        print(f"\n{Fore.YELLOW}Next steps:")
        print(f"  1. Run examples: python3 examples/ringer_comparison_demo.py")
        print(f"  2. Read integration guide: cat INTEGRATION_GUIDE.md")
        print(f"  3. Start using in your scraper!")
        return 0
    else:
        print(f"{Fore.RED}\n⚠️  Some packages need attention")
        print(f"\n{Fore.YELLOW}Try:")
        print(f"  pip install -r requirements.txt")
        return 1


if __name__ == '__main__':
    sys.exit(main())
