# Dounai Checkin 自动化签到助手

基于 Python 开发的轻量级自动签到工具，支持智能算式验证码识别、动态凭据计算与本地会话保持。

---

### ✨ 功能特性

* **开箱即用**：提供免安装的可执行程序（`.exe`），**无 Python 环境的电脑直接在 Releases 下载即可运行**。
* **智能验证码解析**：基于 `ddddocr` 深度学习框架，内置汉字数字与复杂数学运算符智能纠错清洗逻辑。
* **凭据校验算法**：自动提取页面时效票据（`checkin_ticket`）并计算 SHA-256 签名凭证（`checkin_token`）。
* **24 小时会话持久化**：支持 Cookie 本地缓存与有效期检测，避免高频重复登录。
* **反爬拟人化调度**：内置拟真请求头、现代浏览器指纹以及随机等待延迟，最大程度契合真实交互行为。

---

### 🚀 快速使用指南

#### 方式一：普通用户（无需 Python 环境，最推荐）

如果你只是想使用签到功能，不需要安装任何编程环境：

1. **获取程序**：
   * 前往本仓库右侧的 [Releases 发布页面](https://github.com/Mertred/dounaicheck/releases) 下载最新版本的打包文件（`dounaicheck.zip` 或 `main.exe`）。
2. **准备配置文件**：
   * 将下载的文件解压到一个单独的文件夹中。
   * 直接双击运行一次 `main.exe`，程序会在同级目录下自动生成一个 `config.json` 模板文件，随后提示退出。
3. **填写账号信息**：
   * 用记事本打开生成的 `config.json`，填入你的账号与密码：
     ```json
     {
       "email": "your_email@example.com",
       "passwd": "your_password"
     }
     ```
4. **开始运行**：
   * 再次双击 `main.exe`，程序将全自动完成识别并执行签到。

---

#### 方式二：开发者（通过源码运行）

如果你需要二次开发或在 Linux / macOS / 本地虚拟环境中运行：

1. **克隆仓库并进入目录**：
   ```bash
   git clone [https://github.com/Mertred/dounaicheck.git](https://github.com/Mertred/dounaicheck.git)
   cd dounaicheck