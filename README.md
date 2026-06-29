# 🛜 网络恢复工具 Network Recovery Tool

一键执行 Windows 网络重置命令的图形化工具。

## 使用

1. 下载 `NetworkRecoveryTool.exe`
2. 右键 → **以管理员身份运行**
3. 勾选需要执行的命令，点击「执行选中命令」
4. 根据提示重启电脑

## 包含命令

- `ipconfig /flushdns` — 刷新 DNS 缓存
- `ipconfig /release` — 释放 IP 地址
- `ipconfig /renew` — 重新获取 IP
- `netsh winsock reset` — 重置 Winsock
- `netsh int ip reset` — 重置 TCP/IP 协议栈
