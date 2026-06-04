# transflux

翻译 Miniflux 未读条目为简体中文。

## 快速开始

克隆项目：

```shell
git clone https://github.com/qvshuo/transflux.git --depth=1
cd transflux
```

复制 Compose 示例文件并修改 `docker-compose.yml` 中的环境变量，然后运行：

```bash
cp docker-compose.example.yml docker-compose.yml
```

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

重新构建：

```bash
docker compose build --no-cache
```

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `MINIFLUX_BASE_URL` | 是 | — | Miniflux 服务器地址 |
| `MINIFLUX_API_KEY` | 是 | — | Miniflux API Key |
| `LLM_BASE_URL` | 是 | — | OpenAI 兼容 API 地址 |
| `LLM_API_KEY` | 是 | — | LLM API Key |
| `LLM_MODEL` | 是 | — | 模型名称 |
| `LLM_MAX_LENGTH` | 否 | `8192` | 发送给 LLM 前的最大字符数 |
| `LLM_TIMEOUT` | 否 | `60` | 请求超时秒数 |
| `TITLE_TRANSLATE_PROMPT` | 否 | 内置提示词 | 条目标题翻译提示词 |
| `CONTENT_TRANSLATE_PROMPT` | 否 | 内置提示词 | 条目内容翻译提示词 |

默认标题翻译提示词会直接返回简体中文译文。默认内容翻译提示词会保留 HTML 标签、属性和结构，只翻译可见文本为简体中文。可以通过环境变量自定义提示词。

## 工作原理

每分钟轮询一次 Miniflux 未读条目，检测每条标题和内容的语言，若非中文则调用 LLM 翻译后写回。标题翻译结果放在原标题前，以 ` || ` 分隔；内容翻译结果放在原文前，以 `<br /><hr><br />` 分隔。

## 致谢

本项目最初的灵感及代码均来自于 [Qetesh/miniflux-ai](https://github.com/Qetesh/miniflux-ai)，默认翻译提示词来自于 [versun/rssbox](https://github.com/versun/rssbox)。
