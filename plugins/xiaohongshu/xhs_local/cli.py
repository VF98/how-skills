import argparse
import json
from pathlib import Path
import sys

from .app import App, TOOLS
from .errors import XHSError
from . import __version__


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def mcp(app, source=None, sink=None):
    source, sink = source or sys.stdin, sink or sys.stdout
    for line in source:
        response = None
        try:
            if len(line) > 2 * 1024 * 1024:
                raise XHSError("message_limit", "MCP 请求过大")
            request = json.loads(line)
            if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                raise ValueError("Invalid JSON-RPC request")
            if "id" not in request:
                continue
            response = {"jsonrpc": "2.0", "id": request["id"]}
            method = request.get("method")
            if method == "initialize":
                requested = (request.get("params") or {}).get("protocolVersion")
                accepted = {"2024-11-05", "2025-03-26", "2025-06-18"}
                response["result"] = {"protocolVersion": requested if requested in accepted else "2025-06-18",
                                      "capabilities": {"tools": {"listChanged": False}},
                                      "serverInfo": {"name": "xiaohongshu-local", "version": __version__}}
            elif method == "ping":
                response["result"] = {}
            elif method == "tools/list":
                response["result"] = {"tools": TOOLS}
            elif method == "tools/call":
                params = request.get("params") or {}
                try:
                    value = app.run_tool(params.get("name"), params.get("arguments", {}))
                    result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
                              "structuredContent": value}
                except XHSError as exc:
                    result = {"isError": True, "content": [{"type": "text", "text": json.dumps(exc.as_dict(), ensure_ascii=False)}]}
                response["result"] = result
            else:
                response["error"] = {"code": -32601, "message": "Method not found"}
        except (ValueError, TypeError, KeyError, AttributeError, XHSError):
            response = {"jsonrpc": "2.0", "id": response.get("id") if response else None,
                        "error": {"code": -32600, "message": "Invalid request"}}
        except Exception:
            response = {"jsonrpc": "2.0", "id": response.get("id") if response else None,
                        "error": {"code": -32603, "message": "Local operation failed; no automatic account write retry"}}
        if response is not None:
            sink.write(json.dumps(response, ensure_ascii=False) + "\n")
            sink.flush()


