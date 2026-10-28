"""TOM core — the new layer grown beside agent.py during the PRD v1.1 refactor.

Sub-packages are added phase by phase (see docs/migration/status.md):
  voice/    — replaceable ASR / TTS adapters running in isolated worker processes
  tasks/    — TaskService: one task API shared by every interface (R2)
  privacy   — which data routes leave the machine, and how each is opted into
"""
