# 国内 DNS 白名单

这份名单以 blackmatrix7 的完整 `China_Domain.list` 为底稿，移除已识别的海外服务，再合并本仓库维护的国内补充项。
由 Python 脚本批量转换、合并、去重和检查。Surge 只需要引用生成后的 `ChinaDNS.list`。

## 文件与维护入口

| 文件 | 用途 |
| --- | --- |
| `ChinaDNS.list` | 生成后的完整规则，Surge 使用 `RULE-SET:` 引用；不要直接修改 |
| `ChinaDNS.extra.list` | 国内补充项，如飞书、WPS、12306、DeepSeek、Kimi 等 |
| `ChinaDNS.exclude.list` | 经审查排除的海外服务及不适合国内解析的条目，含分类和依据 |
| `../tools/build_china_dns.py`（从仓库根目录运行 `tools/build_china_dns.py`） | 批量生成工具 |
| `ChinaDNS.LICENSE` | 保留上游 GPL v2 许可文本 |

脚本位于仓库根目录的 `tools/`，从本文件所在目录访问时路径是 `../tools/build_china_dns.py`。
`extra` 和 `exclude` 是维护输入；实际生效名单由脚本生成，避免人工维护两套完整列表。
这两个输入文件本身不要绑定国内 DNS，尤其不能把排除文件当作国内名单引用。

## 本次处理结果（2026-11-06）

| 步骤 | 数量 |
| --- | ---: |
| 上游原始域名条目 | 3,689 |
| 国内补充条目 | 67 |
| 根据 155 条排除规则移除的条目 | 161 |
| 去除被父域名规则覆盖的条目 | 1 |
| 最终规则 | **3,594** |

排除包括 BrowserLeaks、Microsoft/Office/Outlook、Oracle/Java、Apple 资源、部分全球 CDN、海外学术机构，
以及 Lark、阿里云国际站、华为云已明确的境外区域等。完整排除项见 `ChinaDNS.exclude.list`，没有用模糊关键词删除域名。

原先上游审计的 156 个主站/资源/API 样本全部命中，之前遗漏的 38 个样本均已补齐。
已验证排除项不会被保留的父域规则重新覆盖，Claude、OpenAI、Google、Microsoft、Oracle 等海外域名以及未知域名样本不命中国内名单。
Surge 离线配置校验通过；脚本的去重、父域冲突检查、输入格式检查和拒绝覆盖行为均已验证。
这些是离线规则验证，不是当前运行环境的 DNS/WebRTC 泄露测试。

本次上游快照 SHA-256：

```text
28817e4a59359c6e6c264b6ed7d05dfc376548afb0aab50dbec5f60eb79e413f
```

## 收录范围和边界

- 保留上游的大部分条目，不把完整名单缩成常用网站抽样名单；保留项并不表示已逐一核实其当前归属。
- 只导入 `China_Domain.list` 的纯域名条目，不导入配套 `China.list` 中的关键词、IP、USER-AGENT 或 `.cn` 整体规则。
- `.example.com` 转为 `DOMAIN-SUFFIX,example.com`，匹配根域名和任意层级子域；无前导点的条目转为精确 `DOMAIN`。
- 本版本保留上游中 `alicdn.com`、`aliyuncs.com`、`myqcloud.com`、`bcebos.com`、`bytedance.net` 等共享基础域名。它们也可能承载国际业务，不能据此承诺所有海外网站的全部资源都不命中国内 DNS。
- 未匹配的域名继续使用全局海外 DNS；“未知”指没有命中名单，也没有命中其父域名规则。
- 国外归属判断需要结合服务身份或官方资料；脚本不根据一次 DNS 返回 IP 的地理位置自动判定。

## 日常补充和排除

国内服务放在 `ChinaDNS.extra.list`，确认不应使用国内 DNS 的域名放在 `ChinaDNS.exclude.list`。
每组规则加上服务名称和必要的来源说明。例如：

```ini
# 国内补充
DOMAIN-SUFFIX,feishu.cn

# 海外排除
DOMAIN-SUFFIX,browserleaks.com
```

