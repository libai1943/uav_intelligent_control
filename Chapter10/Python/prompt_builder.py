#!/usr/bin/env python3
"""第10章：离线生成完整提示词。仅拼接文本，不联网、不调用模型、不控制设备。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
DEMO_REQUEST = "三个仓库都看一下，先去东库，然后北库，最后西库。今天不开放的就跳过，拍普通照片。"
MAX_INPUT_CHARS = 6000


def read_utf8(path: Path) -> str:
    """兼容带或不带UTF-8 BOM的文本。"""
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"无法读取UTF-8文件：{path}。{exc}") from exc


def build_prompt(user_text: str, context_text: Optional[str] = None) -> str:
    """把规则、已核对资料、用户原话和输出约定组织为一个独立消息。"""
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("请输入非空的任务要求。")
    if len(user_text) > MAX_INPUT_CHARS:
        raise ValueError(f"本教学工具最多接受{MAX_INPUT_CHARS}个字符。")
    template = read_utf8(ROOT / "assets" / "prompt_template.txt")
    context = context_text if context_text is not None else read_utf8(ROOT / "assets" / "context_demo.txt")
    if not isinstance(context, str) or not context.strip():
        raise ValueError("场景资料不能为空。")
    # 资料由教师/应用维护；不让原话改变模板的结构或执行代码。
    # JSON转义仅明确文本边界，不构成对提示注入的安全保证。
    for marker in ("{{CONTEXT}}", "{{USER_REQUEST_JSON}}"):
        if template.count(marker) != 1:
            raise ValueError(f"模板必须且只能含有一个占位符：{marker}")
    if "{{USER_REQUEST_JSON}}" in context:
        raise ValueError("场景资料含有保留的模板占位符，请先修正资料。")
    prompt = template.replace("{{CONTEXT}}", context.strip() + "\n")
    encoded = json.dumps(user_text.strip(), ensure_ascii=False)
    return prompt.replace("{{USER_REQUEST_JSON}}", encoded)


def save_prompt(prompt: str, path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(prompt, encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"无法保存提示词：{path}。{exc}") from exc


def launch_gui() -> None:
    """可选的本地输入窗口；没有桌面环境时可改用命令行。"""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext
        window = tk.Tk()
    except Exception as exc:
        raise ValueError("无法打开本地窗口。请在终端使用 --demo 或 --text。") from exc
    window.title("第10章 · 完整提示词生成器（离线）")
    window.geometry("980x760")
    window.minsize(760, 600)
    tk.Label(window, text="输入一句任务要求；程序仅生成文本，不联网，也不会执行巡检。",
             anchor="w").pack(fill="x", padx=14, pady=(12, 5))
    request_box = scrolledtext.ScrolledText(window, height=5, wrap="word", font=("TkDefaultFont", 11))
    request_box.pack(fill="x", padx=14)
    request_box.insert("1.0", DEMO_REQUEST)
    tk.Label(window, text="已核对场景资料（课堂示例，可编辑；不是实时数据）", anchor="w").pack(fill="x", padx=14, pady=(10, 4))
    context_box = scrolledtext.ScrolledText(window, height=7, wrap="word", font=("TkDefaultFont", 10))
    context_box.pack(fill="x", padx=14)
    context_box.insert("1.0", read_utf8(ROOT / "assets" / "context_demo.txt"))
    controls = tk.Frame(window)
    controls.pack(fill="x", padx=14, pady=8)
    result_box = scrolledtext.ScrolledText(window, wrap="word", font=("TkDefaultFont", 10))
    result_box.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    def generate() -> None:
        try:
            prompt = build_prompt(request_box.get("1.0", "end-1c"), context_box.get("1.0", "end-1c"))
            result_box.delete("1.0", "end")
            result_box.insert("1.0", prompt)
        except ValueError as exc:
            messagebox.showerror("输入检查", str(exc))

    def copy_result() -> None:
        text = result_box.get("1.0", "end-1c")
        if not text:
            messagebox.showinfo("尚无结果", "请先生成完整提示词。")
            return
        window.clipboard_clear()
        window.clipboard_append(text)
        window.update()
        messagebox.showinfo("已复制", "可自行粘贴到所选对话模型。请仅使用可公开的课堂数据。")

    def save_result() -> None:
        text = result_box.get("1.0", "end-1c")
        if not text:
            messagebox.showinfo("尚无结果", "请先生成完整提示词。")
            return
        name = filedialog.asksaveasfilename(initialfile="complete_prompt.txt", defaultextension=".txt",
                                           filetypes=[("UTF-8文本", "*.txt")])
        if name:
            try:
                save_prompt(text, Path(name))
            except ValueError as exc:
                messagebox.showerror("保存失败", str(exc))

    tk.Button(controls, text="生成完整提示词", command=generate).pack(side="left")
    tk.Button(controls, text="复制结果", command=copy_result).pack(side="left", padx=8)
    tk.Button(controls, text="保存文本", command=save_result).pack(side="left")
    generate()
    window.mainloop()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text", help="直接传入用户原话")
    group.add_argument("--demo", action="store_true", help="使用正文示例，不需要交互")
    group.add_argument("--gui", action="store_true", help="打开本地输入窗口")
    parser.add_argument("--context", type=Path, help="可选：教师维护的UTF-8场景资料")
    parser.add_argument("--out", type=Path, default=ROOT / "complete_prompt.txt", help="生成文件的位置")
    args = parser.parse_args(argv)
    try:
        if args.gui:
            if args.context:
                parser.error("--gui中可直接编辑场景资料；--context供命令行使用。")
            launch_gui()
            return 0
        if args.demo:
            request = DEMO_REQUEST
        elif args.text is not None:
            request = args.text
        elif sys.stdin.isatty():
            request = input("请输入任务要求（直接回车使用正文示例）：\n").strip() or DEMO_REQUEST
        else:
            parser.error("非交互运行请指定 --demo 或 --text。")
        context = read_utf8(args.context) if args.context else None
        prompt = build_prompt(request, context)
        save_prompt(prompt, args.out)
        print(prompt)
        print(f"\n已保存：{args.out.resolve()}\n本程序没有调用任何模型。", file=sys.stderr)
        return 0
    except (ValueError, EOFError, KeyboardInterrupt) as exc:
        print(f"未生成：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
