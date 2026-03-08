"""
Design System Batch Analyzer
Analyze multiple music sites in parallel and extract design tokens efficiently
"""

import asyncio
import aiohttp
import jmespath
import pandas as pd
from tqdm import tqdm
from colorama import Fore, Style, init
from rich.console import Console
from rich.table import Table
from pathlib import Path
import time

# Initialize
init(autoreset=True)
console = Console()


class DesignSystemBatchAnalyzer:
    """
    Analyze design systems across multiple music sites
    Uses async HTTP for parallel scraping
    """

    def __init__(self):
        self.results = []
        self.output_dir = Path('data/design_tokens')
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def analyze_site(self, session: aiohttp.ClientSession, site_url: str) -> dict:
        """
        Analyze a single site's design system
        """
        try:
            # Make request to your scraper API
            async with session.post(
                'http://localhost:8080/api/deep-scan',
                json={'url': site_url},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    return {'site': site_url, 'status': 'failed', 'error': f'HTTP {response.status}'}

                data = await response.json()

                # Extract design tokens with JMESPath
                tokens = self.extract_design_tokens(data, site_url)
                return tokens

        except asyncio.TimeoutError:
            return {'site': site_url, 'status': 'timeout'}
        except Exception as e:
            return {'site': site_url, 'status': 'error', 'error': str(e)}

    def extract_design_tokens(self, scraper_data: dict, site_url: str) -> dict:
        """
        Extract design tokens using JMESPath queries
        """
        # JMESPath queries for common design patterns
        queries = {
            # Colors
            'primary_colors': 'evidence.color_palette.palette.primary[*].color',
            'success_colors': 'evidence.color_palette.palette.success[*].color',
            'error_colors': 'evidence.color_palette.palette.error[*].color',

            # Spacing
            'spacing_scale': 'evidence.spacing_scale.scale',
            'spacing_base': 'evidence.spacing_scale.base_unit',
            'spacing_pattern': 'evidence.spacing_scale.pattern',

            # Typography
            'font_families': 'evidence.typography.fonts[*].family',
            'font_sizes': 'evidence.typography.sizes[*]',

            # Breakpoints
            'breakpoints': 'evidence.responsive_breakpoints.breakpoints',
            'breakpoint_framework': 'evidence.responsive_breakpoints.framework',

            # Shadows
            'shadow_levels': 'evidence.shadow_system.levels[*]',

            # Border Radius
            'radius_scale': 'evidence.border_radius_scale.scale',

            # Framework
            'detected_framework': 'evidence.frameworks[0]',

            # Visual Hierarchy
            'hero_text': 'evidence.visual_hierarchy.hero_section.text',
            'primary_cta': 'evidence.visual_hierarchy.primary_cta.text',
        }

        tokens = {'site': site_url, 'status': 'success'}

        for key, query in queries.items():
            try:
                result = jmespath.search(query, scraper_data)
                tokens[key] = result
            except Exception:
                tokens[key] = None

        return tokens

    async def analyze_batch(self, site_urls: list) -> pd.DataFrame:
        """
        Analyze multiple sites in parallel
        """
        print(f"\n{Fore.CYAN}Analyzing {len(site_urls)} sites in parallel...")

        async with aiohttp.ClientSession() as session:
            # Create tasks for all sites
            tasks = [
                self.analyze_site(session, url)
                for url in site_urls
            ]

            # Run with progress bar
            results = []
            for coro in tqdm(
                asyncio.as_completed(tasks),
                total=len(tasks),
                desc=f"{Fore.CYAN}Scraping sites"
            ):
                result = await coro
                results.append(result)

        # Convert to DataFrame
        df = pd.DataFrame(results)
        print(f"{Fore.GREEN}✅ Completed {len(df)} site analyses")

        return df

    def save_tokens_parquet(self, df: pd.DataFrame, category: str):
        """
        Save design tokens to Parquet files organized by category
        """
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f'{category}_tokens_{timestamp}.parquet'

        df.to_parquet(filename, compression='snappy')
        print(f"{Fore.GREEN}✅ Saved to {filename}")

        return filename

    def compare_design_systems(self, df: pd.DataFrame):
        """
        Generate comparison table using Rich
        """
        table = Table(title="Design System Comparison")

        table.add_column("Site", style="cyan", no_wrap=True)
        table.add_column("Framework", style="magenta")
        table.add_column("Spacing", style="green")
        table.add_column("Colors", style="yellow")
        table.add_column("Breakpoints", style="blue")

        for _, row in df.iterrows():
            # Extract site name
            site_name = row['site'].replace('https://', '').split('/')[0]

            # Format data
            framework = row.get('detected_framework', 'Unknown')
            spacing = row.get('spacing_pattern', 'N/A')
            colors = len(row.get('primary_colors', [])) if row.get('primary_colors') else 0
            breakpoints = len(row.get('breakpoints', [])) if row.get('breakpoints') else 0

            table.add_row(
                site_name,
                str(framework),
                str(spacing),
                f"{colors} colors",
                f"{breakpoints} breakpoints"
            )

        console.print("\n")
        console.print(table)

    def generate_token_report(self, df: pd.DataFrame) -> str:
        """
        Generate markdown report of design tokens
        """
        report = "# Design System Analysis Report\n\n"
        report += f"**Analyzed**: {len(df)} sites\n"
        report += f"**Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n"

        report += "## Summary\n\n"

        for _, row in df.iterrows():
            site = row['site'].replace('https://', '').split('/')[0]
            report += f"### {site}\n\n"

            if row['status'] != 'success':
                report += f"⚠️ Status: {row['status']}\n\n"
                continue

            # Framework
            if row.get('detected_framework'):
                report += f"**Framework**: {row['detected_framework']}\n\n"

            # Spacing
            if row.get('spacing_pattern'):
                report += f"**Spacing Pattern**: {row['spacing_pattern']}\n"
                if row.get('spacing_base'):
                    report += f"  - Base unit: {row['spacing_base']}\n"
                if row.get('spacing_scale'):
                    report += f"  - Scale: {row['spacing_scale']}\n"
                report += "\n"

            # Colors
            if row.get('primary_colors'):
                report += f"**Primary Colors**: {', '.join(row['primary_colors'][:5])}\n\n"

            # Typography
            if row.get('font_families'):
                report += f"**Fonts**: {', '.join(row['font_families'][:3])}\n\n"

            # Breakpoints
            if row.get('breakpoints'):
                report += f"**Breakpoints**: {row['breakpoints']}\n\n"

            report += "---\n\n"

        return report


# Example Usage
async def demo_batch_analysis():
    """
    Demonstrate batch design system analysis
    """
    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.MAGENTA}  DESIGN SYSTEM BATCH ANALYZER")
    print(f"{Fore.MAGENTA}{'='*60}\n")

    analyzer = DesignSystemBatchAnalyzer()

    # Music sites to analyze
    sites = [
        'https://www.ninaprotocol.com',
        'https://pitchfork.com',
        'https://www.theringer.com',
        'https://www.vogue.com',
        'https://www.complex.com'
    ]

    print(f"{Fore.CYAN}Target sites:")
    for site in sites:
        print(f"  • {site}")

    # Analyze all sites in parallel
    print(f"\n{Fore.YELLOW}⚡ Starting parallel analysis...")
    start_time = time.time()

    df = await analyzer.analyze_batch(sites)

    elapsed = time.time() - start_time
    print(f"\n{Fore.GREEN}✅ Completed in {elapsed:.2f}s")
    print(f"{Fore.CYAN}Average: {elapsed/len(sites):.2f}s per site")

    # Save to Parquet
    print(f"\n{Fore.CYAN}Saving results to Parquet...")
    filename = analyzer.save_tokens_parquet(df, 'music_sites')

    # Display comparison table
    print(f"\n{Fore.CYAN}Generating comparison table...")
    analyzer.compare_design_systems(df)

    # Generate markdown report
    print(f"\n{Fore.CYAN}Generating markdown report...")
    report = analyzer.generate_token_report(df)
    report_file = analyzer.output_dir / 'design_tokens_report.md'
    report_file.write_text(report)
    print(f"{Fore.GREEN}✅ Report saved to {report_file}")

    # Load and verify Parquet
    print(f"\n{Fore.CYAN}Verifying Parquet file...")
    loaded_df = pd.read_parquet(filename)
    print(f"{Fore.GREEN}✅ Loaded {len(loaded_df)} rows from Parquet")

    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"{Fore.GREEN}  ✅ BATCH ANALYSIS COMPLETE")
    print(f"{Fore.GREEN}{'='*60}\n")


