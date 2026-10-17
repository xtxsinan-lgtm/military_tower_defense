# D2-B 待决问题汇总与分级

> 审查范围：docs/spec/00–06 第 8 节全部待决问题 + pending_decisions.md（4 条）。
> 状态：**编写中**（边写边存）。

## 0. 进度

- [x] 00 第 8 节（Q1–Q17）
- [x] 01 第 8.1 节（Q1–Q15）
- [x] 02 第 8.1 节（Q1–Q39）
- [ ] 03
- [ ] 04
- [ ] 05
- [ ] 06
- [ ] 合并、核对、分级

## 草稿：已发现的冲突

- 地球曲率：01 Q14 计入（4/3 有效地球半径）；02 Q1 "不模拟地球曲率（地平线效果由倍率概括）"。
- 天线高度：01 Q3 `rules/terrain.json.defaultAntennaHeightM = 10`；02 Q32 `rules/tracks.json.detection.sensorHeightM = 10`——同一参数两个位置。
