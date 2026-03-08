"""
Axe-core Contrast Extractor

Injects axe-core into the live page and runs WCAG colour-contrast rules only.
Returns per-element violations with impact level, the element's CSS selector,
the actual foreground/background RGBA pair, and the measured contrast ratio.

Why not page.add_script_tag(url=CDN)?  Content-Security-Policy on many sites
blocks external script sources.  Instead we inject axe's minified source via
Playwright's add_init_script(), which is delivered via CDP before the page's
own CSP can apply — so it works on any site regardless of CSP headers.

Requires: website-understanding-sdk/node_modules/axe-core/axe.min.js
          (installed automatically when the project runs npm install)

Evidence key: 'contrast_a11y'
"""

import json
import logging
from pathlib import Path
from typing import Dict

from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)

# Path to the locally installed axe-core bundle
_AXE_PATH = (
    Path(__file__).parent.parent
    / "website-understanding-sdk"
    / "node_modules"
    / "axe-core"
    / "axe.min.js"
)

# axe rules to run — contrast only, nothing else
_CONTRAST_RULES = ["color-contrast", "color-contrast-enhanced"]


class AxeContrastExtractor(BaseExtractor):
    name = "contrast_a11y"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Axe-core: injecting for contrast check...")

        if not _AXE_PATH.exists():
            return self._unavailable(
                f"axe-core not found at {_AXE_PATH}. "
                "Run: npm install axe-core --prefix website-understanding-sdk"
            )

        # Inject axe source directly into the current page context.
        # NOTE: add_init_script() only fires on FUTURE navigations, but the page
        # is already loaded when this extractor runs.  So we read the source and
        # evaluate it directly.
        try:
            axe_source = _AXE_PATH.read_text(encoding="utf-8")
        except Exception as e:
            return self._unavailable(f"Could not read axe source: {e}")

        try:
            await ctx.page.evaluate(axe_source)
        except Exception as e:
            return self._unavailable(f"axe inject failed: {e}")

        # axe.run() must be called after DOMContentLoaded
        try:
            raw = await ctx.page.evaluate(
                """() => {
                    if (typeof axe === 'undefined') {
                        return { error: 'axe not loaded' };
                    }
                    return axe.run(document, {
                        runOnly: { type: 'rule', values: ['color-contrast', 'color-contrast-enhanced'] },
                        resultTypes: ['violations', 'passes'],
                        elementRef: false
                    });
                }"""
            )
        except Exception as e:
            return self._unavailable(f"axe.run() failed: {e}")

        if not raw or raw.get("error"):
            return self._unavailable(raw.get("error", "axe returned no data"))

        violations = raw.get("violations", [])
        passes     = raw.get("passes", [])

        # Flatten violations into per-node records
        items = []
        for rule in violations:
            rule_id = rule.get("id", "")
            impact  = rule.get("impact", "unknown")  # critical | serious | moderate | minor
            for node in rule.get("nodes", []):
                # axe packs the actual contrast data into node.any[].data
                ratio = None
                fg = bg = None
                for check in node.get("any", []) + node.get("all", []):
                    data = check.get("data") or {}
                    if isinstance(data, dict):
                        ratio = data.get("contrastRatio") or ratio
                        fg    = data.get("fgColor")  or fg
                        bg    = data.get("bgColor")  or bg

                items.append({
                    "rule":           rule_id,
                    "impact":         impact,
                    "selector":       " > ".join(node.get("target", [])),
                    "html_snippet":   node.get("html", "")[:200],
                    "contrast_ratio": round(ratio, 2) if ratio else None,
                    "fg_color":       fg,
                    "bg_color":       bg,
                    "fix_summary":    node.get("failureSummary", "")[:200],
                })

        # Severity breakdown
        critical = sum(1 for i in items if i["impact"] == "critical")
        serious  = sum(1 for i in items if i["impact"] == "serious")
        moderate = sum(1 for i in items if i["impact"] == "moderate")
        minor    = sum(1 for i in items if i["impact"] == "minor")

        total_violations = len(items)
        total_passes     = sum(len(r.get("nodes", [])) for r in passes)

        # Score: 100 minus weighted penalty (critical costs most)
        penalty = (critical * 15) + (serious * 8) + (moderate * 3) + (minor * 1)
        score   = max(0, 100 - penalty)

        # Confidence: higher when we have real pass/fail data
        confidence = 90 if (total_violations + total_passes) > 0 else 50

        if total_violations == 0:
            pattern = f"✓ No contrast violations — {total_passes} elements pass WCAG AA"
        else:
            pattern = (
                f"{total_violations} contrast violations: "
                f"{critical} critical, {serious} serious, "
                f"{moderate} moderate, {minor} minor"
            )

        return {
            "pattern":    pattern,
            "confidence": confidence,
            "score":      score,
            "details": {
                "violations":       items,
                "total_violations": total_violations,
                "total_passes":     total_passes,
                "severity": {
                    "critical": critical,
                    "serious":  serious,
                    "moderate": moderate,
                    "minor":    minor,
                },
                "wcag_level": "AA",
                "rules_tested": _CONTRAST_RULES,
            },
        }

    @staticmethod
    def _unavailable(reason: str) -> Dict:
        return {
            "pattern":    f"Contrast check unavailable: {reason}",
            "confidence": 0,
            "details":    {"violations": [], "total_violations": 0},
        }
