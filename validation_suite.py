"""
Validation Suite - Prove DeepEvidenceEngine accuracy against ground truth.

Runs the engine against 5 known sites and calculates Precision/Recall/F1
for typography, color, spacing, and layout detection.

Usage:
    python validation_suite.py                      # all sites
    python validation_suite.py --url stripe.com     # single site
    python validation_suite.py --metric colors      # specific metric only
    python validation_suite.py --report report.json # save full results

Requirements:
    pip install colorama  # optional, for colored terminal output
"""

import asyncio
import json
import argparse
import math
import re
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deep_evidence_engine import DeepEvidenceEngine

GROUND_TRUTH_PATH = Path(__file__).parent / 'benchmarks' / 'ground_truth.json'

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    _COLOR = True
except ImportError:
    _COLOR = False

# ---------------------------------------------------------------------------
# Color/display helpers
# ---------------------------------------------------------------------------

def _green(s):  return f"{Fore.GREEN}{s}{Style.RESET_ALL}" if _COLOR else s
def _red(s):    return f"{Fore.RED}{s}{Style.RESET_ALL}" if _COLOR else s
def _yellow(s): return f"{Fore.YELLOW}{s}{Style.RESET_ALL}" if _COLOR else s
def _bold(s):   return f"{Style.BRIGHT}{s}{Style.RESET_ALL}" if _COLOR else s


def _grade(f1: float) -> str:
    if f1 >= 0.90: return _green('A')
    if f1 >= 0.75: return _green('B')
    if f1 >= 0.60: return _yellow('C')
    if f1 >= 0.45: return _red('D')
    return _red('F')


# ---------------------------------------------------------------------------
# Comparison utilities
# ---------------------------------------------------------------------------

def _normalize_hex(c: str) -> Optional[str]:
    c = c.strip().lower().lstrip('#')
    if len(c) == 3:
        c = ''.join(ch * 2 for ch in c)
    return f'#{c}' if len(c) == 6 else None


def _hex_to_rgb(c: str) -> Optional[Tuple[int,int,int]]:
    n = _normalize_hex(c)
    if not n:
        return None
    return tuple(int(n[i:i+2], 16) for i in (1, 3, 5))


def _color_distance(c1: str, c2: str) -> float:
    """Simple RGB Euclidean distance, normalized to 0-1."""
    r1 = _hex_to_rgb(c1)
    r2 = _hex_to_rgb(c2)
    if r1 is None or r2 is None:
        return 1.0
    dist = math.sqrt(sum((a - b)**2 for a, b in zip(r1, r2)))
    return dist / math.sqrt(3 * 255**2)


def _colors_match(c1: str, c2: str, tolerance_delta_e: float = 5.0) -> bool:
    """True if colors are perceptually close (within tolerance)."""
    return _color_distance(c1, c2) * 441 < tolerance_delta_e


def _font_family_match(extracted: str, expected: str) -> bool:
    """True if expected family name appears in extracted string (case-insensitive)."""
    if not extracted or not expected:
        return False
    return expected.lower() in extracted.lower() or extracted.lower() in expected.lower()


def _parse_px(value) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.match(r'([\d.]+)', value.strip())
        return float(m.group(1)) if m else None
    return None


def _sizes_overlap(extracted: List[float], expected: List[float], tolerance_pct: float) -> Tuple[int,int,int]:
    """
    Returns (true_positives, false_positives, false_negatives) for size sets.
    A match is within tolerance_pct of the expected value.
    """
    tp = 0
    matched_expected = set()
    for e_size in extracted:
        for i, x_size in enumerate(expected):
            if i in matched_expected:
                continue
            if x_size > 0 and abs(e_size - x_size) / x_size <= tolerance_pct:
                tp += 1
                matched_expected.add(i)
                break
    fp = len(extracted) - tp
    fn = len(expected) - tp
    return tp, max(0, fp), max(0, fn)


