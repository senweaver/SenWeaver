# SendWeaver后端
## 安装环境

安装Redis

安装MySQL、PostgreSQL、MariaDB、SQLite、Oracle、SQLServer等（SQLAlchemy支持的数据库）

## python环境

```shell
conda create -n senweaver python=3.12
conda activate senweaver
```

## 安装依赖包

```shell
pip install poetry --index-url=https://mirrors.aliyun.com/pypi/simple
poetry install
```

## 修改env文件

> 拷贝.env.example为.env，然后配置.env文件

```
# Project
NAME=SenWeaver
VERSION=1.0.0
TITLE=SenWeaver
DESCRIPTION="SenWeaver framework, high performance, easy to learn, fast to code, ready for production."
# Uvicorn
APP_HOST=0.0.0.0
APP_PORT=8010
APP_RELOAD=True
# Environment: dev, test, prod
ENVIRONMENT=dev
DEMO_MODE=False

# Database
DATABASE_ID_TYPE=snowflake
DATABASE_URL = mysql+asyncmy://root:123456@localhost:3306/senweaver


# REDIS  redis://:pass@host:port/dbname
REDIS_ENABLE=True
REDIS_URL=redis://:@localhost:6379/0

# CAPTCHA
CAPTCHA_ENABLE=False
CAPTCHA_EXPIRE_SECONDS=60

# Token
ALGORITHM="HS256"
SECRET_KEY=hQl4ihESBJLDZ2kCxUsrVBszR0kFXA_nk6_YUVm

# Log
#LOG_PATH=

# CORS
CORS_ENABLE=True
CORS_ALLOW_ORIGINS="http://localhost,http://localhost:8848,https://127.0.0.1,http://www.senweaver.com" 
CORS_ALLOW_CREDENTIALS=True  

```

## 创建数据库表

> 使用数据库迁移 [alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

1. 生成迁移文件

    ```shell
    alembic revision --autogenerate
    ```
2. 执行迁移

    ```shell
    alembic upgrade head
    ```

## 创建超管用户

```shell
python main.py createsuperuser
```

## 初始化数据

```shell
python main.py data init
```

## 启动后端

```shell
python main.py run
```

‍
