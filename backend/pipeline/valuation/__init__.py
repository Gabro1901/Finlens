"""
Valuation Pipeline Module

Architecture:
  selector.py  -> LLM chooses model + params (JSON config)
  engine.py    -> Python executes selected models (pure code)
  model_library.py -> Individual valuation function implementations

All valuation math is code-computed. No AI-generated numbers.
"""

from .engine import ValuationEngine
from .selector import select_valuation_model
