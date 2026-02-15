
# rename.js
```
https://raw.githubusercontent.com/gw124/Collection/refs/heads/main/Script/Sub-Store/rename.js#out=zh&nf&flag&name=机场名｜&bl&blkey=Zx>专线+Fam>家宽+直连+Direct>直连+中转+Transit>中转+中继>中转+Relay>中转+家宽+动态+IPV6+流媒体+Netflix+Disney+chatGPT>OpenAI+IPLC+IEPL+BGP+CN2+GIA+CMI+CMIN+AIG+PCCW+HKT
```
| 原始节点名 (Input) | 处理后效果 (Output) | 说明 |
| :--- | :--- | :--- |
| `Hong Kong 01` | **机场｜ 🇭🇰 香港 01** | 基础格式化 |
| `[专线] SG IPLC AIG` | **机场｜ 🇸🇬 新加坡 01 IPLC AIG** | 保留高级线路标识 |
| `US Zx chatGPT` | **机场｜ 🇺🇸 美国 01 专线 OpenAI** | Zx转专线，chatGPT转OpenAI |
| `台湾 Relay 01` | **机场｜ 🇹🇼 台湾 01 中继** | Relay转中继 |
| `JP Direct 05` | **机场｜ 🇯🇵 日本 05 直连** | Direct转直连 |
| `🇭🇰 [动态家宽] 1.5x` | **机场｜ 🇭🇰 香港 01 动态 家宽 1.5x** | 提取属性与倍率 |
| `🇺🇸 US_CN2_GIA` | **机场｜ 🇺🇸 美国 01 CN2 GIA** | 下划线清理与关键词保留 |
| `HK PCCW 流媒体` | **机场｜ 🇭🇰 香港 01 流媒体 PCCW** | 组合保留 |
