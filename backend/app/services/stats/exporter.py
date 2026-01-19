"""
数据导出模块

职责：
- 将统计数据导出为 CSV 格式
- 将统计数据导出为 Excel 格式
- 支持按时间范围筛选导出数据
- 支持按区域筛选导出数据

核心接口：
- export_csv(start_time, end_time, regions) -> bytes
- export_excel(start_time, end_time, regions) -> bytes

被调用方：
- api/endpoints/stats.py 处理导出请求
"""
