---
title: 从 CUDA Tile 到 Dynamo：英伟达推理软件栈在补哪一课
date: 2026-11-10
series: tech-nvidia
author: Guangyi Zhao
---

硬件这两年讲得够多了：NVL72、NVLink、FP4。但真把推理服务跑上生产的人都知道，最后决定每兆瓦能出多少 token 的，往往是软件栈。看 NVIDIA 最近一年的官方发布，软件侧有两步棋很值得拆：一是 CUDA 13.1 把编程模型从「线程」抬到「数据块」（CUDA Tile），二是 Dynamo 把推理从「单机引擎」抬到「分布式系统」（分离式服务加 KV 管理）。这两步补的是同一课：让硬件的账面能力更容易被普通团队兑现出来。

## 一、CUDA Tile：二十年来编程模型第一次换挡

CUDA 自 2006 年以来的基本假设是 SIMT：程序员亲自安排线程、线程束、共享内存和同步。性能好，但门槛和维护成本都高，而且每换一代硬件（Tensor Core 形态、异步拷贝机制都在变），手工优化的核就得重调一遍。

2025 年 12 月发布的 CUDA 13.1 引入 CUDA Tile：程序员写的是对数据块（tile）的运算，Tensor Core 调度、显存搬运、并行映射交给编译器和运行时处理。它由两部分组成——虚拟指令集 CUDA Tile IR，和 Python 侧的 DSL（cuTile）。NVIDIA 自己给这一版的定性是「CUDA 平台自诞生以来最大的一次更新」。后续版本补得很快：13.2 把 Tile 扩展到 Ampere、Ada 架构（此前首发只覆盖 Blackwell），13.3 补上 Tile 的 C++ 支持和 CompileIQ 编译器自动调优（官方称对 GEMM、注意力这类关键核最高约 15% 提速），同时 CUDA Python 转正 1.0、Green Contexts 支持把 SM 分区隔离。

对从业者的实际含义有两条。第一，可移植性：tile 级代码由编译器适配不同代际硬件，核的「保鲜期」变长了。第二，人群变化：cuTile 让 Python 工程师能直接写出接近库函数性能的自定义算子（官方展示的 GEMM 例子能到 cuBLAS 性能的九成量级），推理服务里那些非标准算子——融合、裁剪、特殊注意力变体——不必再排队等 C++ 工程师。

## 二、Dynamo：把推理当分布式系统来做

引擎层有 TensorRT-LLM（以及 vLLM、SGLang），它们解决单机多卡怎么跑得快。但生产级推理的难点在上一层：请求怎么路由、KV 缓存放哪、prefill 和 decode 互相干扰怎么办。Dynamo 就是 NVIDIA 补的这一层，开源、引擎无关，官方文档给它的定位是「分布式层」，由四块拼成：

- **分离式服务（disaggregated serving）**：prefill（吃提示词、算 KV）和 decode（逐 token 生成）拆到不同 GPU 组，各自独立扩缩。两者节奏完全不同——prefill 是计算密集的突发，decode 是显存带宽密集的长尾——混在一组卡上必然互相拖累。官方文档引 InferenceX 数据：DeepSeek V3 用分离式加大规模专家并行，单卡吞吐约 7 倍。
- **KV 感知路由**：路由器知道每张卡上缓存了哪些 KV 块，把请求优先发给「已经算过相同前缀」的卡，避免重复计算。这对多轮对话、长文档问答这类前缀复用率高的场景是直接的成本项。
- **KV 缓存分层卸载**：KV 在 HBM、主机内存、存储之间分层放置和找回，把「显存不够」从硬约束变成调度问题——长上下文推理能不能跑，常常就卡在这里。
- **SLA 规划与自动扩缩**：按时延/吞吐目标自动配比 prefill 与 decode 的资源，而不是靠人工经验拍比例。

TensorRT-LLM 在这套体系里是执行引擎：FP4/NVFP4 量化、推测解码、注意力数据并行这些引擎级优化照旧，只是被 Dynamo 的运行时管起来，多节点、请求取消、KV 事件发布都有了统一的壳。

## 三、两步棋的共同指向

把 CUDA Tile 和 Dynamo 放在一起看，逻辑是一致的：**把复杂度从使用者手里收回平台层**。Tile 收的是硬件细节（线程、同步、Tensor Core 映射），Dynamo 收的是系统细节（路由、缓存、扩缩）。原因也不难理解——GB300 这一代硬件的账面指标（整柜 130 TB/s NVLink、FP4 算力、576 TB/s 显存带宽聚合）要兑现成 token 产出，中间隔着的正是这两层复杂度。官方在性能/瓦那篇博客里特意提到，同样的 Blackwell 硬件靠软件优化在几个月内把每瓦性能又抬了一截——软件栈的迭代速度已经快于硬件换代，它就是产能的一部分。

对做基础设施的人来说，结论很实际：评估一个 AI 平台不能只看芯片规格表，还要看这两层的成熟度——算子生态跟不跟得上新硬件、推理框架的分布式能力到哪一步。这两项，才是账面 PFLOPS 和实际 token 产出之间那道差价的去处。

## 来源

- NVIDIA CUDA 13.3 官方博客（Tile C++、CompileIQ 最高约 15%、CUDA Python 1.0、Green Contexts）：https://developer.nvidia.com/blog/nvidia-cuda-13-3-enhances-gpu-development-with-tile-programming-in-c-compiler-autotuning-and-python-updates/
- NVIDIA CUDA 13.2 官方博客（Tile 扩展至 Ampere/Ada/Blackwell、cuTile Python）：https://developer.nvidia.com/blog/cuda-13-2-introduces-enhanced-cuda-tile-support-and-new-python-features/
- NVIDIA Dynamo 官方文档·Introduction（分布式层定位、分离式服务、KV 感知路由、KV 卸载、DeepSeek V3 约 7 倍单卡吞吐）：https://docs.nvidia.com/dynamo/v1.3.0/getting-started/introduction
- NVIDIA Dynamo 官方文档·TensorRT-LLM 后端（分离式、KV 路由、多节点、推测解码支持矩阵）：https://docs.nvidia.com/dynamo/v1.6.0/knowledge-base/modular-components/backends/tensor-rt-llm/overview
- NVIDIA GB300 NVL72 产品页（NVLink 130 TB/s、GPU 显存聚合带宽 576 TB/s）：https://www.nvidia.com/en-us/data-center/gb300-nvl72/

> 说明：本文为本人独立撰写，只使用公开资料，不涉及任何雇主或客户信息；文中数字均为厂商公开口径。
