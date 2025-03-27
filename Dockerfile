# 使用官方的Python基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制当前目录下的所有文件到工作目录
COPY . /app

# 安装unzip工具和依赖
RUN apt-get update && apt-get install -y unzip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 解压static.zip到工作目录
RUN unzip static.zip -d /app

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露8080端口
EXPOSE 8080

# 运行应用
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]