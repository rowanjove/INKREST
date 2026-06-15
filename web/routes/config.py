from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

import web.context as ws_server
import web.helpers as ws_helpers
from web.deps import ProjectSession, RequireProjectDep, coerce_project_session
from web.security import ALLOW_RUNTIME_INSTALL_ENV, validate_outbound_model_base_url
from web.model_library import ModelLibrary

ws_server._mask_config_secrets = ws_helpers._mask_config_secrets
ws_server._effective_pipeline_settings = ws_helpers._effective_pipeline_settings
ws_server._merge_preserving_masked_secrets = ws_helpers._merge_preserving_masked_secrets
ws_server._write_yaml = ws_helpers._write_yaml
ws_server._validate_id = ws_helpers._validate_id
ws_server.ModelLibrary = ModelLibrary
from web.models import (
    ConfigUpdate,
    ModelSaveRequest,
    ModelSlotRequest,
    ModelTestRequest,
)
from novel_agent.pipeline import (
    GLOBAL_SHARED_SECTIONS,
    load_global_pipeline_file,
    load_pipeline_settings,
    load_project_pipeline_file,
    resolve_global_config_dir,
    write_pipeline_file,
)

router = APIRouter()


def _validated_model_base_url(raw_url: str) -> str:
    try:
        return validate_outbound_model_base_url(raw_url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _cleanup_llm_flat_keys(llm: Dict[str, Any]) -> None:
    if "default" in llm:
        for key in ("provider", "base_url", "api_key", "model", "max_tokens", "temperature"):
            llm.pop(key, None)


def _merge_preserving_secrets_section(
    current: Dict[str, Any], patch: Dict[str, Any]
) -> Dict[str, Any]:
    return ws_server._merge_preserving_masked_secrets(current, patch)


def _save_global_model_sections(
    global_dir: Path, *, llm: Any = None, embedding: Any = None
) -> None:
    path = global_dir / "pipeline.yaml"
    on_disk = load_global_pipeline_file(global_dir)
    if llm is not None:
        on_disk["llm"] = _merge_preserving_secrets_section(on_disk.get("llm", {}), llm)
        _cleanup_llm_flat_keys(on_disk["llm"])
    if embedding is not None:
        on_disk["embedding"] = _merge_preserving_secrets_section(
            on_disk.get("embedding", {}), embedding
        )
    write_pipeline_file(path, on_disk)


def _save_project_scoped_sections(
    root_dir: Path, *, runtime: Any = None, chapter: Any = None
) -> None:
    path = root_dir / "config" / "pipeline.yaml"
    on_disk = load_project_pipeline_file(root_dir)
    if runtime is not None:
        block = dict(on_disk.get("runtime", {}))
        block.update(runtime)
        on_disk["runtime"] = block
    if chapter is not None:
        block = dict(on_disk.get("chapter", {}))
        block.update(chapter)
        on_disk["chapter"] = block
    # Drop legacy per-book model copies so global settings always apply.
    for key in GLOBAL_SHARED_SECTIONS:
        on_disk.pop(key, None)
    write_pipeline_file(path, on_disk)


# ---- Config ----

@router.get("/api/config")
def get_config(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    return ws_server._mask_config_secrets(ws_server._effective_pipeline_settings(session.root_dir))


@router.put("/api/config")
def update_config(body: ConfigUpdate, session: ProjectSession = RequireProjectDep) -> Dict[str, str]:
    session = coerce_project_session(session)
    root_dir = session.root_dir
    global_dir = resolve_global_config_dir(root_dir)

    if global_dir:
        if body.llm is not None or body.embedding is not None:
            _save_global_model_sections(global_dir, llm=body.llm, embedding=body.embedding)
        if body.runtime is not None or body.chapter is not None:
            _save_project_scoped_sections(
                root_dir, runtime=body.runtime, chapter=body.chapter
            )
        return {"status": "updated"}

    current = load_pipeline_settings(root_dir)
    if body.llm is not None:
        current["llm"] = _merge_preserving_secrets_section(current.get("llm", {}), body.llm)
    if body.embedding is not None:
        current["embedding"] = _merge_preserving_secrets_section(
            current.get("embedding", {}), body.embedding
        )
    if body.runtime is not None:
        runtime = dict(current.get("runtime", {}))
        runtime.update(body.runtime)
        current["runtime"] = runtime
    if body.chapter is not None:
        chapter = dict(current.get("chapter", {}))
        chapter.update(body.chapter)
        current["chapter"] = chapter
    llm = current.get("llm", {})
    _cleanup_llm_flat_keys(llm)
    write_pipeline_file(root_dir / "config" / "pipeline.yaml", current)
    return {"status": "updated"}


@router.put("/api/config/global-defaults")
def update_global_defaults(body: ConfigUpdate) -> Dict[str, str]:
    global_dir = ws_server.BASE_DIR / "config"
    if body.llm is not None or body.embedding is not None:
        _save_global_model_sections(global_dir, llm=body.llm, embedding=body.embedding)
    if body.runtime is not None or body.chapter is not None:
        raise HTTPException(400, "runtime/chapter 请保存到当前书籍（PUT /api/config）。")
    return {"status": "updated"}


# ---- Models Library ----

@router.get("/api/models")
def list_models(session: ProjectSession = RequireProjectDep) -> List[Dict[str, Any]]:
    session = coerce_project_session(session)
    return ws_server.ModelLibrary(session.root_dir).list_models()


@router.get("/api/models/slots")
def get_model_slots(session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    return ws_server.ModelLibrary(session.root_dir).get_slots()


@router.patch("/api/models/{model_id}/slot")
def set_model_slot(
    model_id: str,
    body: ModelSlotRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    ws_server._validate_id(model_id, "model_id")
    return ws_server.ModelLibrary(session.root_dir).set_model_slot(model_id, body.slot)


@router.post("/api/models")
def save_model(req: ModelSaveRequest, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    data = req.model_dump()
    model_id = data.pop("id")
    return ws_server.ModelLibrary(session.root_dir).save_model(model_id, data)


@router.delete("/api/models/{model_id}")
def delete_model(model_id: str, session: ProjectSession = RequireProjectDep) -> Dict[str, str]:
    session = coerce_project_session(session)
    ws_server._validate_id(model_id, "model_id")
    ws_server.ModelLibrary(session.root_dir).delete_model(model_id)
    return {"status": "deleted"}


@router.post("/api/models/test")
def test_model(req: ModelTestRequest, session: ProjectSession = RequireProjectDep) -> Dict[str, Any]:
    session = coerce_project_session(session)
    config = req.model_dump()
    return ws_server.ModelLibrary(session.root_dir).test_model(config)


from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class ModelContextTestRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: Optional[str] = None
    provider: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 30
    proxy: str = ""
    type: str = "text"
    test_context_tokens: int = 16000

class EmbeddingTestRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: str = "stub"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    model_path: Optional[str] = None


@router.post("/api/models/test-context")
def test_model_context(
    req: ModelContextTestRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    config = req.model_dump()
    test_tokens = config.pop("test_context_tokens", 16000)
    return ws_server.ModelLibrary(session.root_dir).test_model(config, test_context_tokens=test_tokens)


@router.post("/api/config/embedding/test")
def test_embedding_config(
    req: EmbeddingTestRequest,
    session: ProjectSession = RequireProjectDep,
) -> Dict[str, Any]:
    session = coerce_project_session(session)
    root_dir = session.root_dir
    provider = req.provider
    
    if provider == "stub":
        try:
            import jieba
            list(jieba.cut("测试分词"))
            return {"success": True, "message": "Jieba 分词组件已就绪。词频 Stub 检索工作正常。"}
        except ImportError:
            return {"success": True, "message": "Jieba 未安装，将使用系统自带的正则表达式单字切分进行 Stub 检索。"}

    elif provider == "local":
        import importlib
        py_deps_dir = BASE_DIR / "data" / "py_deps"
        if str(py_deps_dir) not in sys.path:
            sys.path.insert(0, str(py_deps_dir))
        importlib.invalidate_caches()
        
        model_path = req.model_path or str(root_dir / "data" / "models" / "bge-micro-v2.onnx")
        
        try:
            import onnxruntime
        except ImportError:
            return {"success": False, "error": "本地 ONNX 推理引擎未安装，请在 Python 环境下安装 onnxruntime (例如 pip install onnxruntime)。"}
            
        try:
            import transformers
        except ImportError:
            return {"success": False, "error": "本地 Tokenizer 未安装，请在 Python 环境下安装 transformers (例如 pip install transformers)。"}
            
        import os
        if not os.path.exists(model_path):
            return {
                "success": False, 
                "error": f"找不到本地 ONNX 向量模型文件，预期路径为: {model_path}。请先下载模型文件并置于该位置。"
            }
            
        try:
            import onnxruntime as ort
            ort.InferenceSession(model_path)
            return {"success": True, "message": "本地 ONNX 向量模型校验成功！依赖组件与模型文件均已就绪。"}
        except Exception as e:
            return {"success": False, "error": f"本地 ONNX 向量模型加载失败: {str(e)}。请检查文件是否完整。"}
            
    else:
        import httpx
        api_key = req.api_key
        base_url = req.base_url
        model = req.model
        
        if not api_key:
            return {"success": False, "error": "在线向量检索需要配置 API Key。"}
            
        if provider == "zhipu":
            test_url = "https://open.bigmodel.cn/api/paas/v4/embeddings"
            test_key = api_key
            test_model = "text-embedding-3"
        elif provider in ("dashscope", "bailian"):
            root = (base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
            test_url = f"{_validated_model_base_url(root)}/embeddings"
            test_key = api_key
            test_model = model if model else "text-embedding-v3"
        else:  # openai
            root = _validated_model_base_url(base_url or "https://api.openai.com/v1")
            test_url = f"{root}/embeddings"
            test_key = api_key
            test_model = model if model else "text-embedding-3-small"
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {test_key}"
        }
        payload = {"model": test_model, "input": ["test"]}
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(test_url, headers=headers, json=payload)
                if resp.status_code == 200:
                    return {"success": True, "message": f"在线向量检索接口 ({provider}) 测试成功！通道已握手。"}
                
                try:
                    err_msg = resp.json().get("error", {}).get("message", resp.text)
                except Exception:
                    err_msg = resp.text
                return {"success": False, "error": f"HTTP {resp.status_code}: {err_msg}"}
        except Exception as e:
            return {"success": False, "error": f"在线向量接口连接失败: {str(e)}"}


# ---- Local Model Setup & Dependency Watchdog ----

import importlib.util
import hashlib
import json
import os
import sys
import subprocess
import threading
import httpx
from pathlib import Path
from web.context import BASE_DIR

MODEL_SHA256_ENV = "NOVEL_AGENT_MODEL_SHA256_JSON"
MAX_MODEL_FILE_BYTES = 256 * 1024 * 1024
MODEL_FILES = (
    "bge-micro-v2.onnx",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
)

setup_lock = threading.Lock()
setup_state = {
    "status": "idle",
    "step": "",
    "progress": 0,
    "message": "",
    "error": None
}

def run_pip_install(args: list) -> None:
    import sys
    import subprocess

    # Use only the current interpreter; never fall back to PATH python/pip.
    cmd = [sys.executable, "-m", "pip", "install"] + args
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            timeout=300,
        )
        if res.returncode == 0:
            return
        raise RuntimeError(
            f"pip install failed with code {res.returncode}. stderr: {res.stderr.strip()}"
        )
    except Exception as e:
        raise RuntimeError(f"Unable to run pip install with the current interpreter: {str(e)}")


def _load_model_sha256() -> Dict[str, str]:
    raw = os.environ.get(MODEL_SHA256_ENV, "")
    if raw:
        source = f"${MODEL_SHA256_ENV}"
    else:
        manifest_path = BASE_DIR / "config" / "model_hashes.json"
        if not manifest_path.exists():
            raise RuntimeError(
                f"Missing model SHA-256 manifest: {manifest_path}. "
                f"Create it or set {MODEL_SHA256_ENV} before automatic model installation."
            )
        source = str(manifest_path)
        raw = manifest_path.read_text(encoding="utf-8")

    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid model SHA-256 manifest {source}: {exc}") from exc

    hashes = manifest.get("files", manifest)
    result: Dict[str, str] = {}
    for filename in MODEL_FILES:
        digest = str(hashes.get(filename, "")).lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise RuntimeError(f"Missing or invalid SHA-256 for {filename} in {source}")
        result[filename] = digest
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bg_setup_local(root_dir: Path):
    global setup_state
    
    with setup_lock:
        setup_state["status"] = "running"
        setup_state["step"] = "installing_deps"
        setup_state["progress"] = 5
        setup_state["message"] = "正在准备环境，开始安装 Python 依赖库..."
        setup_state["error"] = None
        
    py_deps_dir = BASE_DIR / "data" / "py_deps"
    py_deps_dir.mkdir(parents=True, exist_ok=True)

    try:
        model_sha256 = _load_model_sha256()
    except Exception as e:
        with setup_lock:
            setup_state["status"] = "failed"
            setup_state["error"] = str(e)
            setup_state["message"] = "模型完整性清单不可用，已停止自动安装。"
        return
    
    try:
        if str(py_deps_dir) not in sys.path:
            sys.path.insert(0, str(py_deps_dir))
            
        importlib.invalidate_caches()
        has_onnx = importlib.util.find_spec("onnxruntime") is not None
        has_transformers = importlib.util.find_spec("transformers") is not None
    except Exception:
        has_onnx = False
        has_transformers = False
        
    if not (has_onnx and has_transformers):
        try:
            cmd_args = [
                "onnxruntime==1.17.3", "transformers==4.46.3",
                "-t", str(py_deps_dir), 
                "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
            ]
            
            with setup_lock:
                setup_state["progress"] = 10
                setup_state["message"] = "正在安装 onnxruntime 和 transformers 依赖，约需 1-2 分钟..."
                
            # Run pip install safely with fallback routes
            run_pip_install(cmd_args)
            importlib.invalidate_caches()
            
        except Exception as e:
            with setup_lock:
                setup_state["status"] = "failed"
                setup_state["error"] = f"依赖库安装失败: {str(e)}"
                setup_state["message"] = "依赖库安装异常中止。"
            return
            
    with setup_lock:
        setup_state["step"] = "downloading_model"
        setup_state["progress"] = 50
        setup_state["message"] = "环境库就绪！开始下载 BGE 向量模型..."
        
    model_dir = BASE_DIR / "data" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    MODEL_URLS = {
        "bge-micro-v2.onnx": "https://hf-mirror.com/Xenova/bge-micro-v2/resolve/main/onnx/model_quantized.onnx",
        "tokenizer.json": "https://hf-mirror.com/Xenova/bge-micro-v2/resolve/main/tokenizer.json",
        "tokenizer_config.json": "https://hf-mirror.com/Xenova/bge-micro-v2/resolve/main/tokenizer_config.json",
        "special_tokens_map.json": "https://hf-mirror.com/Xenova/bge-micro-v2/resolve/main/special_tokens_map.json",
        "vocab.txt": "https://hf-mirror.com/Xenova/bge-micro-v2/resolve/main/vocab.txt",
    }
    
    MODEL_FALLBACKS = {
        "bge-micro-v2.onnx": "https://huggingface.co/Xenova/bge-micro-v2/resolve/main/onnx/model_quantized.onnx",
        "tokenizer.json": "https://huggingface.co/Xenova/bge-micro-v2/resolve/main/tokenizer.json",
        "tokenizer_config.json": "https://huggingface.co/Xenova/bge-micro-v2/resolve/main/tokenizer_config.json",
        "special_tokens_map.json": "https://huggingface.co/Xenova/bge-micro-v2/resolve/main/special_tokens_map.json",
        "vocab.txt": "https://huggingface.co/Xenova/bge-micro-v2/resolve/main/vocab.txt",
    }
    
    total_files = len(MODEL_URLS)
    for idx, (filename, url) in enumerate(MODEL_URLS.items()):
        dest_path = model_dir / filename
        
        if dest_path.exists() and _sha256_file(dest_path) == model_sha256[filename]:
            with setup_lock:
                setup_state["progress"] = int(50 + ((idx + 1) / total_files) * 50)
                setup_state["message"] = f"文件 {filename} 已存在，跳过下载"
            continue
            
        try:
            progress_start = 50 + (idx / total_files) * 50
            progress_end = 50 + ((idx + 1) / total_files) * 50
            
            temp_path = dest_path.with_suffix(".tmp")
            
            try:
                _do_stream_download(url, temp_path, progress_start, progress_end, model_sha256[filename])
            except Exception as e:
                fallback_url = MODEL_FALLBACKS[filename]
                _do_stream_download(fallback_url, temp_path, progress_start, progress_end, model_sha256[filename])
                
            if temp_path.exists():
                if dest_path.exists():
                    dest_path.unlink()
                temp_path.rename(dest_path)
                
        except Exception as e:
            with setup_lock:
                setup_state["status"] = "failed"
                setup_state["error"] = f"下载文件 {filename} 失败: {str(e)}"
                setup_state["message"] = "向量模型下载异常中止。"
            return
            
    # Auto configure embedding provider to "local"
    try:
        from novel_agent.pipeline import load_pipeline_settings
        import yaml
        
        embedding_cfg = {
            "provider": "local",
            "model_path": str(model_dir / "bge-micro-v2.onnx"),
        }
        global_dir = resolve_global_config_dir(root_dir)
        if global_dir:
            _save_global_model_sections(global_dir, embedding=embedding_cfg)
        else:
            current = load_pipeline_settings(root_dir)
            current["embedding"] = _merge_preserving_secrets_section(
                current.get("embedding", {}), embedding_cfg
            )
            write_pipeline_file(root_dir / "config" / "pipeline.yaml", current)
        
    except Exception:
        pass
        
    with setup_lock:
        setup_state["status"] = "completed"
        setup_state["step"] = "finished"
        setup_state["progress"] = 100
        setup_state["message"] = "本地依赖与向量模型全部配置成功！系统已自动切换为本地嵌入检索。"

def _do_stream_download(url: str, temp_path: Path, p_start: float, p_end: float, expected_sha256: str):
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    try:
        with httpx.Client(follow_redirects=True, timeout=60.0) as client:
            with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"HTTP {response.status_code}")

                total_size = int(response.headers.get("content-length", 0))
                if total_size > MAX_MODEL_FILE_BYTES:
                    raise RuntimeError("Model file exceeds the size limit")
                downloaded = 0

                with open(temp_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=16384):
                        if chunk:
                            downloaded += len(chunk)
                            if downloaded > MAX_MODEL_FILE_BYTES:
                                raise RuntimeError("Model file exceeds the size limit")
                            digest.update(chunk)
                            f.write(chunk)
                            if total_size > 0:
                                ratio = downloaded / total_size
                                curr = p_start + ratio * (p_end - p_start)
                                with setup_lock:
                                    setup_state["progress"] = int(curr)
                                    setup_state["message"] = f"正在下载 {temp_path.name.replace('.tmp', '')} ({int(ratio*100)}%)"
        if digest.hexdigest() != expected_sha256:
            raise RuntimeError("Downloaded model file SHA-256 mismatch")
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


@router.get("/api/config/embedding/status")
def get_embedding_status(session: ProjectSession = RequireProjectDep):
    session = coerce_project_session(session)
    import importlib.util
    
    py_deps_dir = BASE_DIR / "data" / "py_deps"
    if str(py_deps_dir) not in sys.path:
        sys.path.insert(0, str(py_deps_dir))
        
    importlib.invalidate_caches()
    has_onnx = importlib.util.find_spec("onnxruntime") is not None
    has_transformers = importlib.util.find_spec("transformers") is not None
    
    model_dir = BASE_DIR / "data" / "models"
    model_file = model_dir / "bge-micro-v2.onnx"
    has_model = model_file.exists() and model_file.stat().st_size > 0
    
    has_tokenizer = all(
        (model_dir / f).exists() and (model_dir / f).stat().st_size > 0 
        for f in ["tokenizer.json", "tokenizer_config.json", "vocab.txt"]
    )
    
    from novel_agent.pipeline import load_pipeline_settings
    from novel_agent.control.scale_profile import is_vector_enabled_for_project
    from novel_agent.control.runtime_policy import is_semantic_search_effective, resolve_runtime_policy

    root_dir = session.root_dir
    current = load_pipeline_settings(root_dir)
    provider = current.get("embedding", {}).get("provider", "stub")
    vector_enabled = is_vector_enabled_for_project(root_dir)
    semantic_ok = is_semantic_search_effective(root_dir)
    policy = resolve_runtime_policy(root_dir)
    scale = str(policy.scale or "medium")
    long_form = scale in ("long", "epic", "infinite")

    return {
        "has_onnx": has_onnx,
        "has_transformers": has_transformers,
        "has_model": has_model and has_tokenizer,
        "provider": provider,
        "model_path": str(model_file) if (has_model and has_tokenizer) else None,
        "vector_enabled": vector_enabled,
        "semantic_search_effective": semantic_ok,
        "work_scale": scale,
        "pipeline_tier": policy.pipeline_tier,
        "audit_profile": policy.audit_profile,
        "long_form_vector_recommended": long_form and vector_enabled and not semantic_ok,
    }


@router.post("/api/config/embedding/rebuild-index")
def rebuild_embedding_index(session: ProjectSession = RequireProjectDep):
    session = coerce_project_session(session)
    """Rebuild HNSW indices from SQLite vector_embeddings (long-run maintenance)."""
    from novel_agent.pipeline import PipelineConfig
    from novel_agent.orchestrator import NovelOrchestrator

    root_dir = session.root_dir
    config = PipelineConfig.from_config(root_dir)
    orchestrator = NovelOrchestrator(config)
    store = orchestrator.vector_store
    if not hasattr(store, "rebuild_hnsw_indices"):
        raise HTTPException(400, "当前向量后端不支持 HNSW 重建")
    counts = store.rebuild_hnsw_indices()
    return {"status": "ok", "dimensions": counts}


@router.post("/api/config/embedding/setup-local")
def post_setup_local(session: ProjectSession = RequireProjectDep):
    session = coerce_project_session(session)
    global setup_state
    if os.environ.get(ALLOW_RUNTIME_INSTALL_ENV, "").lower() not in ("1", "true", "yes"):
        raise HTTPException(
            403,
            f"Runtime dependency installation is disabled. Set {ALLOW_RUNTIME_INSTALL_ENV}=1 to enable it.",
        )
    with setup_lock:
        if setup_state["status"] == "running":
            return {"status": "already_running"}
        setup_state["status"] = "running"
        setup_state["step"] = "queued"
        setup_state["progress"] = 0
        setup_state["message"] = "正在启动本地模型部署..."
        setup_state["error"] = None

    root_dir = session.root_dir
    thread = threading.Thread(target=bg_setup_local, args=(root_dir,), daemon=True)
    try:
        thread.start()
    except Exception as exc:
        with setup_lock:
            setup_state["status"] = "failed"
            setup_state["error"] = str(exc)
            setup_state["message"] = "本地模型部署线程启动失败。"
        raise HTTPException(500, "Failed to start local model setup")
    return {"status": "started"}


@router.get("/api/config/embedding/setup-status")
def get_setup_status():
    with setup_lock:
        return setup_state
