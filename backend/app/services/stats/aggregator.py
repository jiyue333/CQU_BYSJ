"""
统计数据聚合模块

职责：
- 聚合实时检测产生的人流数据
- 按时间维度统计（每秒、每分钟、每小时）
- 按区域维度统计（各区域人数、密度）
- 计算趋势指标（峰值、均值、变化率）
- 将统计结果持久化到数据库

数据输入：
- 来自 video/processor.py 的每帧检测结果
- 包含：timestamp, total_count, region_counts, in_count, out_count

数据输出：
- 时间序列统计数据
- 区域密度数据
- 供 api/endpoints/stats.py 查询

被调用方：
- video/processor.py 实时推送数据
- api/endpoints/stats.py 查询历史数据
"""
