#!/usr/bin/env python3
"""启动 cloudflared 并捕获 URL"""
import subprocess
import sys
import time
import re
from pathlib import Path

project_dir = Path("/mnt/c/Users/rober/Desktop/LINE群組羽球報名系統")
cloudflared = project_dir / "tools" / "cloudflared"

print("=" * 60)
print("🚀 启动 Cloudflared Tunnel...")
print("=" * 60)
print()

# 启动 cloudflared
proc = subprocess.Popen(
    [str(cloudflared), "tunnel", "--url", "http://localhost:8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=str(project_dir)
)

print("⏳ 正在启动，请稍候...")
print()

# 读取输出
url_pattern = re.compile(r'URL:\s*(https://[^\s]+)')
urls = []

for i in range(30):  # 最多等待30秒
    line = proc.stdout.readline()
    if not line:
        break
    
    print(line.rstrip())
    
    # 查找 URL
    match = url_pattern.search(line)
    if match:
        urls.append(match.group(1))
    
    # 如果找到 URL，继续读取几行确认
    if urls:
        time.sleep(1)
        for _ in range(3):
            extra = proc.stdout.readline()
            if extra:
                print(extra.rstrip())
            if 'ERROR' in extra.upper():
                print("\n⚠️  检测到错误，但已获取 URL")
                break
        break

print()
print("=" * 60)
print("📋 结果")
print("=" * 60)

if urls:
    print(f"\n✅ 成功获取 {len(urls)} 个 URL:\n")
    for url in urls:
        print(f"   {url}")
    print(f"\n   请复制以上 URL 到 LINE Developers Console:")
    print(f"   {urls[0]}/webhook/line")
else:
    print("\n❌ 未找到 URL")
    print("\n请查看上方输出，寻找类似 'URL: https://xxx.trycloudflare.com' 的行")

print()
print("💡 提示：cloudflared 正在运行中...")
print("   请保持在另一个终端窗口查看实时输出")
print("   按 Ctrl+C 可停止隧道")
print("=" * 60)

# 保持进程运行
try:
    proc.wait()
except KeyboardInterrupt:
    print("\n🛑 手动停止")
    proc.terminate()
