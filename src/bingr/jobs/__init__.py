"""Periodic background jobs — scheduled tasks that emit event bus signals.

Jobs are pure schedulers: they never touch models/services directly.
View models subscribe to the emitted signals and refresh their data.
"""
