# Serenity Daily Push

每天早 8:57 自动抓取 Serenity(@aleabitoreddit) 最新推文 → 分析 → 推送微信。

## 部署

### 1. 推送到 GitHub

```bash
# 安装 GitHub CLI（如果没有）
brew install gh

# 登录
gh auth login

# 创建仓库并推送
cd serenity-push
git init
git add .
git commit -m "init"
gh repo create serenity-push --public --source . --push
```

### 2. 设置 Secret

```bash
gh secret set SCT_SENDKEY --body "你的SendKey"
```

### 3. 验证

在 GitHub 仓库页面 → Actions → Serenity Daily Push → Run workflow 手动触发一次。

## 以后

什么都不用管。每天早上 8:57 微信自动收到推送。
