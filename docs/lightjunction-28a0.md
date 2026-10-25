# LIghtJUNction 的 RTX 4060 Laptop 实验版本

版本：`1.1.1.lj1`。分支：`lightjunction/ad107m-28a0`。

这份改动只开放 NVIDIA `10de:28a0`、子设备 `1d05:1274`、修订号 `a1`，并要求
GPU 的 `PMC_BOOT_0` 等于 `0x197000a1`。这些条件与本机 PCI 信息及公开的同板卡
实验记录一致，但不代表这份构建已经在本机启动成功。当前本机 NVIDIA 驱动为
`615.78.08`，内核为 `7.2.11-arch1-1`，VBIOS 为 `95.07.16.80.E1`。

## 改动来源

- 基于 [JustAResearcher/gpu-unlock-ada](https://github.com/JustAResearcher/gpu-unlock-ada)
  的 `4e7fefc`，保留原有许可证与固件来源。
- 引入 [abdecd 的 4060 Laptop 分支](https://github.com/abdecd/gpu-unlock-ada/tree/contrib/ad107-4060-laptop)
  中的 `3c4a233`，保留作者信息及其单独标注的测试证据。
- 参考 [buguj23 的 PR #31](https://github.com/JustAResearcher/gpu-unlock-ada/pull/31)
  核对设备分发、AD102 固件选择和数值验证要求。
- 参考 [woodsonl 的 PR #24](https://github.com/Zagitta/gpu-unlock/pull/24) 对固件选择
  分散的修复，以及 [jacksonfcs 的报告](https://github.com/Zagitta/gpu-unlock/issues/91)
  对独显空闲断电后失效的观察。
- 参考 [victorhramos-dev 的 PR #82](https://github.com/Zagitta/gpu-unlock/pull/82)
  对 `1d05:1274` 板卡和启动阶段的限制。该 PR 明确区分实验版本的硬件结果与
  尚未实际启动的提议版本。

## 这个版本新增了什么

1. 在枚举阶段检查子设备和修订号；其他笔记本即使也是 `28a0` 也不会被选中。
   直接调用解锁入口同样需要通过板卡检查。
2. 映射 BAR0 后先读取芯片标识；不匹配就退出，不进入显存布局、DMA 分配或
   固件执行阶段。
3. 用同一个 `gpu_unlock_uses_ad102()` 决定 Ada 固件与权限、速率读回的检查
   路径，避免更新一处设备表却漏掉另一处。
4. 默认关闭；必须同时给出 `ad107_experimental=1` 和一个完整 PCI 地址。
   `targets=all`、地址列表、重复地址、错误地址不能启用这块卡。
5. 提供只读的 `tools/check_28a0.py`。它检查驱动实际返回的速率，默认要求
   `fmla32`、`imla2`、`imla4` 都为全速；查询失败、半速或身份不符均返回失败。
   输出不包含 GPU UUID 或完整系统启动参数。
6. Arch 包构建使用 `make test-full`，要求完整的固定版本源码与生成固件，
   避免因为缺少输入而跳过完整事务检查。
7. Arch 包只安装模块、固件与独立镜像配置，不向普通镜像的配置目录写入
   自动加载规则。实验配置显式读取本机已有配置，再把解锁模块放到 NVIDIA 前。

保留原有固件 SHA-256、完成标记、权限、SEC2 停止、选择器读回、重置后状态及
失败时 DMA 内存保留检查。没有修改 VBIOS、提高功耗上限或在当前桌面会话中
卸载 NVIDIA 驱动。其他人的性能数据不属于本机的验收结果。

## 构建和检查

```sh
# 大文件可以放到空间充足的目录。
make assets CACHE=/var/tmp/gpu-unlock-lightjunction
make test-full CACHE=/var/tmp/gpu-unlock-lightjunction
make -C kernel/gpu_unlock -j2
python3 tools/print_boot_option.py --exact28a0
python3 tools/check_28a0.py --expect stock
```

`--expect stock` 要求三个目标字段都是 `1`，表示当前半速。它不是性能测试，
也不会上传固件、写寄存器、重置 GPU 或创建 CUDA 上下文。

`make arch` 从**已提交的 HEAD** 构建 Arch 安装包。固件在本机下载并核对哈希，
不会随这个源码仓库发布。单独验证内核模块构建不会安装或加载它。

## 在本机如何启用

使用一个单独的 Limine 启动项，以及为当前内核生成的独立 UKI（把内核、启动
参数和初始文件系统装在一起的启动文件）。保留普通启动项与原 UKI 的回退路径。
Arch 包提供 `/usr/share/doc/gpu-unlock/mkinitcpio-experimental.conf`，仅在生成
实验镜像时通过 `mkinitcpio -c` 指定它；安装包本身不会给普通镜像加入模块。
首次尝试先正常关机，再开机选择实验项；不要在 NVIDIA 已经占用显卡时手动
加载模块或尝试运行时解锁。

实验项的附加参数是：

```text
gpu_unlock.targets=0000:01:00.0 gpu_unlock.ad107_experimental=1 nvidia.NVreg_DynamicPowerManagement=0x00
```

其中 PCI 地址必须以本机检测结果为准。第三项关闭 NVIDIA 独显的运行时自动
断电，避免空闲后丢失解锁状态；可能增加待机耗电，只放在实验启动项中。
它不证明休眠、挂起恢复、驱动重新加载或长时间计算能够保持解锁。

进入实验项后执行：

```sh
journalctl -k -b --no-pager | rg 'gpu_unlock|AD107 board verified'
python3 tools/check_28a0.py
nvidia-smi
```

需要同时看到目标卡解锁成功、驱动健康与实际全速读回，随后再做数值验证和
同卡、同驱动、同功耗条件下的性能对照。测试程序通过或模块成功加载不能替代
这些实机检查；专项吞吐也不等于 AI 应用或游戏帧率的提升。

首次实验 UKI 绑定构建时的内核版本。更新内核后需要重新生成和检查实验项，
不要在依赖旧内核的实验项还在使用时删除旧内核。正式长期启用前应完成断电
启动、普通重启、空闲和实际工作负载验证。

## 撤回

选择原来的普通启动项，不传入 `gpu_unlock.*` 和实验项的独显断电参数。普通
启动不执行解锁。若固件事务失败且日志提示仍保留 DMA 缓冲区，应关机后再试，
不要强制卸载模块。

本次机器部署的备份与精确操作记录保存在本机 `$HOME/Backups/gpu-unlock-ada/`
下，原始启动配置和本机路径不提交到仓库。
