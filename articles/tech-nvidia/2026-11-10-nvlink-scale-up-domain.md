---
title: NVLink 的 scale-up 域：为什么 72 张卡要先当成一台机器
date: 2026-11-10
series: tech-nvidia
author: Guangyi Zhao
---

做数据中心基础设施这些年，我越来越觉得，理解 Blackwell 这一代平台的第一把钥匙不是 GPU 本身，而是 NVLink 域（NVLink domain）这个概念：一组 GPU 之间用 NVLink 全互联、彼此以接近显存语义的速度通信，这个集合的边界，就是系统设计的边界。域内是「一台机器」，域外是「一个集群」，两边的性能特征完全不在一个量级。

## 一、先把数字摆正：三代 NVLink 的官方规格

NVIDIA 官方 NVLink 页面给的代际表很干净：

| 代 | 平台 | 单 GPU 带宽（双向） | 域内 GPU 数 | 聚合带宽 |
|---|---|---|---|---|
| NVLink 4 / NVSwitch 4 | Hopper | 900 GB/s | 8 | 7.2 TB/s |
| NVLink 5 / NVSwitch 5 | Blackwell | 1,800 GB/s | 8 / 72 | 130 TB/s（NVL72） |
| NVLink 6 / NVSwitch 6 | Vera Rubin | 3,000 GB/s | 8 / 72 | 216 TB/s（NVL72） |

注意官方带宽是双向合计口径。第五代每张 GPU 有 18 条 NVLink 链路，单向 900 GB/s、双向合计 1.8 TB/s。72 张卡乘起来就是那句到处被引用的「130 TB/s 全互联」。第六代单 GPU 升到 3 TB/s，是 PCIe Gen6 的 12 倍。

## 二、NVSwitch 干的活：把点对点连成全互联

NVLink 本身是点对点链路。靠链路直连，8 张卡还能勉强全连接，72 张卡在物理上不可能。NVSwitch 就是那颗交换芯片：GB300 NVL72 里有 9 个 NVLink 交换托盘，每托盘 2 颗第五代 NVSwitch 芯片，18 颗交换芯片把 72 张 GPU 的每一条链路都接进来，实现任意两卡之间全速 all-to-all。

还有一个容易被忽略的点：NVSwitch 里内置了 SHARP 引擎（Scalable Hierarchical Aggregation and Reduction Protocol），把集合通信里的归约运算下放到交换芯片里在网完成。对训练来说，all-reduce 是每一步都要过的关，把它放进网络里做，省下的是 GPU 的显存带宽和计算周期。第六代 NVSwitch 还补了三件运维向的能力：控制面韧性、机柜部分填充也能运行、交换托盘热插拔——这些对可用性是实打实的改进，不再是「一颗交换芯片挂了整柜歇着」。

## 三、为什么 MoE 和推理把域推大

域从 8 张涨到 72 张，直接驱动力是负载形态变了。MoE（混合专家）模型的每一次前向都要做专家路由，token 被分发到不同 GPU 上的专家再收回来，这是典型的 all-to-all 通信，通信量随专家并行度放大。域越大、带宽越高，能摊开的专家并行就越大，单卡显存里要塞的东西就越少。

推理侧也一样：长上下文把 KV 缓存撑得很大，注意力计算需要在大域内分片；官方在 GB300 页给的口径里，Dynamo 分离式部署加 FP4，整柜 72 卡作为一个域对外服务，本质上是把「一台大推理机」卖给你。张量并行这类通信密集的切分方式，只能放在域内做；跨出机柜走 InfiniBand 或以太网，单链路带宽立刻掉一个量级，并行策略就得换一套——这是做集群规划时第一个要定的边界。

## 四、域的边界决定基础设施的边界

从基建视角看，NVLink 域有三条硬约束：

第一，**铜的距离**。域内全互联靠机柜内的铜缆/背板实现，物理上锁死在一个机柜里。这也是机柜功率密度被推到 130 kW 量级的根本原因之一：不是 NVIDIA 想把柜子做热，是互联的物理距离只允许把卡 pack 得这么紧。官方在 800 VDC 那篇博客里把这件事说得很直白——铜缆有效距离有限，形成「性能-密度陷阱」。

第二，**代际锁定**。NVLink 代际之间不互通，交换托盘和计算托盘都绑定 GPU 世代。扩容规划里不存在「先买半柜、明年混插新一代」，升级等于整域换代。做资产生命周期测算时必须按整柜、整代算。

第三，**域外是另一张网**。跨柜 scale-out 走 Quantum-X800 InfiniBand 或 Spectrum-X 以太网，GB300 每 GPU 的网络带宽是 ConnectX-8 给的 800 Gb/s。集群设计里，域内 1.8 TB/s 和域外 800 Gb/s（即 100 GB/s）之间差了 18 倍，并行策略、检查点、数据加载全都要按这个落差来设计。

## 五、往下看一代

第六代 NVLink 把单 GPU 带宽推到 3 TB/s、整柜 216 TB/s，域规模维持 72。再往外，NVIDIA 已经摆了两张牌：NVLink Fusion 把 NVLink 开放给半定制 ASIC 和 CPU 做混合基础设施；更大的域（NVL144 等形态）出现在其机架路线图里。方向很清楚：scale-up 域还会继续变大，机柜作为「一台机器」的语义只会更强。对做基础设施的人来说，规划单位早就不该是服务器，而是域。

## 来源

- NVIDIA NVLink & NVLink Switch 官方页（代际规格表、SHARP、NVLink 6 韧性特性、NVLink Fusion）：https://www.nvidia.com/en-us/data-center/nvlink/
- NVIDIA GB300 NVL72 产品页（NVLink 130 TB/s、ConnectX-8 800 Gb/s/卡、Quantum-X800/Spectrum-X）：https://www.nvidia.com/en-us/data-center/gb300-nvl72/
- NVIDIA Technical Blog《Building the 800 VDC Ecosystem for Efficient, Scalable AI Factories》（铜缆距离与性能-密度关系）：https://developer.nvidia.com/blog/building-the-800-vdc-ecosystem-for-efficient-scalable-ai-factories
- NVIDIA Vera Rubin NVL72 产品页（NVLink 6：216 TB/s 整柜、3 TB/s 单 GPU、NVLink-C2C 65 TB/s）：https://www.nvidia.com/en-us/data-center/vera-rubin-nvl72/

> 说明：本文为本人独立撰写，只使用公开资料，不涉及任何雇主或客户信息；文中性能数字均为厂商公开口径。
