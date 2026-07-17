"""LLM security assessment for probes with unambiguous success signals.

A good probe expects detector-matching output that is absent from its prompt
and the rendered page before submission. Probe authors own that contract; the
runtime baseline and echo evidence provide defense in depth.
"""