def demo_sequential_comparison():
    """
    Compare sequential vs parallel scraping performance
    """
    import requests

    sites = [
        'https://example.com',
        'https://example.org',
        'https://example.net'
    ]

    # Sequential (slow)
    print(f"\n{Fore.YELLOW}Sequential scraping (requests):")
    start = time.time()
    for url in sites:
        try:
            requests.get(url, timeout=5)
        except Exception:
            pass
    sequential_time = time.time() - start
    print(f"  Time: {sequential_time:.2f}s")

    # Parallel (fast)
    print(f"\n{Fore.YELLOW}Parallel scraping (aiohttp):")
    async def parallel_fetch():
        async with aiohttp.ClientSession() as session:
            tasks = [session.get(url) for url in sites]
            await asyncio.gather(*tasks, return_exceptions=True)

    start = time.time()
    asyncio.run(parallel_fetch())
    parallel_time = time.time() - start
    print(f"  Time: {parallel_time:.2f}s")

    speedup = sequential_time / parallel_time
    print(f"\n{Fore.GREEN}Speedup: {speedup:.1f}x faster!")


if __name__ == '__main__':
    # Run batch analysis
    asyncio.run(demo_batch_analysis())

    # Uncomment to see sequential vs parallel comparison
    # demo_sequential_comparison()
