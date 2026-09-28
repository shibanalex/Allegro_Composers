"""Shared kernel: configuration, database session, errors, security, file storage and small helpers.

Knows nothing about the domain modules — `allegro.core` must never import from `allegro.modules`.
"""
