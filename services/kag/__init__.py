"""
KAG (Knowledge Augmented Generation) Services Package

This package provides services for generating KAG input files and processing
documents for knowledge augmentation workflows.
"""

from .kag_writer import generate_kag_input

__all__ = ["generate_kag_input"]