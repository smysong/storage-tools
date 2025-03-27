# 使用官方的Python基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制当前目录下的所有文件到工作目录
COPY . /app

# 解压static.tar.gz到工作目录
RUN tar -xf static.tar -C /app

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露8080端口
EXPOSE 8080

# 运行应用
CMD ["python", "app.py"]