def main():
    parser = argparse.ArgumentParser(description="本机小红书读取与本地文稿 MVP；无发布能力")
    parser.add_argument("--data-dir", help="插件独立数据目录；默认位于工作目录内")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("mcp")
    sub.add_parser("tools")
    sub.add_parser("account-instructions")
    sub.add_parser("creator-inspect")
    bind = sub.add_parser("native-bind", help="绑定已有官方首页锚点和同一窗口的非活动工作标签；不创建权限")
    bind.add_argument("--anchor-tab-id", required=True)
    bind.add_argument("--work-tab-id", required=True)
    bind.add_argument("--creator-tab-id")
    inspect = sub.add_parser("creator-form", help="后台只读检查已审查的官方创作界面；不上传或保存")
    inspect.add_argument("url")
    enable = sub.add_parser("account-enable")
    enable.add_argument("--confirm-persistent-account", action="store_true", required=True)
    search = sub.add_parser("search")
    search.add_argument("keyword")
    search.add_argument("--limit", type=int, default=10)
    read = sub.add_parser("read")
    read.add_argument("url")
    create = sub.add_parser("manuscript-create")
    create.add_argument("json_file", help="包含 title/content/tags/images 的 UTF-8 JSON，或 - 读取 stdin")
    update = sub.add_parser("manuscript-update")
    update.add_argument("manuscript_id")
    update.add_argument("--expected-revision", type=int, required=True)
    update.add_argument("--patch-file", required=True)
    for command in ["manuscript-get", "manuscript-preview"]:
        p = sub.add_parser(command)
        p.add_argument("manuscript_id")
        p.add_argument("--revision", type=int)
    sub.add_parser("platform-draft-status")
    pb = sub.add_parser("platform-bind", help="绑定已有官方创作页，供上传和草稿编辑")
    pb.add_argument("--window-id", required=True)
    pb.add_argument("--tab-id", required=True)
    pi = sub.add_parser("platform-inspect", help="只读核对当前创作页及同步日志")
    pi.add_argument("--manuscript-id")
    ps = sub.add_parser("platform-sync", help="上传已授权文稿图片、保存并重开同一平台草稿；不发布")
    ps.add_argument("manuscript_id")
    ps.add_argument("--expected-revision", type=int, required=True)
    pr = sub.add_parser("platform-reopen", help="按已保存原生ID重开核对")
    pr.add_argument("manuscript_id")
    pc = sub.add_parser("platform-reconcile", help="只读匹配未完成操作后继续保存，不重复上传")
    pc.add_argument("manuscript_id")
    pc.add_argument("--expected-revision", type=int, required=True)
    iso = sub.add_parser("isolated-status", help="专用无界面浏览器状态及官方登录码；不使用桌面 Chrome")
    iso.add_argument("--capture-login", action="store_true")
    args = parser.parse_args()
    try:
        app = App(args.data_dir)
        if args.command == "mcp":
            return mcp(app)
        if args.command == "tools":
            return emit({"tools": TOOLS})
        if args.command == "account-instructions":
            return emit(app.account_instructions())
        if args.command == "native-bind":
            return emit(app.bind_native(args.anchor_tab_id, args.work_tab_id, args.creator_tab_id))
        if args.command == "creator-form":
            return emit(app.inspect_creator_form(args.url))
        if args.command == "account-enable":
            return emit(app.confirm_account(args.confirm_persistent_account))
        if args.command == "doctor":
            result = app.doctor()
        elif args.command == "search":
            result = app.run_tool("xhs_search", {"keyword": args.keyword, "limit": args.limit})
        elif args.command == "read":
            result = app.run_tool("xhs_read_note", {"url": args.url})
        elif args.command == "platform-draft-status":
            result = app.run_tool("xhs_platform_draft_status", {})
        elif args.command == "platform-bind":
            result = app.run_tool("xhs_platform_draft_bind", {"window_id":args.window_id,"tab_id":args.tab_id})
        elif args.command == "platform-inspect":
            result = app.run_tool("xhs_platform_draft_inspect", {"manuscript_id":args.manuscript_id} if args.manuscript_id else {})
        elif args.command == "platform-sync":
            result = app.run_tool("xhs_platform_draft_sync", {"manuscript_id":args.manuscript_id,"expected_revision":args.expected_revision})
        elif args.command == "platform-reopen":
            result = app.run_tool("xhs_platform_draft_reopen", {"manuscript_id":args.manuscript_id})
        elif args.command == "platform-reconcile":
            result = app.run_tool("xhs_platform_draft_reconcile", {"manuscript_id":args.manuscript_id,"expected_revision":args.expected_revision})
        elif args.command == "isolated-status":
            result = app.run_tool("xhs_isolated_status", {"capture_login":args.capture_login})
        elif args.command == "creator-inspect":
            result = app.run_tool("xhs_creator_inspect", {})
        elif args.command == "manuscript-create":
            data = sys.stdin.read() if args.json_file == "-" else Path(args.json_file).read_text()
            result = app.run_tool("xhs_local_manuscript_create", {"payload": json.loads(data)})
        elif args.command == "manuscript-update":
            data = sys.stdin.read() if args.patch_file == "-" else Path(args.patch_file).read_text()
            result = app.run_tool("xhs_local_manuscript_update", {
                "manuscript_id": args.manuscript_id, "expected_revision": args.expected_revision, "patch": json.loads(data)})
        else:
            values = {"manuscript_id": args.manuscript_id}
            if args.revision is not None:
                values["revision"] = args.revision
            tool = "xhs_local_manuscript_get" if args.command == "manuscript-get" else "xhs_local_manuscript_preview"
            result = app.run_tool(tool, values)
        emit(result)
    except XHSError as exc:
        emit(exc.as_dict())
        return 2
    except (ValueError, OSError):
        emit({"ok": False, "error": "local_input_error", "message": "本地输入文件、JSON或存储无效"})
        return 2


if __name__ == "__main__":
    sys.exit(main())
