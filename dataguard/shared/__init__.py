"""Shared infrastructure — config, logging, exceptions, types.

This package is the only layer with no dependencies on other dataguard layers.
Every other layer may import from shared, but shared must never import from
domain, application, infrastructure, or delivery.
"""