规则必须是 `DOMAIN,完整主机名` 或 `DOMAIN-SUFFIX,域名后缀`。不接受关键词、IP、URL 或通配符。
重复规则和已有父域名覆盖的子规则由脚本自动去重。

如果要排除一个具体海外子域，但上游保留了它的父域名，脚本会报错停止。
正向名单不能表示“父域全部允许，唯独某个子域例外”；此时需要排除或缩小该父域范围，再把明确的国内子域补回来。
不能仅从文本中删掉子域那一行就认为排除成功。

## 使用脚本更新

在仓库根目录运行。默认下载上游文件；也可以用 `--upstream /path/to/China_Domain.list` 指定已保存的快照。
脚本只创建新的候选文件和报告，拒绝覆盖已有文件，也不会提交、推送或修改 Surge 运行状态。

```bash
cd /Users/xiaozhaodong/VsCodeProjects/Surge

dns_preview_dir=$(mktemp -d /tmp/surge-china-dns.XXXXXX)
python3 tools/build_china_dns.py \
  --output "$dns_preview_dir/ChinaDNS.list" \
  --report "$dns_preview_dir/report.json"

diff -u rule/ChinaDNS.list "$dns_preview_dir/ChinaDNS.list"
```

`diff` 返回 1 表示存在差异。检查候选内容和报告后，再用候选替换 `rule/ChinaDNS.list`，并按需要提交、推送。
报告包含上游及两个本地输入的 SHA-256、移除的具体条目、去重明细和最终数量。
有格式错误、网络错误或排除冲突时构建明确失败，不会悄悄退回旧数据或忽略错误。

## 接入现有 Surge 配置

仓库发布只更新规则资源，不会自动替换本机正在使用的配置。下面的片段按需加入现有配置。
保留现有默认海外 DNS、`PROTOCOL,DOH,Oracle-US` 和 Oracle-US 的 H2 主用/Snell 备用配置。
在现有 `[Host]` 中保留海外例外，用新名单**替换**原来的 `China_Domain.list` 国内 DNS 绑定。
不要同时保留旧绑定，否则已从新名单排除的域名仍可能被旧名单分配国内 DNS。

仅在这台 Mac 使用本地文件时：

```ini
[Host]
browserleaks.com = server:https://8.8.8.8/dns-query
*.browserleaks.com = server:https://8.8.8.8/dns-query
RULE-SET:/Users/xiaozhaodong/VsCodeProjects/Surge/rule/ChinaDNS.list = server:quic://223.5.5.5
```

跨设备使用时，可以引用仓库 `master` 上的 Raw 地址：

```ini
RULE-SET:https://raw.githubusercontent.com/xiaozhaodong/Surge/master/rule/ChinaDNS.list = server:quic://223.5.5.5
```

名单更新后，检查 Surge 的外部资源是否已刷新。
本地绝对路径不适合直接同步给手机或其他电脑。

同一文件也可用于流量分流，在已有 `[Rule]` 中指定策略，例如直连：

```ini
RULE-SET,https://raw.githubusercontent.com/xiaozhaodong/Surge/master/rule/ChinaDNS.list,DIRECT
```

通用国内规则应放在广告拦截、Claude、BrowserLeaks 等专用规则之后，`GEOIP` 和 `FINAL` 之前。
排除文件只保证某个域名不命中本名单，其他旧规则仍可能将它直连，接入时应检查重叠规则。

`[Host]` 的引用选择 DNS 上游，`[Rule]` 的引用选择连接策略，两者独立配置。
代理服务器解析、浏览器自带 DNS、实际出口和 WebRTC 仍需要在接入后分别检查。
可用 `surge-cli dns trace <域名>` 对照验证国内和海外样本。

## 来源与许可

生成规则派生自 [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)，保留作者归属和 [GPL v2 许可文本](ChinaDNS.LICENSE)。
本仓库对规则格式、海外排除和国内补充做了修改，首次整理于 2026-11-06。

- [上游 China_Domain.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/China/China_Domain.list)
- [Surge DNS 映射及 RULE-SET 引用](https://manual.nssurge.com/dns/local-dns-mapping.html)
- [Surge 域名匹配语义](https://manual.nssurge.com/rules/domain.html)
