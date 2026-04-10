# Telegram 批量换绑脚本

> 支持从旧手机号批量迁移 Telegram 账号到全新未注册的手机号，所有数据（聊天、群组、联系人）完整保留。

---

## 📋 功能特点

- ✅ 通过 `.session` 文件免验证登录（无需输入旧号码验证码）
- ✅ 自动检测并替换非默认 `app_id`/`app_hash`
- ✅ 根据新号码国家自动匹配对应国家的代理 IP（IPDeep）
- ✅ 自动轮询接码平台获取验证码
- ✅ 自动处理两步验证（2FA）
- ✅ 详细的中文日志（控制台 + 文件）
- ✅ 生成格式化的结果文件和更新后的账号包

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 准备输入文件

将以下文件放入 `input/` 目录：

#### `input/accounts.zip`

包含配对的 `.session` 和 `.json` 文件：

```
accounts.zip
├── 8801721397818.session
├── 8801721397818.json
├── 8801721397819.session
├── 8801721397819.json
└── ...
```

**JSON 文件格式**（每个账号一个）：

```json
{
  "phone": "8801721397818",
  "session_file": "8801721397818.session",
  "app_id": 4,
  "app_hash": "014b35b6184100b085b0d0572f9b5103",
  "twoFA": "xx99999",
  "user_id": "7221232881",
  "first_name": "mr",
  "last_name": "shuvo"
}
```

> **注意**：如果 `app_id` 和 `app_hash` 不是默认值，脚本会自动替换为默认值。

#### `input/new_phones.txt`

每行一个新号码和对应的接码 API，用 `|` 分隔：

```txt
+8617800001234|https://smsapis.com/api/get_sms?key=074095f2f34c11bb28c024d45a32b331
+8617800005678|https://smsapis.com/api/get_sms?key=074095f2f34c11bb28c024d45a32b332
+12025551234|https://smsapis.com/api/get_sms?key=074095f2f34c11bb28c024d45a32b333
```

> **重要**：新号码必须是**全新未注册**的手机号。

### 3. 运行脚本

```bash
python change_phone.py
```

### 4. 查看结果

结果文件保存在 `output/` 目录：

```
output/
├── success_result.txt          # 成功换绑的号码+API（格式同输入）
├── updated_accounts.zip        # 更新后的 session+json 文件包
├── failed_phones.txt           # 换绑失败的号码（可重新使用）
├── success_accounts.json       # 成功换绑的详细信息
└── logs/
    └── change_phone_20260410_143022.log   # 详细日志文件
```

---

## 📁 完整文件结构

```
api/
├── change_phone.py              # 主脚本
├── config.json                  # 配置文件
├── requirements.txt             # Python 依赖
├── README.md                    # 本文档
├── .gitignore                   # Git 忽略规则
│
├── input/                       # 输入文件夹（您上传文件到这里）
│   ├── accounts.zip             # 包含 session+json 的压缩包
│   └── new_phones.txt           # 新号码+接码API 列表
│
├── sessions/                    # 脚本自动解压到此目录
│   ├── 8801721397818.session
│   ├── 8801721397818.json
│   └── ...
│
└── output/                      # 输出结果
    ├── success_result.txt
    ├── updated_accounts.zip
    ├── failed_phones.txt
    ├── success_accounts.json
    └── logs/
```

---

## ⚙️ 配置说明（config.json）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `proxy.enabled` | 是否启用代理 | `true` |
| `proxy.username` | IPDeep 代理用户名前缀 | `d1561533000` |
| `proxy.password` | IPDeep 代理密码 | `Qqesi3rN` |
| `proxy.server` | 代理服务器地址 | `gate.ipdeep.com` |
| `proxy.port` | 代理端口 | `8082` |
| `proxy.auto_match_country` | 根据号码自动匹配国家 IP | `true` |
| `intervals.between_accounts_min` | 账号间最小等待时间（秒） | `30` |
| `intervals.between_accounts_max` | 账号间最大等待时间（秒） | `60` |
| `sms.max_retry` | 接码最大轮询次数 | `60` |
| `sms.retry_interval` | 接码轮询间隔（秒） | `5` |

---

## 📊 输出文件说明

### `success_result.txt`

换绑成功的号码和接码 API（格式同 `new_phones.txt`）：

