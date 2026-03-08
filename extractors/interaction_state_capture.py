"""
Interaction State Capture — Physical hover/focus state extraction via Playwright.

Uses Playwright's native .hover() and .focus() to trigger real CSS :hover and :focus
pseudo-classes, then reads computed styles to extract state deltas.

This solves the fundamental limitation of dispatchEvent('mouseenter') which fires
JS event listeners but does NOT trigger CSS :hover pseudo-class styling.

Proven on: Stripe.com CTAs (resting → hover → focus), Pigeons & Planes dropdown items.
"""

import logging
from typing import Dict, List, Optional, Tuple
from patchright.async_api import Page

logger = logging.getLogger(__name__)

# Properties that commonly change on hover/focus/active
STATE_PROPERTIES = [
    'backgroundColor', 'color', 'borderColor', 'boxShadow',
    'outline', 'outlineColor', 'outlineWidth', 'outlineOffset',
    'transform', 'opacity', 'textDecoration', 'borderRadius',
]

# Max elements to hover per selector type (keeps scan time reasonable)
MAX_SAMPLES_PER_TYPE = 5

# Max total elements to hover across all types
MAX_TOTAL_HOVERS = 25


async def capture_interaction_states(page: Page) -> Dict:
    """
    Physically hover and focus interactive elements to capture real CSS state deltas.

    Returns:
        {
            'hover_deltas': [...],      # List of hover state changes
            'focus_deltas': [...],      # List of focus state changes
            'hover_colors': {...},      # Hover-specific color roles
            'patterns': [...],          # Detected hover patterns (e.g., "darken 20%")
            'elements_tested': int,
            'states_detected': int,
        }
    """
    logger.info("Capturing interaction states via Playwright hover/focus...")

    # Step 1: Gather interactive elements with resting styles
    resting_elements = await page.evaluate('''() => {
        const results = [];
        const selectors = [
            { query: 'button', type: 'button' },
            { query: 'a[href]', type: 'link' },
            { query: '[role="button"]', type: 'role-button' },
            { query: 'input[type="text"], input[type="email"], input[type="search"], input[type="password"], textarea', type: 'input' },
        ];

        for (const { query, type } of selectors) {
            const els = document.querySelectorAll(query);
            let count = 0;
            for (const el of els) {
                if (count >= ''' + str(MAX_SAMPLES_PER_TYPE) + ''') break;

                const rect = el.getBoundingClientRect();
                // Skip invisible or off-screen elements
                if (rect.width < 10 || rect.height < 10) continue;
                if (rect.top < -100 || rect.top > window.innerHeight + 500) continue;

                const s = window.getComputedStyle(el);
                const safeClass = (typeof el.className === 'string') ? el.className : (el.className?.baseVal || '');
                const cls = safeClass.split(/\\s+/).filter(Boolean);

                // Build a robust selector for re-finding this element
                let uniqueSelector = '';
                if (el.id) {
                    uniqueSelector = '#' + CSS.escape(el.id);
                } else {
                    // Use nth-of-type for precision
                    const parent = el.parentElement;
                    if (parent) {
                        const siblings = parent.querySelectorAll(':scope > ' + el.tagName.toLowerCase());
                        let idx = 0;
                        for (let i = 0; i < siblings.length; i++) {
                            if (siblings[i] === el) { idx = i; break; }
                        }
                        const parentSel = parent.id ? '#' + CSS.escape(parent.id) :
                            (parent.tagName.toLowerCase() !== 'body' ? parent.tagName.toLowerCase() : 'body');
                        uniqueSelector = parentSel + ' > ' + el.tagName.toLowerCase() + ':nth-of-type(' + (idx + 1) + ')';
                    } else {
                        uniqueSelector = el.tagName.toLowerCase();
                    }
                }

                results.push({
                    type,
                    selector: uniqueSelector,
                    displaySelector: el.id ? '#' + el.id : (cls[0] ? '.' + cls[0] : el.tagName.toLowerCase()),
                    text: (el.textContent || '').replace(/\\s+/g, ' ').trim().substring(0, 30),
                    tag: el.tagName.toLowerCase(),
                    resting: {
                        backgroundColor: s.backgroundColor,
                        color: s.color,
                        borderColor: s.borderColor,
                        boxShadow: s.boxShadow,
                        outline: s.outline,
                        outlineColor: s.outlineColor,
                        outlineWidth: s.outlineWidth,
                        outlineOffset: s.outlineOffset,
                        transform: s.transform,
                        opacity: s.opacity,
                        textDecoration: s.textDecoration,
                        borderRadius: s.borderRadius,
                    },
                    bounds: {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                    }
                });
                count++;
            }
        }

        return results;
    }''')

    if not resting_elements:
        logger.info("No interactive elements found for state capture")
        return _empty_result()

    # Trim to max total
    elements = resting_elements[:MAX_TOTAL_HOVERS]
    logger.info(f"Capturing states for {len(elements)} interactive elements...")

    hover_deltas = []
    focus_deltas = []
    hover_colors = {}  # role -> {resting, hover}
    elements_tested = 0
    states_detected = 0

    for el in elements:
        selector = el['selector']
        try:
            locator = page.locator(selector).first

            # Verify element exists and is visible
            if not await locator.is_visible(timeout=1000):
                continue

            elements_tested += 1

            # --- HOVER STATE ---
            try:
                await locator.hover(timeout=2000)
                # Small wait for transition to complete
                await page.wait_for_timeout(150)

                hover_styles = await page.evaluate('''(sel) => {
                    const el = document.querySelector(sel);
                    if (!el) return null;
                    const s = window.getComputedStyle(el);
                    return {
                        backgroundColor: s.backgroundColor,
                        color: s.color,
                        borderColor: s.borderColor,
                        boxShadow: s.boxShadow,
                        outline: s.outline,
                        outlineColor: s.outlineColor,
                        outlineWidth: s.outlineWidth,
                        outlineOffset: s.outlineOffset,
                        transform: s.transform,
                        opacity: s.opacity,
                        textDecoration: s.textDecoration,
                        borderRadius: s.borderRadius,
                    };
                }''', selector)

                if hover_styles:
                    delta = _compute_delta(el['resting'], hover_styles)
                    if delta:
                        hover_deltas.append({
                            'selector': el['displaySelector'],
                            'text': el['text'],
                            'type': el['type'],
                            'tag': el['tag'],
                            'changes': delta,
                            'resting': {k: el['resting'][k] for k in delta},
                            'hover': {k: hover_styles[k] for k in delta},
                        })
                        states_detected += 1

                        # Track hover colors for color roles
                        if 'backgroundColor' in delta:
                            _track_hover_color(
                                hover_colors, el['type'],
                                el['resting']['backgroundColor'],
                                hover_styles['backgroundColor']
                            )
                        if 'color' in delta:
                            _track_hover_color(
                                hover_colors, el['type'] + '_text',
                                el['resting']['color'],
                                hover_styles['color']
                            )

            except Exception as e:
                logger.debug(f"Hover failed for {selector}: {str(e)[:60]}")

            # --- FOCUS STATE ---
            try:
                # Move mouse away first to clear hover
                await page.mouse.move(0, 0)
                await page.wait_for_timeout(100)

                # Focus the element
                await locator.focus(timeout=2000)
                await page.wait_for_timeout(100)

                focus_styles = await page.evaluate('''(sel) => {
                    const el = document.querySelector(sel);
                    if (!el) return null;
                    const s = window.getComputedStyle(el);
                    return {
                        backgroundColor: s.backgroundColor,
                        color: s.color,
                        borderColor: s.borderColor,
                        boxShadow: s.boxShadow,
                        outline: s.outline,
                        outlineColor: s.outlineColor,
                        outlineWidth: s.outlineWidth,
                        outlineOffset: s.outlineOffset,
                        transform: s.transform,
                        opacity: s.opacity,
                        textDecoration: s.textDecoration,
                        borderRadius: s.borderRadius,
                    };
                }''', selector)

                if focus_styles:
                    delta = _compute_delta(el['resting'], focus_styles)
                    if delta:
                        focus_deltas.append({
                            'selector': el['displaySelector'],
                            'text': el['text'],
                            'type': el['type'],
                            'tag': el['tag'],
                            'changes': delta,
                            'resting': {k: el['resting'][k] for k in delta},
                            'focus': {k: focus_styles[k] for k in delta},
                        })
                        states_detected += 1

                # Blur to reset
                await page.evaluate('''(sel) => {
                    const el = document.querySelector(sel);
                    if (el && el.blur) el.blur();
                }''', selector)

            except Exception as e:
                logger.debug(f"Focus failed for {selector}: {str(e)[:60]}")

        except Exception as e:
            logger.debug(f"State capture failed for {selector}: {str(e)[:60]}")
            continue

    # Move mouse to corner to reset all hover states
    try:
        await page.mouse.move(0, 0)
    except Exception:
        pass

    # Analyze patterns
    patterns = _analyze_hover_patterns(hover_deltas)

    logger.info(
        f"State capture complete: {elements_tested} elements tested, "
        f"{states_detected} state changes detected "
        f"({len(hover_deltas)} hover, {len(focus_deltas)} focus)"
    )

    return {
        'hover_deltas': hover_deltas,
        'focus_deltas': focus_deltas,
        'hover_colors': hover_colors,
        'patterns': patterns,
        'elements_tested': elements_tested,
        'states_detected': states_detected,
    }


