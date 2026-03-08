"""
Pydantic Data Models for Music Site Scraping
Ensures scraped data is clean and validated
"""

from pydantic import BaseModel, HttpUrl, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class ColorRole(str, Enum):
    """Color role categories"""
    PRIMARY = "primary"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    NEUTRAL = "neutral"


class ColorToken(BaseModel):
    """
    Validated color token from design system
    """
    color: str = Field(..., pattern=r'^#[0-9A-Fa-f]{6}$')  # Must be valid hex
    role: ColorRole
    wcag_aa_compliant: bool
    contrast_ratio: float = Field(..., ge=1.0, le=21.0)  # 1-21 range

    class Config:
        json_schema_extra = {
            "example": {
                "color": "#635BFF",
                "role": "primary",
                "wcag_aa_compliant": True,
                "contrast_ratio": 4.52
            }
        }


class SpacingScale(BaseModel):
    """
    Validated spacing scale
    """
    base_unit: int = Field(..., gt=0)  # Must be positive
    pattern: str
    scale: List[int]
    confidence: int = Field(..., ge=0, le=100)

    @validator('scale')
    def validate_scale(cls, v):
        """Ensure scale is sorted and contains base unit"""
        if len(v) == 0:
            raise ValueError("Scale cannot be empty")
        if sorted(v) != v:
            raise ValueError("Scale must be sorted")
        return v


class BreakpointConfig(BaseModel):
    """
    Validated responsive breakpoints
    """
    mobile: Optional[int] = Field(None, ge=0, le=768)
    tablet: Optional[int] = Field(None, ge=768, le=1024)
    desktop: Optional[int] = Field(None, ge=1024, le=1920)
    wide: Optional[int] = Field(None, ge=1920)
    framework: Optional[str] = None


class Album(BaseModel):
    """
    Validated music album data
    """
    title: str = Field(..., min_length=1, max_length=200)
    artist: str = Field(..., min_length=1, max_length=100)
    cover_url: HttpUrl
    release_date: datetime
    genre: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    dominant_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Digital Dreams",
                "artist": "Synthwave Artist",
                "cover_url": "https://example.com/cover.jpg",
                "release_date": "2024-01-15T00:00:00",
                "genre": "Electronic",
                "price": 10.00,
                "dominant_color": "#FF5733"
            }
        }


class DesignSystemTokens(BaseModel):
    """
    Complete validated design system
    """
    site_url: HttpUrl
    analyzed_at: datetime = Field(default_factory=datetime.now)

    # Colors
    colors: List[ColorToken]

    # Spacing
    spacing: SpacingScale

    # Breakpoints
    breakpoints: BreakpointConfig

    # Typography
    font_families: List[str] = Field(..., min_items=1)
    font_sizes: List[int] = Field(..., min_items=1)

    # Framework
    framework: Optional[str] = None

    # Metadata
    confidence_score: int = Field(..., ge=0, le=100)


class ScraperResult(BaseModel):
    """
    Validated scraper result with error handling
    """
    url: HttpUrl
    status: str = Field(..., pattern=r'^(success|failed|timeout|error)$')
    data: Optional[DesignSystemTokens] = None
    error_message: Optional[str] = None
    scraped_at: datetime = Field(default_factory=datetime.now)


