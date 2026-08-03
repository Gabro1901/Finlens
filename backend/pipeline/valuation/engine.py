"""
Valuation Engine
================
Takes the LLM's JSON config (model selections + parameters) and executes
all specified valuation models using the pure-Python model_library.

All math is code-computed. Results flow to the Analyst LLM for narrative
generation.
"""

import json
from typing import Dict, Any, AsyncIterator

from .model_library import MODEL_REGISTRY


class ValuationEngine:
    """Executes valuation models specified by the LLM's JSON config."""

    def __init__(self, bundled_data: dict, valuation_config: dict):
        self.data = bundled_data
        self.config = valuation_config

    def run(self):
        """
        Execute all models specified in the config. Returns a dict
        with all results and a blended target price.
        """
        plan = self.config.get('valuation_plan', {})
        if not plan:
            return self._error('No valuation_plan found in config')

        primary = plan.get('primary', {})
        cross_checks = plan.get('cross_checks', [])

        results = {
            'business_profile': self.config.get('business_profile', {}),
            'model_results': {},
            'blended_target': None,
            'error': None,
        }

        # Run primary model
        primary_result = self._run_model(primary, 'primary')
        primary_price = primary_result.get('result', {}).get('implied_price') or \
                        primary_result.get('result', {}).get('blended_price') or \
                        primary_result.get('result', {}).get('price_mid') or \
                        primary_result.get('result', {}).get('fair_value') or 0
        results['model_results']['primary'] = primary_result

        # Run cross-checks
        cross_prices = []
        for i, cc in enumerate(cross_checks):
            label = cc.get('label', f'cross_check_{i}')
            cc_result = self._run_model(cc, label)
            results['model_results'][label] = cc_result

            # Extract price from cross-check
            res = cc_result.get('result', {})
            cc_price = res.get('implied_price') or \
                       res.get('blended_price') or \
                       res.get('price_mid') or \
                       res.get('fair_value') or 0
            if cc_price > 0:
                cross_prices.append((cc.get('weight', 0), cc_price))

        # Blend
        primary_weight = primary.get('weight', 0.50)
        total_weight = primary_weight + sum(w for w, _ in cross_prices)

        if total_weight > 0 and primary_price > 0:
            blended = primary_price * (primary_weight / total_weight)
            for w, p in cross_prices:
                blended += p * (w / total_weight)
            results['blended_target'] = round(blended, 2)

        # Current price for reference
        info = self.data.get('market', {}).get('info', {})
        results['current_price'] = float(info.get('currentPrice', 0))

        return results

    def run_streaming(self):
        """
        Generator version that yields SSE events as each model completes.
        Use this for the pipeline integration.
        """
        yield {
            'event': 'valuation_progress',
            'data': json.dumps({'stage': 'valuation_start', 'message': 'Starting quantitative valuation...'})
        }

        plan = self.config.get('valuation_plan', {})
        if not plan:
            yield {
                'event': 'valuation_error',
                'data': json.dumps({'message': 'No valuation_plan found in config'})
            }
            return

        primary = plan.get('primary', {})
        cross_checks = plan.get('cross_checks', [])

        results = {
            'business_profile': self.config.get('business_profile', {}),
            'model_results': {},
            'blended_target': None,
            'error': None,
        }

        # Primary model
        model_name = primary.get('model', 'unknown')
        yield {
            'event': 'valuation_progress',
            'data': json.dumps({
                'stage': 'running_model',
                'model': model_name,
                'label': 'primary',
                'message': f'Running {model_name.upper()} valuation...'
            })
        }

        primary_result = self._run_model(primary, 'primary')
        primary_price = self._extract_price(primary_result)
        results['model_results']['primary'] = primary_result

        yield {
            'event': 'valuation_progress',
            'data': json.dumps({
                'stage': 'model_complete',
                'model': model_name,
                'label': 'primary',
                'price': primary_price,
                'message': f'{model_name.upper()} complete -> ${primary_price:.2f}'
            })
        }

        # Cross-checks
        cross_prices = []
        for i, cc in enumerate(cross_checks):
            label = cc.get('label', f'cross_check_{i}')
            cc_model = cc.get('model', 'unknown')

            yield {
                'event': 'valuation_progress',
                'data': json.dumps({
                    'stage': 'running_model',
                    'model': cc_model,
                    'label': label,
                    'message': f'Running {cc_model.upper()} cross-check...'
                })
            }

            cc_result = self._run_model(cc, label)
            results['model_results'][label] = cc_result
            cc_price = self._extract_price(cc_result)
            if cc_price > 0:
                cross_prices.append((cc.get('weight', 0), cc_price))

            yield {
                'event': 'valuation_progress',
                'data': json.dumps({
                    'stage': 'model_complete',
                    'model': cc_model,
                    'label': label,
                    'price': cc_price,
                    'message': f'{cc_model.upper()} complete -> ${cc_price:.2f}'
                })
            }

        # Blend
        primary_weight = primary.get('weight', 0.50)
        total_weight = primary_weight + sum(w for w, _ in cross_prices)

        if total_weight > 0 and primary_price > 0:
            blended = primary_price * (primary_weight / total_weight)
            for w, p in cross_prices:
                blended += p * (w / total_weight)
            results['blended_target'] = round(blended, 2)

        info = self.data.get('market', {}).get('info', {})
        results['current_price'] = float(info.get('currentPrice', 0))

        bt = results.get('blended_target')
        msg = f'All models complete. Blended target: ${bt:.2f}' if bt is not None else 'All models complete. Blended target: N/A'
        
        yield {
            'event': 'valuation_progress',
            'data': json.dumps({
                'stage': 'valuation_complete',
                'blended_target': bt,
                'message': msg
            })
        }

        yield {
            'event': 'valuation_results',
            'data': json.dumps(results, default=str)
        }

    def _run_model(self, model_spec: dict, label: str) -> dict:
        """Run a single model and return its result."""
        model_type = model_spec.get('model', '')
        params = model_spec.get('params', {})
        weight = model_spec.get('weight', 0)

        if model_type not in MODEL_REGISTRY:
            return {
                'label': label,
                'model': model_type,
                'weight': weight,
                'error': f'Unknown model type: {model_type}',
                'result': {},
            }

        try:
            func = MODEL_REGISTRY[model_type]
            output = func(self.data, params)
            output['label'] = label
            output['weight'] = weight
            return output
        except Exception as e:
            return {
                'label': label,
                'model': model_type,
                'weight': weight,
                'error': str(e),
                'result': {},
            }

    @staticmethod
    def _extract_price(model_output: dict) -> float:
        """Extract the price target from a model's output dict."""
        res = model_output.get('result', {})
        if not res:
            return 0
        return (
            res.get('blended_price') or
            res.get('implied_price') or
            res.get('price_mid') or
            res.get('fair_value') or
            0
        )

    @staticmethod
    def _error(msg: str) -> dict:
        return {'error': msg, 'model_results': {}, 'blended_target': None}
