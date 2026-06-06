import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def get_target_triple():
    try:
        res = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True)
        for line in res.stdout.splitlines():
            if line.startswith("host:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    
    # Fallback to python detection
    arch = platform.machine().lower()
    if arch in ("amd64", "x86_64"):
        arch_str = "x86_64"
    elif arch in ("arm64", "aarch64"):
        arch_str = "aarch64"
    else:
        arch_str = arch
        
    system = platform.system().lower()
    if system == "windows":
        return f"{arch_str}-pc-windows-msvc"
    elif system == "darwin":
        return f"{arch_str}-apple-darwin"
    else:
        return f"{arch_str}-unknown-linux-gnu"

def main():
    root_dir = Path(__file__).resolve().parent.parent
    os.chdir(root_dir)
    
    triple = get_target_triple()
    print(f"Target system triple detected: {triple}")
    
    bin_name = "novel-agent-backend"
    ext = ".exe" if platform.system().lower() == "windows" else ""
    
    dist_path = root_dir / "build" / "python-runtime"
    work_path = root_dir / "build" / "pyinstaller-work"
    
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name", bin_name,
        "--distpath", str(dist_path),
        "--workpath", str(work_path),
        "--exclude-module", "onnxruntime",
        "--exclude-module", "transformers",
        "--exclude-module", "torch",
        "--collect-all", "uvicorn",
        "--collect-all", "fastapi",
        "--collect-all", "pydantic",
        "--collect-all", "pydantic_core",
        "--collect-all", "novel_agent",
        "--collect-all", "pip",
        "main.py"
    ]
    
    print("Running PyInstaller to compile Python backend to a single file Sidecar...")
    print("Command:", " ".join(pyinstaller_cmd))
    
    res = subprocess.run(pyinstaller_cmd)
    if res.returncode != 0:
        print("PyInstaller build failed!", file=sys.stderr)
        sys.exit(1)
        
    compiled_file = dist_path / f"{bin_name}{ext}"
    if not compiled_file.exists():
        print(f"Compiled binary not found at {compiled_file}!", file=sys.stderr)
        sys.exit(1)
        
    # Copy to tauri sidecar bin directory
    tauri_bin_dir = root_dir / "web" / "frontend" / "src-tauri" / "bin"
    tauri_bin_dir.mkdir(parents=True, exist_ok=True)
    
    dst_file = tauri_bin_dir / f"{bin_name}-{triple}{ext}"
    print(f"Copying compiled sidecar from {compiled_file} to {dst_file}...")
    shutil.copy2(compiled_file, dst_file)
    
    print("\n=============================================")
    print("Sidecar binary successfully built and copied!")
    print(f"Target location: {dst_file}")
    print("=============================================")

if __name__ == "__main__":
    main()
