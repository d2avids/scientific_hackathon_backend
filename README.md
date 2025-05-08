## Installation
### 1. Install poetry dependencies:
```shell
poetry install
```

### 2. Activate virtual environment:
```shell
poetry shell
```

### 3. Set environment variables in .env file based on .env_example:

```shell
cp .env_example .env
```

###  4. Run the service locally:

```shell
cd src && python main.py
```

### or in Docker containers:
```shell
docker compose up --build --force-recreate -d
```