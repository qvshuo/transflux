# FluxHans

翻译 Miniflux 未读条目为简体中文。

### 快速开始

克隆项目：

```shell
git clone https://github.com/qvshuo/FluxHans.git --depth=1
cd FluxHans
```

复制 Compose 示例文件，并根据实际情况修改 `docker-compose.yml` 中的环境变量：

```shell
cp docker-compose.example.yml docker-compose.yml
```

启动服务：

```shell
docker compose up -d --build
```

查看日志：

```shell
docker compose logs -f
```

重新构建：

```shell
docker compose build --no-cache
```

### 环境变量

| 变量                         | 必填 | 默认值    | 说明               |
| -------------------------- | -- | ------ | ---------------- |
| `MINIFLUX_BASE_URL`        | 是  | —      | Miniflux 服务器地址   |
| `MINIFLUX_API_KEY`         | 是  | —      | Miniflux API Key |
| `LLM_BASE_URL`             | 是  | —      | OpenAI 兼容 API 地址 |
| `LLM_API_KEY`              | 是  | —      | LLM API Key      |
| `LLM_MODEL`                | 是  | —      | 模型名称             |
| `LLM_MAX_LENGTH`           | 否  | `8192` | 发送给 LLM 前的最大字符数  |
| `LLM_TIMEOUT`              | 否  | `60`   | 请求超时秒数           |
| `TITLE_TRANSLATE_PROMPT`   | 否  | 内置提示词  | 标题翻译提示词          |
| `CONTENT_TRANSLATE_PROMPT` | 否  | 内置提示词  | 内容翻译提示词          |

### 致谢

本项目的灵感及初始代码来源于 [Qetesh/miniflux-ai](https://github.com/Qetesh/miniflux-ai)，默认翻译提示词来源于 [versun/rssbox](https://github.com/versun/rssbox)。
