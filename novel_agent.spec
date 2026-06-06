# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Novel Agent single exe."""

import os

block_cipher = None
ROOT = os.path.abspath('.')

a = Analysis(
    ['main.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # Vue frontend
        ('web/frontend/dist', 'web/frontend/dist'),
        # Config
        ('config', 'config'),
        # Prompts
        ('prompts', 'prompts'),
        # Assets (templates, user edits at runtime)
        ('assets', 'assets'),
        # State templates
        ('state', 'state'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'web.server',
        'web.tasks',
        'web.models',
        'web.novel_chat',
        'novel_agent.agents.base',
        'novel_agent.agents.planner',
        'novel_agent.agents.writer',
        'novel_agent.agents.context_builder',
        'novel_agent.agents.length_fix',
        'novel_agent.agents.stitch_editor',
        'novel_agent.agents.style_editor',
        'novel_agent.agents.continuity_checker',
        'novel_agent.agents.auditor',
        'novel_agent.agents.chapter_summary',
        'novel_agent.agents.asset_compressor',
        'novel_agent.agents.chief_editor',
        'novel_agent.agents.managing_editor',
        'novel_agent.agents.chapter_planner',
        'novel_agent.agents.state_extractor',
        'novel_agent.state.manager',
        'novel_agent.state.sqlite_store',
        'novel_agent.state.vector_store',
        'novel_agent.pipeline',
        'novel_agent.orchestrator',
        'novel_agent.approval',
        'novel_agent.dashboard',
        'novel_agent.plugins',
        'novel_agent.plugins.base',
        'novel_agent.plugins.discovery',
        'novel_agent.plugins.manager',
        'novel_agent.control.calibration',
        'novel_agent.control.chapter_window',
        'novel_agent.control.constraint_synthesizer',
        'novel_agent.control.genre_genes',
        'novel_agent.control.narrative_debt',
        'novel_agent.control.platform_profiles',
        'novel_agent.control.scale_profile',
        'novel_agent.control.serial_engine',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NovelAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for server logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
