# 能源早报 · 海外能源资讯聚合

自动聚合全球能源领域最新资讯，每3小时更新，标题自动翻译为中文。

涵盖分类：太阳能 / 风电 / 储能 / 氢能 / 电网 / 电力 / 油气 / 核能 / EV / 政策

---

## 部署步骤

### 第一步：创建 GitHub 仓库

1. 登录 [github.com](https://github.com)，点击右上角 **+** → **New repository**
2. 仓库名填写：`energy-news`（或你喜欢的名字）
3. 选择 **Public**（公开，GitHub Pages 免费托管需要公开仓库）
4. **不要**勾选"Add a README file"
5. 点击 **Create repository**

### 第二步：上传代码

在本地 `energy-news` 目录中执行：

```bash
cd C:\Users\Administrator\WorkBuddy\Claw\energy-news

# 初始化 git
git init
git add .
git commit -m "initial commit"

# 替换为你的 GitHub 用户名
git remote add origin https://github.com/你的用户名/energy-news.git
git branch -M main
git push -u origin main
```

### 第三步：配置 DeepSeek API Key（用于中文翻译）

1. 前往 [platform.deepseek.com](https://platform.deepseek.com) 注册并创建 API Key
2. 在 GitHub 仓库页面点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. Name 填写：`DEEPSEEK_API_KEY`
5. Value 填写你的 DeepSeek API Key
6. 点击 **Add secret**

> 费用参考：DeepSeek 翻译约 $0.001/篇，每天抓取100篇约 $0.1，非常便宜

### 第四步：开启 GitHub Pages

1. 在仓库页面点击 **Settings** → **Pages**
2. Source 选择：**Deploy from a branch**
3. Branch 选择：`main`，目录选择：`/docs`
4. 点击 **Save**
5. 等待约1分钟，页面会显示你的网站地址：`https://你的用户名.github.io/energy-news/`

### 第五步：手动触发首次抓取

1. 在仓库页面点击 **Actions** 标签
2. 左侧选择 **Fetch & Deploy Energy News**
3. 点击 **Run workflow** → **Run workflow**
4. 等待约3-5分钟，完成后刷新你的 Pages 地址即可看到内容

---

## 自动化说明

- GitHub Actions 每3小时自动运行一次
- 自动抓取 32 个海外能源 RSS 源
- 调用 DeepSeek API 将标题翻译为中文
- 自动生成静态 HTML，推送到 GitHub Pages
- 如果没有新文章，跳过提交（不产生无效 commit）

---

## 添加/删除数据源

编辑 `sources.json` 文件，每个条目格式：

```json
{
  "name": "来源名称",
  "url": "RSS地址",
  "category": "分类名"
}
```

分类可选：`太阳能` `风电` `储能` `氢能` `电网` `电力` `油气` `核能` `EV` `综合` `政策`

---

## 目录结构

```
energy-news/
├── .github/
│   └── workflows/
│       └── fetch.yml        # GitHub Actions 自动化配置
├── templates/
│   └── index.html           # 页面模板
├── data/
│   └── articles.json        # 抓取的文章数据（自动生成）
├── docs/                    # 生成的静态网站（GitHub Pages 托管目录）
├── fetch.py                 # 抓取+翻译主脚本
├── build.py                 # 静态页面生成器
├── sources.json             # 数据源列表
├── requirements.txt         # Python 依赖
└── README.md
```

---

## 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API Key（可选，不设置则保留英文标题）
set DEEPSEEK_API_KEY=你的key

# 运行抓取+生成
python fetch.py

# 用浏览器打开 docs/index.html 预览
```