def _precision_recall_f1(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


# ---------------------------------------------------------------------------
# Per-metric validators
# ---------------------------------------------------------------------------

def validate_typography(evidence: dict, truth: dict, tol: dict) -> dict:
    typo = evidence.get('typography', {})
    t_truth = truth.get('typography', {})

    results = {}

    # Font family detection
    extracted_font = typo.get('primary_font', typo.get('font_families', [''])[0] if typo.get('font_families') else '')
    expected_font = t_truth.get('primary_font_family', '')
    font_match = _font_family_match(str(extracted_font), expected_font)
    results['font_family'] = {
        'match':    font_match,
        'extracted': str(extracted_font)[:60],
        'expected':  expected_font,
        'f1':        1.0 if font_match else 0.0,
    }

    # Font size coverage
    type_scale = typo.get('type_scale', {})
    if isinstance(type_scale, dict):
        raw_sizes = type_scale.get('sizes_px', type_scale.get('all_sizes', []))
    else:
        raw_sizes = typo.get('font_sizes', [])

    extracted_sizes = [_parse_px(s) for s in raw_sizes if _parse_px(s) is not None]
    expected_sizes  = [float(s) for s in t_truth.get('expected_sizes_px', [])]
    tol_pct = tol.get('font_size_pct', 0.10)

    if expected_sizes:
        tp, fp, fn = _sizes_overlap(extracted_sizes, expected_sizes, tol_pct)
        p, r, f1 = _precision_recall_f1(tp, fp, fn)
        results['font_sizes'] = {
            'precision': round(p, 3), 'recall': round(r, 3), 'f1': round(f1, 3),
            'tp': tp, 'fp': fp, 'fn': fn,
            'extracted_count': len(extracted_sizes),
            'expected_count':  len(expected_sizes),
        }
    else:
        results['font_sizes'] = {'f1': None, 'note': 'no expected sizes in ground truth'}

    # Scale ratio detection
    detected_ratio = None
    if isinstance(type_scale, dict):
        detected_ratio = type_scale.get('ratio')
    expected_ratio = t_truth.get('scale_ratio')
    if expected_ratio and detected_ratio:
        try:
            ratio_diff = abs(float(detected_ratio) - float(expected_ratio)) / float(expected_ratio)
            results['scale_ratio'] = {
                'match':     ratio_diff < 0.08,
                'extracted': round(float(detected_ratio), 3),
                'expected':  round(float(expected_ratio), 3),
                'f1':        1.0 if ratio_diff < 0.08 else max(0, 1 - ratio_diff * 5),
            }
        except (TypeError, ValueError):
            pass

    # Aggregate F1
    f1_scores = [v['f1'] for v in results.values() if isinstance(v.get('f1'), float)]
    results['_aggregate_f1'] = round(sum(f1_scores) / len(f1_scores), 3) if f1_scores else 0.0
    return results


def validate_colors(evidence: dict, truth: dict, tol: dict) -> dict:
    colors = evidence.get('colors', {})
    c_truth = truth.get('colors', {})
    delta_tol = tol.get('color_hex_delta_e', 5)

    results = {}
    all_palette_colors: List[str] = []

    palette = colors.get('palette', {})
    for group in ('primary', 'secondary', 'intentional'):
        for c in palette.get(group, []):
            norm = _normalize_hex(str(c))
            if norm:
                all_palette_colors.append(norm)

    tp = fp = fn = 0
    for label, expected_hex in c_truth.items():
        if not expected_hex.startswith('#'):
            continue
        matched = any(_colors_match(ec, expected_hex, delta_tol) for ec in all_palette_colors)
        if matched:
            tp += 1
        else:
            fn += 1
            results[f'missed_{label}'] = {'expected': expected_hex, 'nearest_extracted': _nearest_color(expected_hex, all_palette_colors)}

    fp = max(0, len(all_palette_colors) - tp)
    p, r, f1 = _precision_recall_f1(tp, fp, fn)
    results['palette'] = {
        'precision': round(p, 3), 'recall': round(r, 3), 'f1': round(f1, 3),
        'tp': tp, 'fp': fp, 'fn': fn,
        'extracted_count': len(all_palette_colors),
    }
    results['_aggregate_f1'] = round(f1, 3)
    return results


def validate_spacing(evidence: dict, truth: dict, tol: dict) -> dict:
    spacing = evidence.get('spacing_scale', {})
    s_truth = truth.get('spacing', {})

    results = {}
    tol_pct = tol.get('spacing_pct', 0.20)

    # Base unit
    extracted_base = _parse_px(spacing.get('base_unit', '0'))
    expected_base  = float(s_truth.get('base_unit_px', 0))
    if expected_base > 0 and extracted_base is not None:
        base_match = abs(extracted_base - expected_base) / expected_base <= tol_pct
        results['base_unit'] = {
            'match':     base_match,
            'extracted': extracted_base,
            'expected':  expected_base,
            'f1':        1.0 if base_match else 0.0,
        }

    # Scale values
    raw_scale = spacing.get('scale', spacing.get('values', []))
    extracted_px = [_parse_px(v) for v in raw_scale if _parse_px(v) is not None]
    expected_px  = [float(v) for v in s_truth.get('expected_scale_px', [])]

    if expected_px:
        tp, fp, fn = _sizes_overlap(extracted_px, expected_px, tol_pct)
        p, r, f1 = _precision_recall_f1(tp, fp, fn)
        results['scale_values'] = {
            'precision': round(p, 3), 'recall': round(r, 3), 'f1': round(f1, 3),
            'tp': tp, 'fp': fp, 'fn': fn,
        }

    f1_scores = [v['f1'] for v in results.values() if isinstance(v.get('f1'), float)]
    results['_aggregate_f1'] = round(sum(f1_scores) / len(f1_scores), 3) if f1_scores else 0.0
    return results


def validate_layout(evidence: dict, truth: dict, _tol: dict) -> dict:
    layout = evidence.get('layout', {})
    l_truth = truth.get('layout', {})

    results = {}

    # Page type
    extracted_type = (
        evidence.get('content_extraction', {}).get('page_type') or
        layout.get('page_type') or
        evidence.get('spatial_composition', {}).get('page_structure', {}).get('pattern_type', '')
    )
    expected_type = l_truth.get('page_type', '')
    if expected_type:
        match = expected_type.lower() in str(extracted_type).lower() or \
                str(extracted_type).lower() in expected_type.lower()
        results['page_type'] = {
            'match':     match,
            'extracted': str(extracted_type)[:60],
            'expected':  expected_type,
            'f1':        1.0 if match else 0.0,
        }

    f1_scores = [v['f1'] for v in results.values() if isinstance(v.get('f1'), float)]
    results['_aggregate_f1'] = round(sum(f1_scores) / len(f1_scores), 3) if f1_scores else 0.0
    return results


def _nearest_color(target: str, candidates: List[str]) -> Optional[str]:
    if not candidates:
        return None
    return min(candidates, key=lambda c: _color_distance(target, c))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class ValidationSuite:
    def __init__(self, ground_truth_path: Path = GROUND_TRUTH_PATH):
        with open(ground_truth_path) as f:
            data = json.load(f)
        self._meta    = data.get('_meta', {})
        self._truth   = {k: v for k, v in data.items() if not k.startswith('_')}
        self.results: Dict[str, dict] = {}

    def run_site(self, url: str, metric_filter: Optional[str] = None) -> dict:
        """Run engine against a single URL and validate against ground truth."""
        # Find matching ground truth key
        truth_key = next(
            (k for k in self._truth if k in url or url in k),
            None
        )
        truth = self._truth.get(truth_key, {}) if truth_key else {}
        tol   = self._meta.get('tolerance', {})

        print(f"\n{_bold('→ Analyzing:')} {url}")
        if not truth:
            print(_yellow(f"  ⚠ No ground truth for {url} — running without validation"))

        engine = DeepEvidenceEngine(url, analysis_mode='single')
        evidence = asyncio.run(engine.extract_all())

        if not truth:
            return {'url': url, 'note': 'no_ground_truth', 'evidence_keys': list(evidence.keys())}

        validators = {
            'typography': validate_typography,
            'colors':     validate_colors,
            'spacing':    validate_spacing,
            'layout':     validate_layout,
        }

        site_results = {'url': url, 'ground_truth_key': truth_key, 'metrics': {}}
        f1_scores = []

        for name, fn in validators.items():
            if metric_filter and name != metric_filter:
                continue
            r = fn(evidence, truth, tol)
            site_results['metrics'][name] = r
            agg = r.get('_aggregate_f1')
            if agg is not None:
                f1_scores.append(agg)

        site_results['overall_f1']       = round(sum(f1_scores) / len(f1_scores), 3) if f1_scores else None
        site_results['confidence_scores'] = {
            k: v.get('confidence', None)
            for k, v in evidence.items()
            if isinstance(v, dict) and 'confidence' in v
        }

        self._print_site_summary(url, site_results)
        return site_results

    def run_all(self, metric_filter: Optional[str] = None) -> dict:
        """Run all ground truth sites and aggregate results."""
        print(_bold(f"\n{'='*60}"))
        print(_bold("  Web Intelligence Scanner — Validation Suite"))
        print(_bold(f"{'='*60}"))

        all_results = {}
        for domain, truth in self._truth.items():
            url = f"https://{domain}"
            try:
                result = self.run_site(url, metric_filter)
                all_results[domain] = result
            except Exception as e:
                print(_red(f"  ✗ {domain} failed: {e}"))
                all_results[domain] = {'url': url, 'error': str(e)}

        self._print_aggregate_summary(all_results)
        return all_results

    def _print_site_summary(self, url: str, results: dict):
        metrics = results.get('metrics', {})
        overall = results.get('overall_f1')

        grade = _grade(overall) if overall is not None else '?'
        print(f"  Overall F1: {overall:.2%}" if overall is not None else "  Overall F1: N/A")

        for metric_name, metric_data in metrics.items():
            agg = metric_data.get('_aggregate_f1')
            if agg is not None:
                bar = '█' * int(agg * 20) + '░' * (20 - int(agg * 20))
                label = _green(f"{agg:.0%}") if agg >= 0.75 else (_yellow(f"{agg:.0%}") if agg >= 0.50 else _red(f"{agg:.0%}"))
                print(f"  {metric_name:<14} [{bar}] {label}")

    def _print_aggregate_summary(self, all_results: dict):
        print(f"\n{_bold('='*60)}")
        print(_bold("  Aggregate Results"))
        print(_bold('='*60))

        metric_f1s: Dict[str, List[float]] = {}
        overall_f1s = []

        for domain, result in all_results.items():
            if 'error' in result:
                print(f"  {domain:<25} {_red('ERROR')}: {result['error'][:40]}")
                continue

            overall = result.get('overall_f1')
            grade = _grade(overall) if overall is not None else '?'
            print(f"  {domain:<30} F1={overall:.2%}  {grade}" if overall is not None else f"  {domain:<30} N/A")

            if overall is not None:
                overall_f1s.append(overall)

            for metric, data in result.get('metrics', {}).items():
                agg = data.get('_aggregate_f1')
                if agg is not None:
                    metric_f1s.setdefault(metric, []).append(agg)

        if overall_f1s:
            avg = sum(overall_f1s) / len(overall_f1s)
            print(f"\n  {_bold('Average overall F1:')} {avg:.2%}  {_grade(avg)}")

        print(f"\n  {_bold('Per-metric averages:')}")
        for metric, scores in metric_f1s.items():
            avg = sum(scores) / len(scores)
            print(f"    {metric:<14} {avg:.2%}  {_grade(avg)}")

        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Validate DeepEvidenceEngine against ground truth sites'
    )
    parser.add_argument('--url',    help='Single URL to validate (must match a ground truth key)')
    parser.add_argument('--metric', choices=['typography', 'colors', 'spacing', 'layout'],
                        help='Validate only this metric')
    parser.add_argument('--report', help='Save full results JSON to this path')
    args = parser.parse_args()

    suite = ValidationSuite()

    if args.url:
        results = suite.run_site(args.url, metric_filter=args.metric)
    else:
        results = suite.run_all(metric_filter=args.metric)

    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Report saved to {path}")