def _empty_result() -> Dict:
    return {
        'hover_deltas': [],
        'focus_deltas': [],
        'hover_colors': {},
        'patterns': [],
        'elements_tested': 0,
        'states_detected': 0,
    }


def _compute_delta(resting: Dict, state: Dict) -> Dict:
    """Compare resting vs state styles, return only changed properties.

    Filters out subpixel anti-aliasing noise: color shifts < 5 RGB units are
    invisible and caused by cursor proximity, not real CSS :hover rules.
    """
    delta = {}
    for prop in STATE_PROPERTIES:
        r_val = resting.get(prop, '')
        s_val = state.get(prop, '')
        if r_val != s_val and s_val:
            # For color properties, filter subpixel noise
            if prop in ('backgroundColor', 'color', 'borderColor', 'outlineColor'):
                if _is_subpixel_color_change(r_val, s_val):
                    continue
            # For outline shorthand, check if only the color component changed by subpixel amount
            if prop == 'outline':
                r_rgb = _parse_rgb(r_val)
                s_rgb = _parse_rgb(s_val)
                if r_rgb and s_rgb:
                    max_diff = max(abs(r_rgb[i] - s_rgb[i]) for i in range(3))
                    # If only color changed by subpixel amount, skip
                    r_no_color = r_val.replace(f'rgb({r_rgb[0]}, {r_rgb[1]}, {r_rgb[2]})', '')
                    s_no_color = s_val.replace(f'rgb({s_rgb[0]}, {s_rgb[1]}, {s_rgb[2]})', '')
                    if r_no_color == s_no_color and max_diff < 5:
                        continue
            delta[prop] = True
    return delta


