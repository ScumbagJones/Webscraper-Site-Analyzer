"""
API Relationship Mapper - jsoncrack.com-style Visual API Analysis

Analyzes network requests to detect:
1. API endpoint relationships (which calls which)
2. Data flow dependencies (response from A used in B)
3. WebSocket ↔ REST synchronization
4. Redundant/duplicate requests
5. Request chains and sequences

Use case: Instead of showing flat API list, show HOW they're connected
"""

import json
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse


class APIRelationshipMapper:
    """
    Analyze API requests to build relationship tree
    """

    def __init__(self, api_requests: List[Dict]):
        """
        Args:
            api_requests: List of API request dicts from network pulse
                Each dict should have: url, method, status, response_body
        """
        self.api_requests = api_requests or []

    def analyze_relationships(self) -> Dict:
        """
        Comprehensive API relationship analysis

        Returns:
            {
                'endpoints': [...],  # Unique API endpoints
                'semantic_classification': {...},  # APIs classified by design role
                'design_insights': {...},  # Human-readable architectural conclusions
                'relationships': [...],  # Connection between APIs
                'data_dependencies': [...],  # Response → Request usage
                'redundant_requests': [...],  # Duplicate calls
                'request_chains': [...],  # Sequential patterns
                'mermaid_diagram': '...',  # Visual diagram code
                'stats': {...}
            }
        """
        endpoints = self._extract_endpoints()
        semantic_map = self._classify_semantic_roles(endpoints)
        design_insights = self._generate_design_insights(semantic_map, endpoints)
        relationships = self._detect_relationships()
        data_deps = self._find_data_dependencies()
        redundant = self._find_redundant_requests()
        chains = self._identify_request_chains(relationships)

        try:
            mermaid = self._generate_mermaid_diagram(endpoints, relationships)
        except Exception:
            try:
                mermaid = self._generate_simplified_diagram(endpoints)
            except Exception:
                mermaid = self._generate_fallback_diagram(endpoints)

        return {
            'endpoints': endpoints,
            'semantic_classification': semantic_map,
            'design_insights': design_insights,
            'relationships': relationships,
            'data_dependencies': data_deps,
            'redundant_requests': redundant,
            'request_chains': chains,
            'mermaid_diagram': mermaid,
            'stats': self._calculate_stats(endpoints, relationships, data_deps, redundant),
        }

    def _extract_endpoints(self) -> List[Dict]:
        """
        Extract unique API endpoints with metadata
        """
        endpoint_map = {}
        for req in self.api_requests:
            url = req.get('url', '')
            if not url:
                continue
            method = req.get('method', 'GET')
            endpoint_key = f"{method} {url}"
            if endpoint_key not in endpoint_map:
                parsed = urlparse(url)
                path = parsed.path
                endpoint_map[endpoint_key] = {
                    'full_url': url,
                    'path': path,
                    'method': method,
                    'call_count': 0,
                    'status': req.get('status', 200),
                    'success_rate': 0,
                    'timestamp': req.get('timestamp', 0),
                }
            ep = endpoint_map[endpoint_key]
            ep['call_count'] += 1
            status = req.get('status', 200)
            if 200 <= status < 400:
                ep['success_rate'] = min(100, ep['success_rate'] + 1)

        return list(endpoint_map.values())

    def _classify_semantic_roles(self, endpoints: List[Dict]) -> Dict:
        """
        Classify APIs by design role (state, content, interaction, monetization, infrastructure)
        """
        PATTERNS = {
            'authentication': {
                'keywords': ['auth', 'login', 'logout', 'token', 'oauth', 'session', 'jwt', 'signup', 'register', 'password'],
                'paths': ['/auth', '/login', '/logout', '/token', '/signup'],
            },
            'content': {
                'keywords': ['article', 'post', 'blog', 'content', 'page', 'story', 'news', 'feed'],
                'paths': ['/articles', '/posts', '/content', '/pages'],
            },
            'user': {
                'keywords': ['user', 'profile', 'account', 'me', 'member'],
                'paths': ['/users', '/profile', '/me', '/account'],
            },
            'monetization': {
                'keywords': ['paywall', 'subscription', 'offer', 'payment', 'billing', 'plan', 'price'],
                'paths': ['/subscribe', '/billing', '/plans', '/offers'],
            },
            'interaction': {
                'keywords': ['comment', 'like', 'share', 'follow', 'vote', 'react', 'reply'],
                'paths': ['/comments', '/likes', '/reactions'],
            },
            'search': {
                'keywords': ['search', 'query', 'find', 'suggest', 'autocomplete'],
                'paths': ['/search', '/query', '/suggest'],
            },
            'feature_flags': {
                'keywords': ['flag', 'experiment', 'variant', 'feature', 'ab', 'cohort'],
                'paths': ['/flags', '/experiments', '/features'],
            },
        }

        classified: Dict[str, List] = {cat: [] for cat in PATTERNS}
        classified['unclassified'] = []

        for endpoint in endpoints:
            full_url = endpoint.get('full_url', '')
            path = endpoint.get('path', '').lower()
            matches = []
            for category, patterns in PATTERNS.items():
                kw_score = sum(1 for kw in patterns['keywords'] if kw in full_url.lower())
                path_score = sum(1 for p in patterns['paths'] if path.startswith(p))
                if kw_score >= 2 or path_score >= 1:
                    matches.append((category, kw_score + path_score * 2))

            if matches:
                best = sorted(matches, key=lambda x: x[1], reverse=True)[0][0]
                confidence = min(95, 50 + len(matches) * 15)
                classified[best].append({**endpoint, 'confidence': confidence})
            else:
                classified['unclassified'].append({**endpoint, 'confidence': 1})

        return {cat: apis for cat, apis in classified.items() if apis}

    def _generate_design_insights(self, semantic_map: Dict, endpoints: List[Dict]) -> Dict:
        """
        Generate human-readable architectural insights from semantic classification
        """
        insights = {}

        state_apis = semantic_map.get('authentication', {})
        if state_apis:
            has_jwt = any('jwt' in e.get('path', '') or 'token' in e.get('path', '') for e in state_apis)
            has_session = any('session' in e.get('path', '') for e in state_apis)
            has_me = any('/me' in e.get('path', '') for e in state_apis)
            if has_jwt:
                insights['auth_strategy'] = 'JWT-based stateless authentication'
            elif has_session:
                insights['auth_strategy'] = 'Server-side session management'
            if has_me:
                insights.setdefault('notes', []).append('User identity endpoint detected')
            insights.setdefault('notes', []).append('Authentication mechanism present')

        content_model_apis = semantic_map.get('content', [])
        if content_model_apis:
            entities = [e.get('path', '').split('/')[1] for e in content_model_apis if e.get('path', '').count('/') >= 1]
            entities = [e for e in entities if e]
            if entities:
                insights['content_model'] = 'Content model centers on: ' + ', '.join(set(entities))

        interaction_apis = semantic_map.get('interaction', [])
        if interaction_apis:
            insights['interaction_model'] = f'{len(interaction_apis)} interactive API endpoint(s) detected'

        monetization_apis = semantic_map.get('monetization', [])
        if monetization_apis:
            has_paywall = any('paywall' in e.get('path', '') for e in monetization_apis)
            has_subscription = any('subscription' in e.get('path', '') for e in monetization_apis)
            has_offer = any('offer' in e.get('path', '') for e in monetization_apis)
            if has_paywall or has_subscription or has_offer:
                insights['monetization'] = 'Metered paywall / subscription strategy detected'

        feature_flag_apis = semantic_map.get('feature_flags', [])
        if feature_flag_apis:
            has_flag = any('flag' in e.get('path', '') for e in feature_flag_apis)
            has_experiment = any('experiment' in e.get('path', '') for e in feature_flag_apis)
            if has_flag or has_experiment:
                insights['feature_flags'] = 'A/B testing or feature flag system detected'

        # Most-used category
        category_counts = {
            cat: sum(e.get('call_count', 1) for e in data)
            for cat, data in semantic_map.items()
            if cat != 'unclassified' and data
        }
        if category_counts:
            dominant = max(category_counts, key=lambda k: category_counts[k])
            insights['dominant_category'] = f'{dominant} APIs dominate traffic'

        return insights

    def _detect_relationships(self) -> List[Dict]:
        """
        Detect relationships between API endpoints
        """
        relationships = []
        sorted_requests = sorted(self.api_requests, key=lambda r: r.get('timestamp', 0))

        for i, req_a in enumerate(sorted_requests):
            for req_b in sorted_requests[i+1:i+6]:
                url_a = req_a.get('url', '')
                url_b = req_b.get('url', '')
                if not url_a or not url_b or url_a == url_b:
                    continue
                time_diff = req_b.get('timestamp', 0) - req_a.get('timestamp', 0)
                if time_diff < 0:
                    continue
                if time_diff < 50:
                    rel_type = 'parallel'
                elif time_diff < 500:
                    rel_type = 'sequential'
                else:
                    continue
                relationships.append({
                    'from': url_a,
                    'to': url_b,
                    'type': rel_type,
                    'time_gap_ms': time_diff,
                })
                if len(relationships) >= 100:
                    break

        return relationships

    def _find_data_dependencies(self) -> List[Dict]:
        """
        Find cases where response from API A is used in request to API B
        """
        dependencies = []
        for i, req_a in enumerate(self.api_requests):
            response_a = req_a.get('response_body', '')
            if not response_a:
                continue
            try:
                response_data = json.loads(response_a)
            except Exception as e:
                logging.debug(f'Could not parse API response (skipping): {e}')
                continue

            extracted_ids = self._extract_ids(response_data)
            for req_b in self.api_requests[i+1:]:
                url_b = req_b.get('url', '')
                body_b = req_b.get('request_body', '')
                for id_val in extracted_ids:
                    if str(id_val) in url_b or (body_b and str(id_val) in body_b):
                        dependencies.append({
                            'source_url': req_a.get('url', ''),
                            'target_url': url_b,
                            'shared_id': id_val,
                            'confidence': 'ID',
                            'confidence_pct': 95,
                        })
                        break

        return dependencies

    def _extract_ids(self, data, prefix: str = '') -> List:
        """
        Recursively extract potential ID fields from JSON data
        """
        ids = []
        id_fields = ('id', 'userId', 'user_id', 'postId', 'post_id', 'articleId', 'token')
        if isinstance(data, dict):
            for id_field in (k for k in data if k in id_fields):
                value = data[id_field]
                if isinstance(value, (str, int)) and len(str(value)) >= 3 and '.' not in str(value):
                    ids.append(value)
            for v in data.values():
                ids.extend(self._extract_ids(v, prefix))
        elif isinstance(data, list):
            for item in data[:5]:
                ids.extend(self._extract_ids(item, prefix))
        return ids

    def _find_redundant_requests(self) -> List[Dict]:
        """
        Find duplicate or redundant API calls
        """
        redundant = []
        url_groups: Dict[str, List] = {}
        for req in self.api_requests:
            url = req.get('url', '')
            if not url:
                continue
            url_groups.setdefault(url, []).append(req)

        for url, reqs in url_groups.items():
            if len(reqs) > 1:
                redundant.append({
                    'url': url,
                    'call_count': len(reqs),
                    'type': 'duplicate',
                    'wasted_calls': len(reqs) - 1,
                    'suggestion': 'Cache response or debounce calls',
                })

        return redundant

    def _identify_request_chains(self, relationships: List[Dict]) -> List[List[str]]:
        """
        Identify sequential request chains (A → B → C → D)
        """
        sequential = {r['from']: r['to'] for r in relationships if r.get('type') == 'sequential'}
        chains = []
        visited = set()

        def dfs(url, current_chain):
            if url in visited or len(current_chain) > 6:
                return
            visited.add(url)
            current_chain.append(url)
            next_url = sequential.get(url)
            if next_url:
                dfs(next_url, current_chain)
            elif len(current_chain) >= 2:
                chains.append(current_chain[:])
            current_chain.pop()

        for url in sequential:
            dfs(url, [])

        return [chain for chain in chains if len(chain) >= 2]

    def _generate_mermaid_diagram(self, endpoints: List[Dict], relationships: List[Dict]) -> str:
        """
        Generate Mermaid.js diagram code for visualization with robust error handling
        """
        if len(endpoints) > 15:
            return self._generate_simplified_diagram(endpoints)

        mermaid = 'graph TD\n'
        node_map = {}
        for i, endpoint in enumerate(endpoints):
            node_id = f'API{i}'
            node_map[endpoint.get('full_url', '')] = node_id
            method = endpoint.get('method', 'GET')
            path = endpoint.get('path', endpoint.get('full_url', ''))[-30:]
            count = endpoint.get('call_count', 1)
            label = path.replace('"', "'").replace('[', '(').replace(']', ')')
            mermaid += f'    {node_id}["{method}: {label} ×{count}"]\n'

        for rel in relationships[:20]:
            from_id = node_map.get(rel.get('from', ''))
            to_id = node_map.get(rel.get('to', ''))
            if from_id and to_id:
                rel_type = rel.get('type', '')
                arrow = '-->' if rel_type == 'sequential' else '-.->'
                mermaid += f'    {from_id} {arrow} {to_id}\n'

        return mermaid

    def _generate_simplified_diagram(self, endpoints: List[Dict]) -> str:
        """Generate simplified diagram for complex APIs"""
        mermaid = 'graph TD\n'
        mermaid += '    START[API Calls]\n'
        methods: Dict[str, List] = {}
        for endpoint in endpoints:
            method = endpoint.get('method', 'METHOD')
            methods.setdefault(method, []).append(endpoint)
        for i, (method, eps) in enumerate(methods.items()):
            count = sum(e.get('call_count', 1) for e in eps)
            label = f'{method}: {len(eps)} endpoints, {count} calls'
            mermaid += f'    M{i}["{label}"]\n'
            mermaid += f'    START --> M{i}\n'
        return mermaid

    def _generate_fallback_diagram(self, endpoints: List[Dict]) -> str:
        """Fallback when mermaid generation fails"""
        mermaid = 'graph TD\n'
        mermaid += f'    A[Detected {len(endpoints)} API endpoints]\n'
        methods = list({e.get('method', '') for e in endpoints})
        for i, method in enumerate(methods[:5]):
            eps = [e for e in endpoints if e.get('method') == method]
            count = sum(e.get('call_count', 1) for e in eps)
            mermaid += f'    B{i}["{method}: {count} calls"]\n'
            mermaid += f'    A --> B{i}\n'
        return mermaid

    def _calculate_stats(self, endpoints, relationships, data_deps, redundant) -> Dict:
        """
        Calculate overall statistics
        """
        total_requests = sum(e.get('call_count', 0) for e in endpoints)
        unique_endpoints = len(endpoints)
        total_relationships = len(relationships)
        wasted = sum(r.get('wasted_calls', 0) for r in redundant)
        efficiency = round(max(0, 100 - (wasted / max(total_requests, 1) * 100)), 1)
        return {
            'total_requests': total_requests,
            'unique_endpoints': unique_endpoints,
            'total_relationships': total_relationships,
            'data_dependencies': len(data_deps),
            'redundant_calls': len(redundant),
            'wasted_requests': wasted,
            'efficiency_score': efficiency,
        }
