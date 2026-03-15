"""
Interactive Elements Extractor — Buttons, inputs, forms, links-as-buttons.

Captures visual styles (including fontSize, fontWeight, padding, border, boxShadow),
groups by appearance, classifies primary/secondary/tertiary roles, and surfaces
selectors + counts.
"""

import logging
import re
from typing import Dict, List
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class InteractiveExtractor(BaseExtractor):
    name = "interactive_elements"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Analyzing interactive elements...")

        # 1. Buttons (with extended style properties)
        _buttons = await ctx.page.evaluate('''() => {
            const out = [];
            document.querySelectorAll("button").forEach(el => {
                const s = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) return;
                const cls = (typeof el.className === "string" ? el.className : (el.className.baseVal || "")).split(/\\s+/).filter(Boolean);
                const sel = el.id ? "#" + el.id : (cls[0] ? "." + cls[0] : "button");
                out.push({
                    text: (el.textContent || "").replace(/\\s+/g, " ").trim().substring(0, 40),
                    selector: sel,
                    bg: s.backgroundColor,
                    color: s.color,
                    borderRadius: s.borderRadius,
                    fontSize: s.fontSize,
                    fontWeight: s.fontWeight,
                    padding: s.padding,
                    border: s.border,
                    boxShadow: s.boxShadow,
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    type: el.getAttribute("type") || "button"
                });
            });
            return out;
        }''')

        # 2. Links styled as buttons (with extended style properties)
        _linkButtons = await ctx.page.evaluate('''() => {
            const out = [];
            document.querySelectorAll("a").forEach(el => {
                const cls = (typeof el.className === "string" ? el.className : (el.className.baseVal || "")).toLowerCase();
                const s = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) return;
                const hasBtnClass = /btn|button/.test(cls);
                const hasBg = s.backgroundColor && s.backgroundColor !== "rgba(0, 0, 0, 0)" && s.backgroundColor !== "transparent";
                if (hasBtnClass || hasBg) {
                    const classes = cls.split(/\\s+/).filter(Boolean);
                    const sel = el.id ? "#" + el.id : (classes[0] ? "." + classes[0] : "a");
                    out.push({
                        text: (el.textContent || "").replace(/\\s+/g, " ").trim().substring(0, 40),
                        selector: sel,
                        href: el.getAttribute("href") || "",
                        bg: s.backgroundColor,
                        color: s.color,
                        borderRadius: s.borderRadius,
                        fontSize: s.fontSize,
                        fontWeight: s.fontWeight,
                        padding: s.padding,
                        border: s.border,
                        boxShadow: s.boxShadow,
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    });
                }
            });
            return out;
        }''')

        # 3. Inputs
        _inputs = await ctx.page.evaluate('''() => {
            const out = [];
            document.querySelectorAll("input, select, textarea").forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) return;
                const s = window.getComputedStyle(el);
                let labelText = "";
                if (el.id) {
                    try {
                        const lbl = document.querySelector("label[for=\\"" + CSS.escape(el.id) + "\\"]");
                        if (lbl) labelText = lbl.textContent.trim();
                    } catch(e) {}
                }
                if (!labelText && el.closest("label")) {
                    labelText = el.closest("label").textContent.replace(el.value || "", "").trim();
                }
                const cls = (typeof el.className === "string" ? el.className : (el.className.baseVal || "")).split(/\\s+/).filter(Boolean);
                const sel = el.id ? "#" + CSS.escape(el.id) : (cls[0] ? "." + CSS.escape(cls[0]) : el.tagName.toLowerCase());
                out.push({
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute("type") || (el.tagName === "SELECT" ? "select" : "textarea"),
                    placeholder: el.getAttribute("placeholder") || "",
                    name: el.getAttribute("name") || "",
                    label: labelText.substring(0, 40),
                    selector: sel,
                    required: el.required || false,
                    bg: s.backgroundColor,
                    borderRadius: s.borderRadius,
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                });
            });
            return out;
        }''')

        # 4. Forms
        _forms = await ctx.page.evaluate('''() => {
            const out = [];
            document.querySelectorAll("form").forEach(el => {
                const rect = el.getBoundingClientRect();
                const cls = (typeof el.className === "string" ? el.className : (el.className.baseVal || "")).split(/\\s+/).filter(Boolean);
                const sel = el.id ? "#" + el.id : (cls[0] ? "." + cls[0] : "form");
                out.push({
                    selector: sel,
                    action: el.getAttribute("action") || "",
                    method: (el.getAttribute("method") || "get").toUpperCase(),
                    inputCount: el.querySelectorAll("input, select, textarea").length,
                    buttonCount: el.querySelectorAll("button, input[type=submit], input[type=button]").length,
                    visible: rect.width > 0 && rect.height > 0
                });
            });
            return out;
        }''')

        # 5. Counts
        _counts = await ctx.page.evaluate('''() => ({
            modals: document.querySelectorAll("[role=\\"dialog\\"], .modal, [class*=\\"modal\\"]").length,
            dropdowns: document.querySelectorAll("select, [role=\\"listbox\\"], [class*=\\"dropdown\\"]").length
        })''')

        # Group button styles (with extended properties)
        _allBtns = _buttons + _linkButtons
        _styleMap = {}
        for btn in _allBtns:
            key = btn['bg'] + '|' + btn['borderRadius']
            if key not in _styleMap:
                _styleMap[key] = {
                    'bg': btn['bg'], 'color': btn['color'],
                    'borderRadius': btn['borderRadius'],
                    'fontSize': btn.get('fontSize', ''),
                    'fontWeight': btn.get('fontWeight', ''),
                    'padding': btn.get('padding', ''),
                    'border': btn.get('border', ''),
                    'boxShadow': btn.get('boxShadow', ''),
                    'count': 0, 'examples': []
                }
            _styleMap[key]['count'] += 1
            if len(_styleMap[key]['examples']) < 3:
                _styleMap[key]['examples'].append({
                    'text': btn['text'], 'selector': btn['selector'],
                    'width': btn.get('width', 0), 'height': btn.get('height', 0)
                })
        _buttonStyles = sorted(_styleMap.values(), key=lambda s: -s['count'])

        # Classify button roles: primary / secondary / tertiary
        _buttonStyles = self._classify_button_roles(_buttonStyles)

        counts = {
            'buttons': len(_buttons),
            'linkButtons': len(_linkButtons),
            'inputs': len(_inputs),
            'forms': len(_forms),
            'modals': _counts.get('modals', 0),
            'dropdowns': _counts.get('dropdowns', 0)
        }

        parts = []
        if counts.get('buttons', 0) + counts.get('linkButtons', 0) > 0:
            parts.append(f"{counts['buttons'] + counts.get('linkButtons', 0)} buttons")
        if counts.get('inputs', 0) > 0:
            parts.append(f"{counts['inputs']} inputs")
        if counts.get('forms', 0) > 0:
            parts.append(f"{counts['forms']} forms")

        # 6. Enrich button styles with hover/focus state deltas if available
        mcp_capture = ctx.evidence.get('_mcp_state_capture')
        if mcp_capture:
            _buttonStyles = self._enrich_with_hover_states(_buttonStyles, mcp_capture)
            logger.info(f"Enriched button styles with {mcp_capture.get('states_detected', 0)} interaction states")

        return {
            'pattern': ', '.join(parts) if parts else 'No interactive elements',
            'confidence': min(95, 50 + sum(counts.values()) * 2),
            'counts': counts,
            'button_styles': _buttonStyles,
            'buttons': _buttons,
            'link_buttons': _linkButtons,
            'inputs': _inputs,
            'forms': _forms
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_opaque_bg(bg: str) -> bool:
        """Check if a background color is opaque (not transparent/zero-alpha)."""
        if not bg:
            return False
        if bg in ('transparent', 'rgba(0, 0, 0, 0)'):
            return False
        # Check for rgba with alpha 0
        match = re.search(r'rgba\(\s*\d+,\s*\d+,\s*\d+,\s*([\d.]+)\)', bg)
        if match and float(match.group(1)) < 0.1:
            return False
        return True

    @staticmethod
    def _is_outline_style(style: Dict) -> bool:
        """Check if a button style looks like an outline/ghost button."""
        bg = style.get('bg', '')
        border = style.get('border', '')
        # Transparent bg with visible border = outline
        is_transparent = not InteractiveExtractor._is_opaque_bg(bg)
        has_border = border and 'none' not in border and '0px' not in border
        return is_transparent and has_border

    @staticmethod
    def _enrich_with_hover_states(button_styles: List[Dict], mcp_capture: Dict) -> List[Dict]:
        """
        Enrich button style groups with hover/focus state deltas from MCP capture.

        Matches captured hover deltas to button style groups by selector overlap,
        then adds 'hover_state' and 'focus_state' dicts to each matching group.
        """
        hover_deltas = mcp_capture.get('hover_deltas', [])
        focus_deltas = mcp_capture.get('focus_deltas', [])
        patterns = mcp_capture.get('patterns', [])

        if not hover_deltas and not focus_deltas:
            return button_styles

        # Build lookup: selector -> delta (for buttons and links)
        hover_by_sel = {}
        for d in hover_deltas:
            if d.get('type') in ('button', 'link', 'role-button'):
                hover_by_sel[d['selector']] = d

        focus_by_sel = {}
        for d in focus_deltas:
            if d.get('type') in ('button', 'link', 'role-button', 'input'):
                focus_by_sel[d['selector']] = d

        # For each button style group, try to find matching hover/focus deltas
        for style_group in button_styles:
            examples = style_group.get('examples', [])
            for example in examples:
                sel = example.get('selector', '')
                # Check hover
                if sel in hover_by_sel:
                    delta = hover_by_sel[sel]
                    style_group['hover_state'] = {
                        'changes': list(delta.get('changes', {}).keys()),
                        'resting': delta.get('resting', {}),
                        'hover': delta.get('hover', {}),
                    }
                    break
                # Fuzzy match: check if any hover delta's selector contains this one
                for h_sel, h_delta in hover_by_sel.items():
                    if sel in h_sel or h_sel in sel:
                        style_group['hover_state'] = {
                            'changes': list(h_delta.get('changes', {}).keys()),
                            'resting': h_delta.get('resting', {}),
                            'hover': h_delta.get('hover', {}),
                        }
                        break

            # Same for focus
            for example in examples:
                sel = example.get('selector', '')
                if sel in focus_by_sel:
                    delta = focus_by_sel[sel]
                    style_group['focus_state'] = {
                        'changes': list(delta.get('changes', {}).keys()),
                        'resting': delta.get('resting', {}),
                        'focus': delta.get('focus', {}),
                    }
                    break

        # Add patterns summary to first style group (for display)
        if patterns and button_styles:
            button_patterns = [p for p in patterns if p['type'] in ('button', 'role-button')]
            link_patterns = [p for p in patterns if p['type'] == 'link']
            if button_patterns:
                button_styles[0]['hover_pattern'] = button_patterns[0].get('description', '')
            if link_patterns:
                # Add to first link-button group or first group
                for sg in button_styles:
                    if any('.a' in (e.get('selector', '') or '') for e in sg.get('examples', [])):
                        sg['hover_pattern'] = link_patterns[0].get('description', '')
                        break

        return button_styles

    @classmethod
    def _classify_button_roles(cls, button_styles: List[Dict]) -> List[Dict]:
        """
        Classify button styles as primary, secondary, or tertiary.

        Rules:
        - Most-used opaque-bg button = primary
        - Most-used transparent/outline button = secondary
        - Everything else = tertiary
        """
        if not button_styles:
            return button_styles

        # Separate opaque vs transparent/outline
        opaque = []
        outline = []
        for i, style in enumerate(button_styles):
            if cls._is_opaque_bg(style.get('bg', '')):
                opaque.append((i, style))
            elif cls._is_outline_style(style):
                outline.append((i, style))

        # Already sorted by count (descending), so first = most-used
        primary_set = False
        secondary_set = False

        for idx, style in opaque:
            if not primary_set:
                button_styles[idx]['role'] = 'primary'
                primary_set = True
            elif not secondary_set:
                button_styles[idx]['role'] = 'secondary'
                secondary_set = True
            else:
                button_styles[idx]['role'] = 'tertiary'

        for idx, style in outline:
            if not secondary_set:
                button_styles[idx]['role'] = 'secondary'
                secondary_set = True
            else:
                button_styles[idx]['role'] = 'tertiary'

        # Anything not yet classified
        for style in button_styles:
            if 'role' not in style:
                style['role'] = 'tertiary'

        return button_styles