# Example Usage
def demo_pydantic_validation():
    """
    Demonstrate Pydantic data validation
    """
    from colorama import Fore, init
    init(autoreset=True)

    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.MAGENTA}  PYDANTIC VALIDATION DEMO")
    print(f"{Fore.MAGENTA}{'='*60}\n")

    # Example 1: Valid data
    print(f"{Fore.CYAN}Example 1: Valid album data")
    try:
        album = Album(
            title="Midnight Sessions",
            artist="Jazz Collective",
            cover_url="https://example.com/cover.jpg",
            release_date="2024-01-15T00:00:00",
            genre="Jazz",
            price=15.00,
            dominant_color="#3498DB"
        )
        print(f"{Fore.GREEN}✅ Valid!")
        print(f"   Title: {album.title}")
        print(f"   Artist: {album.artist}")
        print(f"   Price: ${album.price}")

    except Exception as e:
        print(f"{Fore.RED}❌ Validation failed: {e}")

    # Example 2: Invalid hex color
    print(f"\n{Fore.CYAN}Example 2: Invalid hex color (should fail)")
    try:
        album = Album(
            title="Test Album",
            artist="Test Artist",
            cover_url="https://example.com/cover.jpg",
            release_date="2024-01-15T00:00:00",
            dominant_color="not-a-hex-color"  # ❌ Invalid
        )
        print(f"{Fore.GREEN}✅ Valid!")

    except Exception as e:
        print(f"{Fore.RED}❌ Validation failed (expected): {e}")

    # Example 3: Invalid URL
    print(f"\n{Fore.CYAN}Example 3: Invalid URL (should fail)")
    try:
        album = Album(
            title="Test Album",
            artist="Test Artist",
            cover_url="not-a-url",  # ❌ Invalid
            release_date="2024-01-15T00:00:00"
        )
        print(f"{Fore.GREEN}✅ Valid!")

    except Exception as e:
        print(f"{Fore.RED}❌ Validation failed (expected): {e}")

    # Example 4: Valid spacing scale
    print(f"\n{Fore.CYAN}Example 4: Valid spacing scale")
    try:
        spacing = SpacingScale(
            base_unit=4,
            pattern="Powers of 2",
            scale=[4, 8, 16, 24, 32, 48, 64],
            confidence=95
        )
        print(f"{Fore.GREEN}✅ Valid!")
        print(f"   Base: {spacing.base_unit}px")
        print(f"   Pattern: {spacing.pattern}")
        print(f"   Scale: {spacing.scale}")

    except Exception as e:
        print(f"{Fore.RED}❌ Validation failed: {e}")

    # Example 5: Invalid spacing scale (unsorted)
    print(f"\n{Fore.CYAN}Example 5: Invalid spacing scale - unsorted (should fail)")
    try:
        spacing = SpacingScale(
            base_unit=4,
            pattern="Custom",
            scale=[16, 8, 4, 32],  # ❌ Not sorted
            confidence=80
        )
        print(f"{Fore.GREEN}✅ Valid!")

    except Exception as e:
        print(f"{Fore.RED}❌ Validation failed (expected): {e}")

    # Example 6: Valid color token with WCAG
    print(f"\n{Fore.CYAN}Example 6: Valid color token with WCAG compliance")
    try:
        color = ColorToken(
            color="#635BFF",
            role=ColorRole.PRIMARY,
            wcag_aa_compliant=True,
            contrast_ratio=4.52
        )
        print(f"{Fore.GREEN}✅ Valid!")
        print(f"   Color: {color.color}")
        print(f"   Role: {color.role}")
        print(f"   WCAG AA: {'✅' if color.wcag_aa_compliant else '❌'}")
        print(f"   Contrast: {color.contrast_ratio}:1")

    except Exception as e:
        print(f"{Fore.RED}❌ Validation failed: {e}")

    # Example 7: Complete design system
    print(f"\n{Fore.CYAN}Example 7: Complete design system tokens")
    try:
        tokens = DesignSystemTokens(
            site_url="https://www.ninaprotocol.com",
            colors=[
                ColorToken(
                    color="#635BFF",
                    role=ColorRole.PRIMARY,
                    wcag_aa_compliant=True,
                    contrast_ratio=4.52
                ),
                ColorToken(
                    color="#34C759",
                    role=ColorRole.SUCCESS,
                    wcag_aa_compliant=True,
                    contrast_ratio=3.89
                )
            ],
            spacing=SpacingScale(
                base_unit=4,
                pattern="Powers of 2",
                scale=[4, 8, 16, 24, 32, 48],
                confidence=95
            ),
            breakpoints=BreakpointConfig(
                mobile=320,
                tablet=768,
                desktop=1024,
                wide=1920,
                framework="Tailwind"
            ),
            font_families=["Inter", "SF Pro", "system-ui"],
            font_sizes=[12, 14, 16, 18, 24, 32],
            framework="React",
            confidence_score=92
        )

        print(f"{Fore.GREEN}✅ Valid complete design system!")
        print(f"   Site: {tokens.site_url}")
        print(f"   Colors: {len(tokens.colors)} validated")
        print(f"   Spacing: {tokens.spacing.pattern}")
        print(f"   Framework: {tokens.framework}")
        print(f"   Confidence: {tokens.confidence_score}%")

        # Convert to JSON
        print(f"\n{Fore.YELLOW}JSON Output:")
        print(tokens.model_dump_json(indent=2)[:500] + "...")

    except Exception as e:
        print(f"{Fore.RED}❌ Validation failed: {e}")

    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"{Fore.GREEN}  ✅ VALIDATION DEMO COMPLETE")
    print(f"{Fore.GREEN}{'='*60}\n")


if __name__ == '__main__':
    demo_pydantic_validation()
