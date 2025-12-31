# Alembic 数据库迁移

## 常用命令

```bash
# 生成迁移（自动检测模型变更）
alembic revision --autogenerate -m "描述信息"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看历史
alembic history

# 查看当前版本
alembic current
```

## 开发流程

1. 在 `app/models/` 中创建或修改模型
2. 在 `app/models/__init__.py` 中导入模型
3. 生成迁移：`alembic revision --autogenerate -m "描述"`
4. 检查生成的迁移脚本（`alembic/versions/`）
5. 执行迁移：`alembic upgrade head`
6. 测试回滚：`alembic downgrade -1 && alembic upgrade head`

## 注意事项

- 执行迁移前务必备份数据库
- 检查自动生成的迁移脚本是否正确
- 确保每个 `upgrade()` 都有对应的 `downgrade()`
- 生产环境迁移前在测试环境充分测试
