"""JSON-RPC 2.0 message framing and protocol serialization."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Union

# Standard JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Application-specific error codes
TIMEOUT_ERROR = -32000
CIRCUIT_OPEN_ERROR = -32001
PLUGIN_CRASH_ERROR = -32002


@dataclass
class RPCError(Exception):
    code: int
    message: str
    data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            d["data"] = self.data
        return d

    def __str__(self) -> str:
        return f"RPCError({self.code}): {self.message}"


@dataclass
class RPCRequest:
    id: Union[str, int]
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
        }
        if self.params is not None:
            d["params"] = self.params
        return d


@dataclass
class RPCResponse:
    id: Union[str, int]
    result: Optional[Any] = None
    error: Optional[RPCError] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            d["error"] = self.error.to_dict()
        else:
            d["result"] = self.result
        return d


@dataclass
class RPCNotification:
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            d["params"] = self.params
        return d


def encode_message(msg: Union[RPCRequest, RPCResponse, RPCNotification]) -> str:
    """Serialize an RPC message to JSON string."""
    return json.dumps(msg.to_dict(), ensure_ascii=False)


def decode_message(raw: Union[str, bytes, Dict[str, Any]]) -> Dict[str, Any]:
    """Parse raw JSON string or dict into an RPC message payload."""
    if isinstance(raw, (str, bytes)):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RPCError(code=PARSE_ERROR, message=f"Parse error: {exc}") from exc
    else:
        payload = raw

    if not isinstance(payload, dict):
        raise RPCError(code=INVALID_REQUEST, message="Invalid Request: payload must be a JSON object")

    if payload.get("jsonrpc") != "2.0":
        raise RPCError(code=INVALID_REQUEST, message="Invalid Request: 'jsonrpc' must be '2.0'")

    return payload
