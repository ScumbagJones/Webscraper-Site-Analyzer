"""
Nina Protocol API Analyzer
Demonstrates using JMESPath, Parquet, and image analysis for music sites
"""

import jmespath
import pandas as pd
from PIL import Image
from tqdm import tqdm
from colorama import Fore, Style, init
import requests
from io import BytesIO
from collections import Counter
import colorsys

# Initialize colorama
init(autoreset=True)


class NinaProtocolAnalyzer:
    """
    Analyze Nina Protocol music releases with enhanced data extraction
    """

    def __init__(self):
        self.base_url = "https://api.ninaprotocol.com"  # Example
        self.releases_data = []

    def query_api_releases(self, api_response: dict) -> list:
        """
        Extract release data using JMESPath instead of nested loops

        Example API response:
        {
          "data": {
            "releases": [
              {
                "title": "Album 1",
                "artist": { "name": "Artist 1", "id": 123 },
                "coverUrl": "https://...",
                "releaseDate": "2024-01-01"
              }
            ]
          }
        }
        """
        # Instead of this mess:
        # releases = []
        # for release in api_response['data']['releases']:
        #     releases.append({
        #         'title': release['title'],
        #         'artist': release['artist']['name'],
        #         'cover': release['coverUrl']
        #     })

        # Use JMESPath:
        query = """
        data.releases[*].{
            title: title,
            artist: artist.name,
            artist_id: artist.id,
            cover_url: coverUrl,
            release_date: releaseDate,
            genre: metadata.genre,
            price: price.amount
        }
        """

        releases = jmespath.search(query, api_response)
        print(f"{Fore.GREEN}✅ Extracted {len(releases)} releases")
        return releases

    def extract_dominant_colors(self, image_url: str, num_colors: int = 5) -> list:
        """
        Extract dominant colors from album artwork
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=10)
            img = Image.open(BytesIO(response.content))

            # Resize for faster processing
            img.thumbnail((150, 150))

            # Convert to RGB
            img = img.convert('RGB')

            # Get all pixels
            pixels = list(img.getdata())

            # Count colors
            color_counts = Counter(pixels)

            # Get top colors
            dominant = color_counts.most_common(num_colors)

            # Convert to hex
            colors = []
            for rgb, count in dominant:
                hex_color = '#{:02x}{:02x}{:02x}'.format(*rgb)

                # Calculate brightness
                r, g, b = rgb
                brightness = (r * 299 + g * 587 + b * 114) / 1000

                colors.append({
                    'hex': hex_color,
                    'rgb': rgb,
                    'count': count,
                    'brightness': brightness,
                    'is_dark': brightness < 128
                })

            return colors

        except Exception as e:
            print(f"{Fore.RED}❌ Error analyzing image: {e}")
            return []

    def analyze_album_art_batch(self, releases: list) -> pd.DataFrame:
        """
        Analyze album artwork colors for multiple releases
        """
        results = []

        for release in tqdm(releases, desc=f"{Fore.CYAN}Analyzing album art"):
            if not release.get('cover_url'):
                continue

            colors = self.extract_dominant_colors(release['cover_url'])

            if colors:
                results.append({
                    'title': release['title'],
                    'artist': release['artist'],
                    'primary_color': colors[0]['hex'],
                    'is_dark_cover': colors[0]['is_dark'],
                    'color_palette': [c['hex'] for c in colors[:5]],
                    'release_date': release.get('release_date')
                })

        df = pd.DataFrame(results)
        print(f"{Fore.GREEN}✅ Analyzed {len(df)} album covers")
        return df

    def save_to_parquet(self, df: pd.DataFrame, filename: str):
        """
        Save DataFrame to Parquet (90% smaller than CSV, 10x faster)
        """
        # Save as Parquet
        parquet_file = f"{filename}.parquet"
        df.to_parquet(parquet_file, compression='snappy')

        # Compare to CSV
        csv_file = f"{filename}.csv"
        df.to_csv(csv_file, index=False)

        import os
        parquet_size = os.path.getsize(parquet_file) / 1024  # KB
        csv_size = os.path.getsize(csv_file) / 1024  # KB

        print(f"\n{Fore.CYAN}File Size Comparison:")
        print(f"  CSV:     {csv_size:.2f} KB")
        print(f"  Parquet: {parquet_size:.2f} KB")
        print(f"  {Fore.GREEN}Savings: {((csv_size - parquet_size) / csv_size * 100):.1f}%")

        # Clean up CSV
        os.remove(csv_file)

    def load_from_parquet(self, filename: str) -> pd.DataFrame:
        """
        Load data from Parquet (10x faster than CSV)
        """
        import time

        start = time.time()
        df = pd.read_parquet(f"{filename}.parquet")
        parquet_time = time.time() - start

        print(f"{Fore.GREEN}✅ Loaded {len(df)} rows in {parquet_time:.3f}s")
        return df


# Example Usage
def demo_nina_protocol_analysis():
    """
    Demonstrate Nina Protocol analysis workflow
    """
    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.MAGENTA}  NINA PROTOCOL ANALYZER DEMO")
    print(f"{Fore.MAGENTA}{'='*60}\n")

    analyzer = NinaProtocolAnalyzer()

    # Simulated API response
    mock_api_response = {
        "data": {
            "releases": [
                {
                    "title": "Digital Dreams",
                    "artist": {"name": "Synthwave Artist", "id": 123},
                    "coverUrl": "https://picsum.photos/400/400?random=1",
                    "releaseDate": "2024-01-15",
                    "metadata": {"genre": "Electronic"},
                    "price": {"amount": 10.00}
                },
                {
                    "title": "Midnight Sessions",
                    "artist": {"name": "Jazz Collective", "id": 456},
                    "coverUrl": "https://picsum.photos/400/400?random=2",
                    "releaseDate": "2024-02-01",
                    "metadata": {"genre": "Jazz"},
                    "price": {"amount": 15.00}
                },
                {
                    "title": "Urban Beats",
                    "artist": {"name": "Hip Hop Producer", "id": 789},
                    "coverUrl": "https://picsum.photos/400/400?random=3",
                    "releaseDate": "2024-03-10",
                    "metadata": {"genre": "Hip Hop"},
                    "price": {"amount": 12.00}
                }
            ]
        }
    }

    # Step 1: Extract data with JMESPath
    print(f"{Fore.CYAN}Step 1: Extracting release data with JMESPath...")
    releases = analyzer.query_api_releases(mock_api_response)

    # Step 2: Analyze album artwork
    print(f"\n{Fore.CYAN}Step 2: Analyzing album artwork colors...")
    df = analyzer.analyze_album_art_batch(releases)

    # Step 3: Display results
    print(f"\n{Fore.CYAN}Step 3: Release Summary:")
    for idx, row in df.iterrows():
        print(f"\n  {Fore.YELLOW}{row['title']} - {row['artist']}")
        print(f"    Primary Color: {row['primary_color']}")
        print(f"    Cover Style: {'Dark' if row['is_dark_cover'] else 'Light'}")
        print(f"    Palette: {', '.join(row['color_palette'])}")

    # Step 4: Save to Parquet
    print(f"\n{Fore.CYAN}Step 4: Saving to Parquet...")
    analyzer.save_to_parquet(df, 'nina_releases')

    # Step 5: Load from Parquet
    print(f"\n{Fore.CYAN}Step 5: Loading from Parquet...")
    loaded_df = analyzer.load_from_parquet('nina_releases')

    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"{Fore.GREEN}  ✅ ANALYSIS COMPLETE")
    print(f"{Fore.GREEN}{'='*60}\n")


if __name__ == '__main__':
    demo_nina_protocol_analysis()
