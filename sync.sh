#!/bin/bash

# 配置变量
NODE_NAME=$(basename "$PWD")
REMOTE_HOST="root@10.132.208.7"
DOCKER_CONTAINER="RunningHub"
DOCKER_PATH="/workspace/ComfyUI/custom_nodes/${NODE_NAME}/"
# 使用固定的远程同步目录，保持 rsync 状态
REMOTE_SYNC_DIR="/root/${NODE_NAME}"

echo "开始增量同步到Docker容器..."

# 自动生成 cptorh01.sh 脚本
echo "正在生成 cptorh01.sh 脚本..."
cat > cptorh01.sh << 'EOF'
#!/bin/bash

# 创建目标目录
mkdir -p /root/custom_nodes

# 简化的mount命令
mount -t nfs4 -o rw rh-nfs.runninghub.cn:/data/rh_storage/global/custom_nodes_rel /root/custom_nodes

# 获取当前目录名作为NODE_NAME
NODE_NAME=$(basename "$PWD")

# 创建目标目录
mkdir -p /root/custom_nodes/${NODE_NAME}

# 显示将要执行的rsync命令
echo "准备执行以下rsync命令："
echo "rsync -av --include=\"*/\" --include=\"*.py\" --exclude=\"*\" ./ /root/custom_nodes/${NODE_NAME}/"
echo ""
echo "此命令将同步当前目录及子目录中的所有 .py 文件到 /root/custom_nodes/${NODE_NAME}/"
echo ""
read -p "是否继续执行？(输入 Y 确认): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "开始同步 Python 文件..."
    rsync -av --include="*/" --include="*.py" --exclude="*" ./ /root/custom_nodes/${NODE_NAME}/
    
    if [ $? -eq 0 ]; then
        echo "Python 文件同步完成！"
    else
        echo "Python 文件同步失败！"
        exit 1
    fi
else
    echo "取消同步操作。"
    exit 1
fi
EOF

# 给 cptorh01.sh 添加执行权限
chmod +x cptorh01.sh
echo "cptorh01.sh 脚本生成完成！"

# 检查本地是否安装了rsync
if ! command -v rsync &> /dev/null; then
    echo "错误：本地未安装 rsync，请先安装: apt-get install rsync 或 yum install rsync"
    exit 1
fi

# 检查远程连接和Docker容器
echo "检查远程连接和Docker容器..."
ssh ${REMOTE_HOST} "docker ps | grep ${DOCKER_CONTAINER}" > /dev/null
if [ $? -ne 0 ]; then
    echo "Docker容器 ${DOCKER_CONTAINER} 未运行！"
    exit 1
fi

# 检查远程是否安装了rsync
echo "检查远程rsync..."
ssh ${REMOTE_HOST} "which rsync" > /dev/null
if [ $? -ne 0 ]; then
    echo "错误：远程主机未安装 rsync，请在远程主机安装: apt-get install rsync 或 yum install rsync"
    exit 1
fi

# 确保Docker容器内目标目录存在
echo "确保Docker容器内目标目录存在..."
ssh ${REMOTE_HOST} "docker exec ${DOCKER_CONTAINER} mkdir -p ${DOCKER_PATH}"
if [ $? -ne 0 ]; then
    echo "无法在Docker容器内创建目录！"
    exit 1
fi

# 确保远程同步目录存在
echo "确保远程同步目录存在..."
ssh ${REMOTE_HOST} "mkdir -p ${REMOTE_SYNC_DIR}"

# 定义要排除的文件和目录
EXCLUDE_PATTERNS=(
    "--exclude=.git"
    "--exclude=__pycache__"
    "--exclude=*.pyc"
    "--exclude=*.pyo"
    "--exclude=.DS_Store"
    "--exclude=Thumbs.db"
    "--exclude=*.tmp"
    "--exclude=*.swp"
    "--exclude=.vscode"
    "--exclude=.idea"
    "--exclude=*.log"
    "--exclude=weights/"
    "--exclude=save_audio/"
)

# 使用rsync进行增量同步到远程固定目录
echo "开始增量同步文件..."
echo "正在比较文件差异，只传输变化的文件..."

rsync -avz --progress --delete \
    "${EXCLUDE_PATTERNS[@]}" \
    --rsync-path="rsync" \
    ./ ${REMOTE_HOST}:${REMOTE_SYNC_DIR}/

if [ $? -eq 0 ]; then
    echo "增量同步到远程主机完成，正在同步到Docker容器..."
    
    # 直接从远程同步目录同步到Docker容器，保持文件权限
    ssh ${REMOTE_HOST} "cd ${REMOTE_SYNC_DIR} && tar -cpf - . | docker exec -i ${DOCKER_CONTAINER} tar -xpf - -C ${DOCKER_PATH}"
    
    if [ $? -eq 0 ]; then
        echo "增量同步完成！只传输了变化的文件。"
        echo "提示：下次同步将更快，因为只会传输修改过的文件。"
        echo "远程同步目录：${REMOTE_SYNC_DIR}"
        
        # 修改文件权限为644
        echo "正在修改文件权限为644..."
        ssh ${REMOTE_HOST} "docker exec ${DOCKER_CONTAINER} find ${DOCKER_PATH} -type f -exec chmod 644 {} \;"
        if [ $? -eq 0 ]; then
            echo "文件权限修改完成！"
        else
            echo "文件权限修改失败，请手动检查！"
        fi
        
        # 重启ComfyUI服务
        echo "正在重启ComfyUI服务..."
        ssh ${REMOTE_HOST} "pkill -9 -f 'python main.py'"
        if [ $? -eq 0 ]; then
            echo "ComfyUI服务已重启！"
        else
            echo "重启ComfyUI服务失败，请手动检查！"
        fi
    else
        echo "同步到Docker容器失败！"
        exit 1
    fi
else
    echo "增量同步失败！"
    exit 1
fi
