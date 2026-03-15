"""
Animation Extractor — CSS animations, transitions, JS libraries, and interaction states.

Detects keyframes, transition declarations, animation libraries (GSAP, Anime.js, etc.),
and also extracts hover/focus/active style deltas via four detection strategies.
Produces two evidence keys: 'animations' and 'interaction_states'.
"""

import logging
from collections import defaultdict
from typing import Dict
from extractors.base import BaseExtractor, ExtractionContext

logger = logging.getLogger(__name__)


class AnimationExtractor(BaseExtractor):
    name = "animations"

    async def extract(self, ctx: ExtractionContext) -> Dict:
        logger.info("Analyzing animations...")

        anim_data = await ctx.page.evaluate('''() => {
            const animated = {
                transitions: [],
                animations: [],
                keyframes: [],
                libraries: {
                    gsap: !!window.gsap,
                    anime: !!window.anime,
                    threejs: !!window.THREE,
                    lottie: !!window.lottie
                }
            };

            // Defaults that mean "no animation/transition active"
            // "all" alone = global catch-all set by frameworks like Squarespace — not a specific transition
            const defaultTrans = ['none 0s ease 0s', 'all 0s ease 0s', 'none', '', 'all'];
            const defaultAnim = 'none 0s ease 0s 1 normal none running';

            const elements = document.querySelectorAll('*');
            const seenTrans = new Set();
            const seenAnim = new Set();
            for (const el of elements) {
                const styles = window.getComputedStyle(el);
                const safeClass = (typeof el.className === 'string') ? el.className : (el.className?.baseVal || '');
                const cls = safeClass.split(/\\s+/).filter(Boolean);
                const selector = el.id ? '#' + el.id : (cls[0] ? '.' + cls[0] : el.tagName.toLowerCase());

                const trans = styles.transition;
                if (trans && !defaultTrans.includes(trans)) {
                    const tKey = selector + '|' + trans;
                    if (!seenTrans.has(tKey)) {
                        seenTrans.add(tKey);
                        animated.transitions.push({ selector: selector, transition: trans });
                    }
                }

                const anim = styles.animation;
                if (anim && anim !== defaultAnim && !anim.startsWith('none')) {
                    const aKey = selector + '|' + anim;
                    if (!seenAnim.has(aKey)) {
                        seenAnim.add(aKey);
                        animated.animations.push({ selector: selector, animation: anim });
                    }
                }
            }

            // Extract @keyframes from stylesheets
            try {
                for (const sheet of document.styleSheets) {
                    try {
                        for (const rule of sheet.cssRules) {
                            if (rule.type === CSSRule.KEYFRAMES_RULE) {
                                animated.keyframes.push({
                                    name: rule.name,
                                    cssText: rule.cssText.substring(0, 500)
                                });
                            }
                        }
                    } catch(e) { /* cross-origin sheet */ }
                }
            } catch(e) {}

            return animated;
        }''')

        anim_result = {
            'pattern': self._determine_animation_pattern(anim_data),
            'confidence': min(90, 40 + len(anim_data.get('animations', [])) * 5),
            'details': anim_data,
            'code_snippets': self._generate_animation_snippets(anim_data)
        }

        # Also extract interaction states and store as a second key
        interaction_result = await self._extract_interaction_states(ctx)

        # Store interaction_states in ctx.evidence so downstream extractors can access it
        ctx.evidence['interaction_states'] = interaction_result

        return anim_result

    # ------------------------------------------------------------------
    # Interaction States (produces ctx.evidence['interaction_states'])
    # ------------------------------------------------------------------

    async def _extract_interaction_states(self, ctx: ExtractionContext) -> Dict:
        """Extract hover/focus/active style deltas from modern CSS approaches.

        Modern sites use three approaches for interaction states:
        1. Traditional :hover/:focus CSS rules in stylesheets
        2. Tailwind/utility classes (hover:bg-blue-500)
        3. CSS-in-JS libraries (styled-components, emotion)

        This method detects all three and combines results.
        """
        logger.info("Extracting interaction states...")

        # Strategy 1: Traditional CSS pseudo-class rules
        traditional_rules = await ctx.page.evaluate('''() => {
            const results = [];
            const pseudos = [':hover', ':focus', ':active', ':focus-within', ':focus-visible'];
            try {
                for (const sheet of document.styleSheets) {
                    let rules;
                    try { rules = sheet.cssRules || sheet.rules; }
                    catch(e) { continue; } // cross-origin stylesheet
                    if (!rules) continue;
                    for (const rule of rules) {
                        if (!rule.selectorText) continue;
                        const sel = rule.selectorText;
                        const matchedPseudo = pseudos.find(p => sel.includes(p));
                        if (!matchedPseudo) continue;
                        const base = sel.replace(matchedPseudo, '').replace(/::before|::after/g, '').trim();
                        if (!base || base.length > 120) continue;
                        const props = {};
                        for (let i = 0; i < rule.style.length; i++) {
                            const prop = rule.style[i];
                            props[prop] = rule.style.getPropertyValue(prop);
                        }
                        if (Object.keys(props).length === 0) continue;
                        results.push({ base, pseudo: matchedPseudo, props });
                    }
                }
            } catch(e) {}
            return results;
        }''')

        # Strategy 2: Extract Tailwind/utility interaction classes from DOM
        utility_classes = await ctx.page.evaluate('''() => {
            const allElements = document.querySelectorAll('*');
            const interactionClasses = {
                hover: [],
                focus: [],
                active: [],
                disabled: []
            };

            allElements.forEach(el => {
                if (!el.className || typeof el.className !== 'string') return;

                const classes = el.className.split(' ').filter(c => c.trim());

                classes.forEach(c => {
                    if (c.startsWith('hover:')) interactionClasses.hover.push(c);
                    else if (c.startsWith('focus:')) interactionClasses.focus.push(c);
                    else if (c.startsWith('active:')) interactionClasses.active.push(c);
                    else if (c.startsWith('disabled:')) interactionClasses.disabled.push(c);
                });
            });

            // Deduplicate and count
            return {
                hover: [...new Set(interactionClasses.hover)],
                focus: [...new Set(interactionClasses.focus)],
                active: [...new Set(interactionClasses.active)],
                disabled: [...new Set(interactionClasses.disabled)]
            };
        }''')

        # Strategy 3: Check <style> tags for hover rules (CSS-in-JS)
        style_tag_rules = await ctx.page.evaluate('''() => {
            const allStyleTags = document.querySelectorAll('style');
            let hoverRules = [];

            allStyleTags.forEach(tag => {
                const content = tag.textContent;
                // Find hover rules
                const hoverRegex = /([^{}]+):hover\s*{([^}]*)}/g;
                let match;
                while ((match = hoverRegex.exec(content)) !== null && hoverRules.length < 20) {
                    hoverRules.push({
                        selector: match[1].trim(),
                        styles: match[2].trim()
                    });
                }
            });

            return hoverRules;
        }''')

        # Strategy 4: Physical hover/focus via Playwright (replaces broken dispatchEvent)
        # dispatchEvent('mouseenter') does NOT trigger CSS :hover — only fires JS listeners.
        # Playwright's .hover() physically moves the mouse cursor → triggers real CSS :hover.
        # State capture runs as StateCaptureExtractor earlier in the pipeline — read its results.
        computed_hover_states = []
        mcp_state_capture = ctx.evidence.get('_mcp_state_capture', {})
        if mcp_state_capture and mcp_state_capture.get('states_detected', 0) > 0:
            # Convert to legacy format for backward compatibility
            for delta in (mcp_state_capture.get('hover_deltas') or []):
                computed_hover_states.append({
                    'tag': delta.get('tag', 'unknown'),
                    'type': 'hover',
                    'selector': delta.get('selector', ''),
                    'text': delta.get('text', ''),
                    'changes': {
                        'bgChanged': 'backgroundColor' in delta.get('changes', {}),
                        'colorChanged': 'color' in delta.get('changes', {}),
                    },
                    'resting': delta.get('resting', {}),
                    'hover': delta.get('hover', {}),
                })
            for delta in (mcp_state_capture.get('focus_deltas') or []):
                computed_hover_states.append({
                    'tag': delta.get('tag', 'unknown'),
                    'type': 'focus',
                    'selector': delta.get('selector', ''),
                    'text': delta.get('text', ''),
                    'changes': delta.get('changes', {}),
                    'resting': delta.get('resting', {}),
                    'focus': delta.get('focus', {}),
                })
            logger.info(
                f"Physical state capture: {mcp_state_capture.get('elements_tested', 0)} tested, "
                f"{mcp_state_capture.get('states_detected', 0)} changes detected"
            )

        # Combine all four strategies
        total_traditional = len(traditional_rules) if traditional_rules else 0
        total_utility = sum(len(v) for v in utility_classes.values())
        total_style_tags = len(style_tag_rules) if style_tag_rules else 0
        total_computed = len(computed_hover_states) if computed_hover_states else 0
        total_detections = total_traditional + total_utility + total_style_tags + total_computed

        if total_detections == 0:
            return {
                'pattern': 'No interaction state styles detected',
                'confidence': 30,
                'state_deltas': {},
                'utility_classes': {},
                'computed_states': {},
                'evidence_trail': {
                    'found': [
                        '0 traditional CSS pseudo-class rules',
                        '0 utility interaction classes',
                        '0 hover rules in <style> tags',
                        '0 computed hover state changes'
                    ],
                    'concluded': 'No hover/focus/active styles found across 4 detection strategies'
                }
            }

        # Process traditional CSS rules
        grouped_traditional = defaultdict(lambda: defaultdict(dict))
        for rule in (traditional_rules or []):
            base = rule['base']
            pseudo = rule['pseudo'].lstrip(':')
            for prop, val in rule['props'].items():
                grouped_traditional[base][pseudo][prop] = val

        # Classify selectors by type
        type_buckets = defaultdict(list)
        for sel in grouped_traditional:
            sel_lower = sel.lower().strip()
            if 'button' in sel_lower or 'btn' in sel_lower:
                type_buckets['buttons'].append(sel)
            elif sel_lower.startswith('a') or 'link' in sel_lower:
                type_buckets['links'].append(sel)
            elif 'input' in sel_lower or 'select' in sel_lower or 'textarea' in sel_lower or 'form' in sel_lower:
                type_buckets['inputs'].append(sel)
            elif 'nav' in sel_lower or 'menu' in sel_lower or 'tab' in sel_lower:
                type_buckets['navigation'].append(sel)
            else:
                type_buckets['other'].append(sel)

        # Build state_deltas for traditional CSS
        state_deltas = {}
        for sel, states in sorted(grouped_traditional.items(), key=lambda x: -sum(len(v) for v in x[1].values()))[:15]:
            state_deltas[sel] = {pseudo: dict(props) for pseudo, props in states.items()}

        # Count coverage
        pseudo_counts = defaultdict(int)
        for sel, states in grouped_traditional.items():
            for pseudo in states.keys():
                pseudo_counts[pseudo] += 1

        # Add all strategy counts together
        hover_count = (pseudo_counts.get('hover', 0) +
                       len(utility_classes.get('hover', [])) +
                       total_style_tags +
                       len([s for s in computed_hover_states if s.get('type') == 'hover']))
        focus_count = (pseudo_counts.get('focus', 0) +
                       pseudo_counts.get('focus-visible', 0) +
                       pseudo_counts.get('focus-within', 0) +
                       len(utility_classes.get('focus', [])))
        active_count = pseudo_counts.get('active', 0) + len(utility_classes.get('active', []))
        disabled_count = len(utility_classes.get('disabled', []))

        # Calculate confidence based on total coverage and detection diversity
        confidence = 40
        if hover_count > 3:
            confidence += 20
        if focus_count > 2:
            confidence += 15
        if active_count > 1:
            confidence += 10
        if total_detections > 10:
            confidence += 15
        # Bonus for using multiple detection strategies
        strategies_used = sum([total_traditional > 0, total_utility > 0, total_style_tags > 0, total_computed > 0])
        if strategies_used >= 2:
            confidence += 5
        confidence = min(confidence, 95)

        # Build pattern description
        pattern_parts = []
        if hover_count:
            pattern_parts.append(f'{hover_count} hover')
        if focus_count:
            pattern_parts.append(f'{focus_count} focus')
        if active_count:
            pattern_parts.append(f'{active_count} active')
        if disabled_count:
            pattern_parts.append(f'{disabled_count} disabled')

        detection_method = []
        if total_traditional > 0:
            detection_method.append('CSS pseudo-classes')
        if total_utility > 0:
            detection_method.append('utility classes')
        if total_style_tags > 0:
            detection_method.append('<style> tags')
        if total_computed > 0:
            detection_method.append('computed states')

        # Prepare computed states summary (tag → count)
        computed_summary = {}
        for state in computed_hover_states:
            tag = state.get('tag', 'unknown')
            if tag not in computed_summary:
                computed_summary[tag] = 0
            computed_summary[tag] += 1

        # Physical hover/focus delta samples (for dashboard display)
        hover_samples = mcp_state_capture.get('hover_deltas', [])[:8] if mcp_state_capture else []
        focus_samples = mcp_state_capture.get('focus_deltas', [])[:5] if mcp_state_capture else []
        hover_patterns = mcp_state_capture.get('patterns', []) if mcp_state_capture else []

        return {
            'pattern': f'{total_detections} interaction states detected ({", ".join(pattern_parts)}) via {" + ".join(detection_method)}',
            'confidence': confidence,
            'state_deltas': state_deltas,
            'utility_classes': utility_classes,
            'computed_states': computed_summary,
            'physical_hover_deltas': hover_samples,
            'physical_focus_deltas': focus_samples,
            'physical_patterns': hover_patterns,
            'style_tag_rules_sample': style_tag_rules[:5] if style_tag_rules else [],
            'type_summary': {k: len(v) for k, v in type_buckets.items()},
            'detection_breakdown': {
                'traditional_css': total_traditional,
                'utility_classes': total_utility,
                'style_tags': total_style_tags,
                'computed_hover': total_computed
            },
            'evidence_trail': {
                'found': [
                    f'{total_traditional} traditional CSS pseudo-class rules',
                    f'{total_utility} utility interaction classes (Tailwind/etc)',
                    f'{total_style_tags} hover rules in <style> tags (CSS-in-JS)',
                    f'{total_computed} computed hover state changes',
                    f'{hover_count} hover states, {focus_count} focus states, {active_count} active states'
                ],
                'analyzed': [
                    'Scanned document.styleSheets for :hover/:focus/:active selectors',
                    'Extracted hover:*/focus:*/active:*/disabled:* utility classes from DOM',
                    'Searched <style> tags for CSS-in-JS hover rules',
                    'Programmatically triggered hover on buttons/links and detected style changes',
                    f'Combined all 4 detection strategies ({strategies_used} strategies had results)'
                ],
                'concluded': f'Site uses {", ".join(detection_method)} for {len(pattern_parts)} interaction state types'
            }
        }

    # ------------------------------------------------------------------
    # Animation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_animation_pattern(data):
        libs = [k for k, v in data['libraries'].items() if v]
        if libs:
            return f"JS Libraries: {', '.join(libs)}"

        parts = []
        if data.get('keyframes'):
            parts.append(f"{len(data['keyframes'])} @keyframes")
        if data['animations']:
            parts.append(f"{len(data['animations'])} animated elements")
        if data['transitions']:
            parts.append(f"{len(data['transitions'])} transitions")

        return ', '.join(parts) if parts else "No animations detected"

    @staticmethod
    def _generate_animation_snippets(data):
        parts = []
        # Keyframes first -- most informative
        for kf in data.get('keyframes', [])[:2]:
            parts.append(kf['cssText'])
        # Then a transition example
        if data['transitions'] and len(parts) < 2:
            ex = data['transitions'][0]
            parts.append(f"{ex['selector']} {{\n  transition: {ex['transition']};\n}}")
        # Then an animation example
        if data['animations'] and len(parts) < 2:
            ex = data['animations'][0]
            parts.append(f"{ex['selector']} {{\n  animation: {ex['animation']};\n}}")
        return '\n\n'.join(parts) if parts else None