```txt
+8617800001234|https://smsapis.com/api/get_sms?key=074095f2f34c11bb28c024d45a32b331
+8617800005678|https://smsapis.com/api/get_sms?key=074095f2f34c11bb28c024d45a32b332
```

### `updated_accounts.zip`

打包了所有换绑成功账号的更新后文件：
- `.session` 文件（Telethon 自动更新）
- `.json` 文件（号码已更新为新号码，API 已替换为默认值）

### `failed_phones.txt`

换绑失败的号码（格式同 `new_phones.txt`），可以重新放入 `new_phones.txt` 重试。

### `success_accounts.json`

成功换绑账号的完整信息，示例：

```json
[
  {
    "old_phone": "8801721397818",
    "new_phone": "+8617800001234",
    "session_file": "8801721397818.session",
    "twoFA": "xx99999",
    "user_id": "7221232881",
    "first_name": "mr",
    "last_name": "shuvo",
    "changed_at": "2026-04-10 14:30:22",
    "country": "cn"
  }
]
```

---

## 🌐 支持的国家代码

脚本支持以下国家的自动代理匹配：

| 区域 | 国家 | 号码前缀 |
|------|------|---------|
| 北美 | 美国 🇺🇸 | +1 |
| 中国及周边 | 中国 🇨🇳 | +86 |
| | 香港 🇭🇰 | +852 |
| | 澳门 🇲🇴 | +853 |
| | 台湾 🇹🇼 | +886 |
| 南亚 | 孟加拉国 🇧🇩 | +880 |
| | 印度 🇮🇳 | +91 |
| | 巴基斯坦 🇵🇰 | +92 |
| 东南亚 | 马来西亚 🇲🇾 | +60 |
| | 印度尼西亚 🇮🇩 | +62 |
| | 菲律宾 🇵🇭 | +63 |
| | 新加坡 🇸🇬 | +65 |
| | 泰国 🇹🇭 | +66 |
| | 越南 🇻🇳 | +84 |
| 欧洲 | 英国 🇬🇧 | +44 |
| | 法国 🇫🇷 | +33 |
| | 德国 🇩🇪 | +49 |
| | 俄罗斯 🇷🇺 | +7 |
| 中东 | 阿联酋 🇦🇪 | +971 |
| | 沙特阿拉伯 🇸🇦 | +966 |
| | 土耳其 🇹🇷 | +90 |
| 其他 | 澳大利亚 🇦🇺 | +61 |
| | 巴西 🇧🇷 | +55 |

---

## ❓ 常见问题

### Q: Session 文件过期怎么办？
A: 脚本会自动跳过过期的 session 文件，并在日志中记录错误。请重新获取有效的 session 文件。

### Q: 验证码超时怎么办？
A: 脚本最多等待 300 秒（60次 × 5秒），超时后将号码写入 `failed_phones.txt`，可以重新尝试。

### Q: 两步验证密码错误怎么办？
A: 确保 JSON 文件中的 `twoFA` 字段填写了正确的密码。如果没有设置两步验证，留空即可。

### Q: 代理连接失败怎么办？
A: 检查 `config.json` 中的代理配置是否正确。如需临时禁用代理，将 `proxy.enabled` 设为 `false`。

### Q: 新号码必须是未注册的吗？
A: 是的，新号码必须是**全新未注册**的 Telegram 手机号。Telegram 会向该号码发送验证码，只有未注册的号码才能成为账号的新手机号绑定目标。

### Q: 换绑后原账号的数据会丢失吗？
A: 不会。换绑只是更换账号绑定的手机号，所有聊天记录、群组、联系人等数据都会完整保留。

---

## ⚠️ 注意事项

1. **每天处理数量**：建议每天不超过 20 个账号，避免触发 Telegram 风控。
2. **账号间隔**：脚本默认在每个账号之间等待 30-60 秒，请勿修改为过小的值。
3. **新号码要求**：新手机号必须是全新未注册 Telegram 的号码，否则换绑会失败。
4. **Session 文件安全**：`.session` 文件包含账号登录凭证，请妥善保管，不要泄露。
5. **备份**：运行前请备份原始的 `accounts.zip` 文件。

---

## 📞 技术支持

如有问题，请查看 `output/logs/` 目录中的详细日志文件进行排查。
