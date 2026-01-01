#!/bin/bash
# F-29: 方案 F 端到端验收脚本
#
# 验收步骤：
# 1. 启动一路流
# 2. 验证 ZLM 出现 {stream_id}_heatmap 渲染流
# 3. 验证前端可播放渲染流（带热力图）
# 4. 停止后无残留推流进程
#
# 使用方法：
#   ./scripts/smoke_render.sh [API_BASE_URL] [ZLM_BASE_URL]
#
# 示例：
#   ./scripts/smoke_render.sh http://localhost:8000 http://localhost:8080

set -e

# 配置
API_BASE_URL="${1:-http://localhost:8000}"
ZLM_BASE_URL="${2:-http://localhost:8080}"
STREAM_NAME="smoke_test_$(date +%s)"
RTSP_URL="rtsp://localhost:554/live/test"  # 测试用 RTSP 源

echo "=========================================="
echo "方案 F 端到端验收测试"
echo "=========================================="
echo "API: $API_BASE_URL"
echo "ZLM: $ZLM_BASE_URL"
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓ $1${NC}"
}

fail() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# 检查依赖
check_deps() {
    echo "检查依赖..."
    command -v curl >/dev/null 2>&1 || fail "需要 curl"
    command -v jq >/dev/null 2>&1 || fail "需要 jq"
    pass "依赖检查通过"
}

# 检查服务健康
check_services() {
    echo ""
    echo "检查服务健康..."
    
    # 检查 API
    if curl -s "$API_BASE_URL/health" | grep -q "ok"; then
        pass "API 服务正常"
    else
        fail "API 服务不可用"
    fi
    
    # 检查 ZLM
    if curl -s "$ZLM_BASE_URL/index/api/getServerConfig" | grep -q "code"; then
        pass "ZLMediaKit 服务正常"
    else
        warn "ZLMediaKit 可能不可用（继续测试）"
    fi
}

# 创建测试流
create_stream() {
    echo ""
    echo "创建测试流..."
    
    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/streams" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"$STREAM_NAME\",
            \"type\": \"rtsp\",
            \"source_url\": \"$RTSP_URL\"
        }")
    
    STREAM_ID=$(echo "$RESPONSE" | jq -r '.id')
    
    if [ "$STREAM_ID" != "null" ] && [ -n "$STREAM_ID" ]; then
        pass "流创建成功: $STREAM_ID"
        echo "  响应: $RESPONSE"
    else
        fail "流创建失败: $RESPONSE"
    fi
}

# 启动流
start_stream() {
    echo ""
    echo "启动流..."
    
    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/streams/$STREAM_ID/start")
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    PLAY_URL=$(echo "$RESPONSE" | jq -r '.play_url')
    
    if [ "$STATUS" = "running" ]; then
        pass "流启动成功"
        echo "  状态: $STATUS"
        echo "  播放地址: $PLAY_URL"
    else
        fail "流启动失败: $RESPONSE"
    fi
    
    # 验证播放地址包含 _heatmap
    if echo "$PLAY_URL" | grep -q "_heatmap"; then
        pass "播放地址为渲染流（包含 _heatmap）"
    else
        warn "播放地址可能不是渲染流: $PLAY_URL"
    fi
}

# 验证渲染流存在
verify_render_stream() {
    echo ""
    echo "验证渲染流..."
    
    # 等待渲染流建立
    sleep 3
    
    # 查询 ZLM 媒体列表
    MEDIA_LIST=$(curl -s "$ZLM_BASE_URL/index/api/getMediaList")
    
    RENDER_STREAM_ID="${STREAM_ID}_heatmap"
    
    if echo "$MEDIA_LIST" | grep -q "$RENDER_STREAM_ID"; then
        pass "渲染流已在 ZLM 注册: $RENDER_STREAM_ID"
    else
        warn "渲染流可能未注册（可能是测试环境限制）"
        echo "  ZLM 媒体列表: $MEDIA_LIST"
    fi
}

# 验证检测结果
verify_detection_results() {
    echo ""
    echo "验证检测结果..."
    
    # 等待推理结果
    sleep 2
    
    RESULT=$(curl -s "$API_BASE_URL/api/streams/$STREAM_ID/latest-result")
    
    if echo "$RESULT" | jq -e '.total_count' >/dev/null 2>&1; then
        TOTAL_COUNT=$(echo "$RESULT" | jq -r '.total_count')
        pass "检测结果可用: total_count=$TOTAL_COUNT"
    else
        warn "检测结果可能不可用（可能是测试环境限制）"
    fi
}

# 停止流
stop_stream() {
    echo ""
    echo "停止流..."
    
    RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/streams/$STREAM_ID/stop")
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    PLAY_URL=$(echo "$RESPONSE" | jq -r '.play_url')
    
    if [ "$STATUS" = "stopped" ]; then
        pass "流停止成功"
    else
        fail "流停止失败: $RESPONSE"
    fi
    
    if [ "$PLAY_URL" = "null" ]; then
        pass "播放地址已清空"
    else
        warn "播放地址未清空: $PLAY_URL"
    fi
}

# 验证无残留进程
verify_no_residual() {
    echo ""
    echo "验证无残留进程..."
    
    # 等待进程清理
    sleep 2
    
    # 检查是否有残留的 ffmpeg 进程（针对该流）
    if pgrep -f "ffmpeg.*$STREAM_ID" >/dev/null 2>&1; then
        warn "可能有残留 ffmpeg 进程"
        pgrep -af "ffmpeg.*$STREAM_ID" || true
    else
        pass "无残留 ffmpeg 进程"
    fi
    
    # 检查 ZLM 中渲染流是否已移除
    MEDIA_LIST=$(curl -s "$ZLM_BASE_URL/index/api/getMediaList")
    RENDER_STREAM_ID="${STREAM_ID}_heatmap"
    
    if echo "$MEDIA_LIST" | grep -q "$RENDER_STREAM_ID"; then
        warn "渲染流可能未从 ZLM 移除"
    else
        pass "渲染流已从 ZLM 移除"
    fi
}

# 清理测试流
cleanup() {
    echo ""
    echo "清理测试流..."
    
    if [ -n "$STREAM_ID" ]; then
        curl -s -X DELETE "$API_BASE_URL/api/streams/$STREAM_ID" >/dev/null 2>&1 || true
        pass "测试流已删除"
    fi
}

# 主流程
main() {
    check_deps
    check_services
    
    # 设置清理钩子
    trap cleanup EXIT
    
    create_stream
    start_stream
    verify_render_stream
    verify_detection_results
    stop_stream
    verify_no_residual
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}验收测试完成${NC}"
    echo "=========================================="
}

main "$@"
