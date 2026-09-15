import { delimiter, resolve } from 'node:path'
import { readdirSync, rmSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const root = resolve(fileURLToPath(new URL('..', import.meta.url)))
const candidates =
  process.platform === 'win32'
    ? [
        ['py', ['-3.12']],
        ['py', ['-3.11']],
        ['python', []],
      ]
    : [
        ['python3.12', []],
        ['python3.11', []],
        ['python3', []],
        ['python', []],
      ]

function findBuildPython() {
  const rejected = []
  for (const [command, prefix] of candidates) {
    const probe = spawnSync(
      command,
      [
        ...prefix,
        '-c',
        [
          'import sys',
          'assert (3, 11) <= sys.version_info[:2] < (3, 13)',
          'import PyInstaller, fastapi, pydantic, docx, reportlab',
          'import novel_agent.exporters',
          'print(sys.executable)',
        ].join(';'),
      ],
      { cwd: root, encoding: 'utf8' },
    )
    if (probe.status === 0) {
      return { command, prefix, executable: probe.stdout.trim() }
    }
    rejected.push(`${command} ${prefix.join(' ')}`.trim())
  }

  throw new Error(
    [
      'No supported Python build environment was found.',
      `Tried: ${rejected.join(', ')}`,
      'Install Python 3.11 or 3.12 dependencies with:',
      '  py -3.12 -m pip install -r requirements.txt -r requirements-build.txt',
    ].join('\n'),
  )
}

function addData(source, destination) {
  return `${source}${delimiter}${destination}`
}

function removePythonCaches(rootPath) {
  const entries = readdirSync(rootPath, { withFileTypes: true })
  for (const entry of entries) {
    const entryPath = resolve(rootPath, entry.name)
    if (!entry.isDirectory()) continue
    if (entry.name === '__pycache__') {
      rmSync(entryPath, { recursive: true, force: true })
      continue
    }
    removePythonCaches(entryPath)
  }
}

const python = findBuildPython()
console.log(`Building desktop backend with ${python.executable}`)

const args = [
  ...python.prefix,
  '-m',
  'PyInstaller',
  '--noconfirm',
  '--clean',
  '--onedir',
  '--name',
  'novel-agent-backend',
  '--distpath',
  'build/python-runtime',
  '--workpath',
  'build/pyinstaller-work-v2',
  '--add-data',
  addData('web/frontend/dist', 'web/frontend/dist'),
  '--add-data',
  addData('web/factory_modes.json', 'web'),
  '--add-data',
  addData('prompts', 'prompts'),
  '--add-data',
  addData('presets', 'presets'),
  '--exclude-module',
  'onnxruntime',
  '--exclude-module',
  'transformers',
  '--exclude-module',
  'torch',
  '--collect-all',
  'uvicorn',
  '--collect-all',
  'fastapi',
  '--collect-all',
  'pydantic',
  '--collect-all',
  'pydantic_core',
  '--collect-all',
  'docx',
  '--collect-all',
  'reportlab',
  '--collect-all',
  'novel_agent',
  '--collect-all',
  'pip',
  'main.py',
]

const build = spawnSync(python.command, args, {
  cwd: root,
  stdio: 'inherit',
})

if (build.error) {
  throw build.error
}
if (build.status !== 0) {
  process.exit(build.status ?? 1)
}

console.log('PyInstaller build completed. Synchronizing frontend assets...')
const syncScript = resolve(root, 'scripts', 'sync_frontend_to_runtime.py')
const sync = spawnSync(python.command, [...python.prefix, syncScript], {
  cwd: root,
  stdio: 'inherit',
})
if (sync.status !== 0) {
  process.exit(sync.status ?? 1)
}

const runtimeRoot = resolve(root, 'build', 'python-runtime', 'novel-agent-backend')
removePythonCaches(runtimeRoot)
console.log('Removed Python bytecode caches from the desktop runtime.')