# Minimum RGB channel delta to count as a real color change (not anti-aliasing noise)
_MIN_COLOR_DELTA = 5


def _is_subpixel_color_change(resting_str: str, state_str: str) -> bool:
    """Return True if the color difference is subpixel noise (< 5 RGB units)."""
    r = _parse_rgb(resting_str)
    s = _parse_rgb(state_str)
    if not r or not s:
        return False  # Can't parse → assume real change
    max_diff = max(abs(r[i] - s[i]) for i in range(3))
    return max_diff < _MIN_COLOR_DELTA


def _track_hover_color(hover_colors: Dict, role: str, resting: str, hover: str):
    """Track hover color changes for color role extraction."""
    if not resting or not hover:
        return
    if resting == hover:
        return
    # Skip transparent
    if resting in ('rgba(0, 0, 0, 0)', 'transparent') and hover in ('rgba(0, 0, 0, 0)', 'transparent'):
        return
    key = f'{role}_hover'
    if key not in hover_colors:
        hover_colors[key] = []
    hover_colors[key].append({
        'resting': resting,
        'hover': hover,
    })


def _parse_rgb(color_str: str) -> Optional[Tuple[int, int, int]]:
    """Parse rgb(r, g, b) or rgba(r, g, b, a) string to tuple."""
    if not color_str:
        return None
    import re
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color_str)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _color_delta_description(resting_str: str, hover_str: str) -> str:
    """Describe the color change in human terms."""
    r = _parse_rgb(resting_str)
    h = _parse_rgb(hover_str)
    if not r or not h:
        return f'{resting_str} → {hover_str}'

    # Calculate brightness delta
    r_brightness = (r[0] * 299 + r[1] * 587 + r[2] * 114) / 1000
    h_brightness = (h[0] * 299 + h[1] * 587 + h[2] * 114) / 1000
    delta_pct = round(abs(h_brightness - r_brightness) / max(r_brightness, 1) * 100)

    if h_brightness < r_brightness:
        return f'Darkens ~{delta_pct}%'
    elif h_brightness > r_brightness:
        return f'Lightens ~{delta_pct}%'
    else:
        return 'Hue shift'


def _analyze_hover_patterns(hover_deltas: List[Dict]) -> List[Dict]:
    """Detect systematic hover patterns across elements."""
    patterns = []

    if not hover_deltas:
        return patterns

    # Group by element type
    by_type = {}
    for delta in hover_deltas:
        t = delta['type']
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(delta)

    for elem_type, deltas in by_type.items():
        # Find common property changes
        prop_counts = {}
        for d in deltas:
            for prop in d['changes']:
                prop_counts[prop] = prop_counts.get(prop, 0) + 1

        common_props = [p for p, c in prop_counts.items() if c >= 2 or c == len(deltas)]

        if not common_props:
            continue

        # For background color changes, describe the pattern
        descriptions = []
        for d in deltas[:3]:
            if 'backgroundColor' in d.get('resting', {}) and 'backgroundColor' in d.get('hover', {}):
                desc = _color_delta_description(
                    d['resting']['backgroundColor'],
                    d['hover']['backgroundColor']
                )
                descriptions.append(desc)

        # Deduplicate descriptions
        unique_descs = list(dict.fromkeys(descriptions))

        patterns.append({
            'type': elem_type,
            'count': len(deltas),
            'common_changes': common_props,
            'description': unique_descs[0] if unique_descs else f'{", ".join(common_props)} change on hover',
            'examples': [d['selector'] for d in deltas[:3]],
        })

    return patterns
