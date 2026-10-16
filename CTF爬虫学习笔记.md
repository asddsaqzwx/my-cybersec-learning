# CTF Python 爬虫学习笔记

> 适用对象:会基本 Python 语法(变量/循环/函数)的 CTF 新手
> 目标:能解答 BUUCTF 及同类平台的 **中等及以下** 爬虫/自动脚本题
> 学习周期:加速版 **2~3 周**(每天 2~3 小时)

---

## 目录

- 第一部分:加速版学习流程(2~3 周)
- 第二部分:CTF 爬虫核心知识速览
- 第三部分:脚本通用结构详解
- 第四部分:5 个解题模板(逐行讲解)
- 第五部分:BUUCTF 递进题单与做题方法论
- 第六部分:常见坑清单
- 第七部分:自检清单

---

# 第一部分:加速版学习流程(2~3 周)

## 先说清:CTF 里的"爬虫题"考什么

你以为的爬虫题 = 抓网页数据。CTF 里的爬虫题 = **用代码和服务器"对话",按规则完成交互,拿到 flag**。

考点地图:

| 类型 | 解法要点 | 难度 |
|---|---|---|
| 口算/答题集 | 请求拿题目 -> 解析提取 -> POST 提交答案 | ★ |
| 改请求头放行 | 伪造 UA / Referer / Cookie | ★ |
| 登录/会话保持 | session 保持登录态,走多步流程 | ★★ |
| JSON 接口取数 | 翻页收集 -> 拼出 flag | ★★ |
| 抢答/并发 | 多线程、快速提交、限速对抗 | ★★ |
| 定时出 flag | 等到指定时间再请求 | ★★ |
| 伪随机/token 破解 | 预测、重放 | ★★★ |
| 简单反爬/轻验证码 | 图片识别、JS 逆向 | ★★★★ |

**关键结论:解"中等及以下"只需要把这 4 件事做到熟练:**
1. 用 requests 发对请求(GET/POST、请求头、Cookie)
2. 从页面/JSON 里把数据取出来(正则、XPath、json)
3. 让脚本多步交互保持状态(session)
4. 快了就用多线程,慢了就加大脑(重试/换 UA)

## 环境准备(第 0 天,30 分钟)

```powershell
# Windows 下安装依赖
python -m pip install requests lxml bs4
```

```python
# 验证安装
import requests, lxml, bs4
print(requests.__version__)
```

## 第 1 周:地基 + 第一道题

| 天 | 内容 | 产出 |
|---|---|---|
| Day1 | HTTP 核心 + F12 抓包实操(见第二部分) | 能看懂一次请求的完整过程 |
| Day2 | requests 入门:GET/POST、headers、超时 | 写完第一个抓取脚本 |
| Day3 | 数据解析:正则 + XPath/BS4 + JSON | 能从任意页面提取到想要的字段 |
| Day4-5 | 实战:BUUCTF 口算/答题集类题 | 独立提交答案拿 flag |
| Day6 | 保命技能:异常处理、重试、编码 | 脚本不再"脆" |
| Day7 | 整理自己的答题类模板(参考模板A) | 有可复用的武器 |

**检查点**:给你一个"页面里有算式,POST 答案"的题,1 小时内能拿下。

## 第 2 周:会话与并发

| 天 | 内容 | 产出 |
|---|---|---|
| Day8-9 | session 保持登录态、多步流程、Cookie 校验 | 能解登录/签到/领取类题 |
| Day10-11 | 多线程、线程安全收集、限速对抗 | 能解并发抢答类题 |
| Day12-13 | 翻页收集/JSON 接口类(拼 flag)、定时任务类 | 能解收集+定时类题 |
| Day14 | 综合实战:连解 2~3 道中等难度题 | 建立起做题手感 |

**检查点**:给你一道需要"先登录、再翻 5 页、把所有片段拼成 flag"的题,半天内能完成。

## 第 3 周:冲刺(选学,时间紧可砍)

| 天 | 内容 | 产出 |
|---|---|---|
| Day15-16 | 前端加密参数 JS 逆向入门、轻验证码 | 能碰一碰中上难度的题 |
| Day17-21 | 按第五部分题单刷题,总结方法 | 稳定输出 |

> 良心提示:砍掉第 3 周不影响你完成"中等及以下"的目标。第 5 阶段第 16 部分笔记里已经给了完整模板,以后想学再补。

---

# 第二部分:CTF 爬虫核心知识速览

## 1. HTTP 协议(必须懂,不懂就写不好脚本)

### URL 结构

```
http://node4.buuoj.cn:30001/path/to/page?a=1&b=2
 \____/   \_______________/ \___________/ \_____/
  协议         主机:端口        路径        查询参数(?后,GET 传参)
```

### 请求方法(做题基本只碰这两个)

- `GET`:拿资源。参数放在 URL 查询字符串里,默认可缓存。
- `POST`:提交数据。数据放在请求体( body )里,分两种:
  - `application/x-www-form-urlencoded`(表单,普通 `<form>` 提交)→ requests 用 `data=` 传
  - `application/json`(JSON)→ requests 用 `json=` 传

### 状态码(看到就懂)

| 码 | 含义 | 做题时的信号 |
|---|---|---|
| 200 | 成功 | 正常 |
| 301/302 | 重定向(默认 requests 自动跟随) | 可能要登录/换个地址 |
| 403 | 禁止访问 | 检查 UA/Referer/登录态 |
| 404 | 不存在 | 路径写错 |
| 405 | 方法不允许 | 该用 POST 你用了 GET |
| 429 | 请求过多 | 被限速了,加延时/换代理 |
| 500 | 服务器内部错误 | 参数格式不对,或触发条件没满足 |

### 常用请求头(重点:服务器靠"头"识别你是谁)

| 头 | 作用 | 做题场景 |
|---|---|---|
| `User-Agent` | 标识浏览器/客户端 | 服务器按 UA 放行,默认 `python-requests` 容易被识破 |
| `Referer` | 说明从哪个页面跳来的 | 服务器要求从指定页面进入 |
| `Cookie` | 会话凭证(`key=value`) | 登录后必须带着 |
| `Content-Type` | body 的格式 | POST 表格/JSON 时要有对应格式 |
| `Authorization` | 鉴权 token | 有的题要带 token |

### 会话(Cookie)的本质

HTTP 是无状态的。网站靠 **Cookie**(一小段"通行证")记住你:第一次登录服务器签发 Cookie,之后每次请求带上 Cookie,服务器就知道"你是那个已登录的用户"。

`requests.Session()` 会自动记住服务器发的 Cookie 并在后续请求中带上 → **绝大多数多步题的核心**。

### F12 抓包五步(做题人肉"反向工程")

```
1. 按 F12 打开开发者工具
2. 切到 Network(网络)标签,勾上 Preserve log(保留日志)
3. 在页面上做出你要模拟的操作(如提交答案)
4. 在请求列表里找到对应请求,依次看:
   - Headers(请求方法、URL、请求头)
   - Payload / Params(提交的数据长啥样)
   - Preview / Response(返回啥)
5. 在某请求上右键 -> Copy -> Copy as cURL,然后:
   在 https://curlconverter.com 转成 Python requests 代码(复制即用的起手式)
```

> 学习提醒:做题第一步永远不是写代码,而是抓包搞清楚"服务器到底想要什么"。抓包越细,代码越短。

## 2. requests 库速成

```python
import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})

# ---- GET ----
r = session.get("http://target.example.com/page", params={"id": 1})
# params 会拼成 ?id=1

# ---- POST 表单 ----
r = session.post("http://target.example.com/submit",
                 data={"ans": "42"})

# ---- POST JSON ----
r = session.post("http://target.example.com/api",
                 json={"name": "admin"})

# ---- 响应对象常用字段 ----
r.text          # 响应文本(页面源码/JSON字符串)
r.status_code   # 状态码,如 200
r.headers       # 响应头(可能藏 Set-Cookie、flag)
r.json()        # 若响应是 JSON,直接转成 dict/list
r.cookies       # 服务器塞的 Cookie
r.url           # 最终 URL(重定向后)
```

```python
# ---- 常用配置 ----
r = session.get(url,
                timeout=5,          # 超时秒数,不写可能卡死
                allow_redirects=True,  # 是否跟随重定向,默认 True
                proxies={"http": "http://127.0.0.1:7890"})  # 本地代理调试
```

> 编码坑:服务器返回中文乱码时,`r.encoding = r.apparent_encoding` 或 `r.content.decode('utf-8', 'ignore')`,见第六部分。

## 3. 解析三件套(从响应里"抠"数据)

做题基本套路:**拿页面 -> 抠出题目/参数/数据 -> 组织答案 -> 提交**。"抠"有以下三种工具,按需选用:

### (1) 正则 re(最通用,CTF 最常用)

```python
import re

html = '<p id="exp">123 + 456 = ?</p>'
m = re.search(r'<p id="exp">(.*?)</p>', html)   # (.*?) 非贪婪匹配任意字符
if m:
    print(m.group(1))   # 123 + 456 = ?
```

常用写法:
- `re.search(pattern, text)` 找第一个;`.group(1)` 取第一个括号里抓到的内容
- `re.findall(pattern, text)` 找所有,返回 list
- `.*?` 非贪婪:意思是从这开始尽量少地匹配到下一个结束点
- `\d+` 数字、`\w+` 字母数字下划线、`.` 任意字符、`[0-9a-f]+` hex

> 记住:在浏览器里对着源码练习写正则,要提取啥就直接照抄到 pattern,用 `(.*?)` 包住目标。

### (2) XPath / BeautifulSoup(适合结构化 HTML)

```python
from lxml import etree
html = etree.HTML(r.text)
# /html/body/div[@class='exp']/text()  取指定元素文本
texts = html.xpath("//div[@class='exp']/text()")
```

```python
from bs4 import BeautifulSoup
soup = BeautifulSoup(r.text, "html.parser")
soup.find("div", class_="exp").get_text()   # 找第一个 div.exp 的文本
soup.select("p#exp")                        # CSS 选择器,类似 jQuery
```

> 正则学精了大多数口算题都够用;页面结构复杂再上 BS4/XPath。

### (3) json(接口题的主角)

```python
data = r.json()          # 直接把响应变 Python 的 list/dict
for item in data["list"]:
    print(item["value"])
# 最喜欢考:翻页接口返回一堆片段,你收集起来拼 flag
```

## 4. 并发基础(快攻题/抢答题)

```python
from concurrent.futures import ThreadPoolExecutor

def attempt(i):
    # 一次提交尝试,成功返回 True
    ...

with ThreadPoolExecutor(max_workers=20) as pool:
    results = list(pool.map(attempt, range(50)))  # 并发 50 次
```

要点:
- 快攻题 = 服务器窗口期极短(比如"3 秒内必须提交"),脚本必须快、重试要多
- **线程安全**:多线程共享一个 list 或计数时,`results[i] = ...` 或者用 `threading.Lock()` 保护,否则数据会丢
- 被限速(429)时反过来:`time.sleep(0.5)` 加慢,或用代理池换 IP

---

# 第三部分:脚本通用结构详解(老师重点讲)

## 为什么要把脚本分层?

新手写脚本最常见的问题:全部代码堆在 15 行里,题一变就全改,还难查错。

CTF 爬虫题的共性是 **"请求 -> 解析 -> 业务逻辑 -> 提交"** 的循环。分层之后,每道新题你只需要改"业务逻辑"和"解析"两层,请求层基本不动,效率翻倍。

## 一个标准脚本的骨架

```python
# ============ 1. 导入与配置 ============
import requests
import re
import time
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "http://node4.buuoj.cn:30001"   # 换成题目的地址
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TIMEOUT = 5

# ============ 2. 请求层(封装,负责和服务器对话) ============
def get_page(session, url, **kw):
    """带超时和重试的 GET,失败自动重试 3 次"""
    for attempt in range(3):
        try:
            r = session.get(url, timeout=TIMEOUT, **kw)
            if r.status_code == 200:
                return r
            log.warning("status %s, retry %s", r.status_code, attempt)
        except requests.RequestException as e:
            log.warning("request error: %s, retry %s", e, attempt)
        time.sleep(0.3)
    raise RuntimeError(f"GET {url} 失败")

def post_answer(session, url, data):
    """带超时和重试的 POST 提交"""
    for attempt in range(3):
        try:
            r = session.post(url, data=data, timeout=TIMEOUT)
            if r.status_code == 200:
                return r
        except requests.RequestException as e:
            log.warning("post error: %s, retry %s", e, attempt)
        time.sleep(0.3)
    raise RuntimeError(f"POST {url} 失败")

# ============ 3. 解析层(负责从响应里抠数据) ============
def parse_question(html):
    """从页面里提取算式,返回字符串"""
    m = re.search(r"<p id='exp'>(.*?)</p>", html)
    if not m:
        raise ValueError("没有找到题目,页面结构可能变了")
    return m.group(1)

def calc(expr):
    """计算算式。eval 只在自己的题目环境里用,别用在外来网站上"""
    return eval(expr.replace("= ?", ""))   # 练习环境专用

# ============ 4. 业务逻辑(每道题的真正解法) ============
def solve(session):
    page = get_page(session, BASE_URL)
    expr = parse_question(page.text)
    ans = calc(expr)
    log.info("题目: %s -> 答案: %s", expr, ans)
    resp = post_answer(session, BASE_URL, {"ans": ans})
    return resp.text

# ============ 5. main 入口(兜底 + 输出结果) ============
def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        result = solve(session)
        print(result)
        if "flag" in result.lower() or "flag{" in result:
            print("[+] 拿到 flag 了!")
        else:
            print("[-] 还没出 flag,检查答案格式或是否被限速")
    except Exception as e:
        log.error("解题失败: %s", e, exc_info=True)

if __name__ == "__main__":
    main()
```

## 逐模块讲清楚为什么这么写

### 模块1:导入与配置
- 把 URL、UA、超时提成常量放顶部,题目地址变了只改一处
- `logging` 比 `print` 好用:能带时间戳、能控制级别、报错带堆栈

### 模块2:请求层
- 全部请求都走封装函数,统一加 **超时 + 重试**。CTF 环境不稳定,服务器偶发 500 很常见,重试 3 次直接让脚本通过率大涨
- 返回 `session` 对象作为参数传入,而不是内部新建:这样 **Cookie 状态共享**、可复用

### 模块3:解析层
- 一个函数专做一件事:`parse_question` 只管抠题目,`calc` 只管算数
- 抠不到就主动 `raise`,**失败早暴露**,而不是带着空数据往下走到提交完才发现错

### 模块4:业务逻辑
- 这道题剩下的核心步骤串在这里,改题只动这里
- 关键节点用 `log.info` 打出来:题目长啥样、答案是多少,一眼能看出哪一步错了

### 模块5:main 入口
- `if __name__ == "__main__":` 是惯例:脚本被直接运行才进 main,被 import 时不执行
- 全局 try/except:任何一步挂了都有日志,不会黑屏

> 一句话总结这套结构:**请求亲儿子(requests),解析给人看,业务自己动,main 收尾兜底。**

---

# 第四部分:5 个解题模板(逐行讲解)

> 下面每个模板都是完整可运行的结构,`TARGET` 等占位符换成你正在做的题。**先看懂结构,再对题目微调解析和业务逻辑。**

## 模板A:口算 / 答题集类(入门必做)

适用:"页面给你一道算式或问题,POST 答案,答对给 flag(或进入下一题,循环 N 题后出 flag)"。

```python
import requests
import re
import time

BASE_URL = "http://node4.buuoj.cn:30001"   # 换成题目地址
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_question(session):
    """第 1 步:GET 拿页面,抠出题目"""
    r = session.get(BASE_URL, timeout=5)
    r.encoding = r.apparent_encoding          # 防中文乱码
    # 假设题目的算式包在 <div id="exp">...</div> 里,照抄到正则
    m = re.search(r'<div id="exp">(.*?)</div>', r.text)
    if not m:
        print(r.text[:500])                    # 没抠到就把源码打出来肉眼找
        raise SystemExit("没找到题目,看源码里算式长啥样再改正则")
    return m.group(1)

def solve_one(session):
    """第 2 步:算出答案并 POST"""
    expr = get_question(session).replace("= ?", "")
    ans = eval(expr)                           # 练习环境专用;认真算就自己写函数
    print(f"[*] 题目 {expr} = {ans}")
    r = session.post(BASE_URL, data={"ans": ans}, timeout=5)
    return r.text

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    for round_no in range(1, 101):             # 有些题要做满 100 题
        text = solve_one(session)
        if "flag" in text.lower():
            print(f"[+] 第 {round_no} 题后出 flag:")
            print(text)
            break
        time.sleep(0.2)                        # 稍微加慢,防 429
    else:
        print("[-] 100 题做完了没出 flag,检查提交的字段名(是 ans 还是 answer?)")

if __name__ == "__main__":
    main()
```

**遇到这题你该先做的三件事:**
1. F12 手动提交一次答案,看请求的 **字段名**(`ans`?`answer`?`submit`)和 **URL**(提交到哪里)
2. 看返回的页面结构,把算式所在标签抄进正则
3. 确认答对后是不是直接出 flag,还是要循环多题

## 模板B:登录 / 会话类(进阶必做)

适用:"先注册/登录拿到 Cookie,再访问只有登录用户才能看/领的页面"。

```python
import requests
import re

LOGIN_URL = "http://node4.buuoj.cn:30002/login"
TARGET    = "http://node4.buuoj.cn:30002/flag"

def get_csrf(session):
    """有些登录页有 csrf token,先 GET 登录页抠出来"""
    r = session.get(LOGIN_URL, timeout=5)
    m = re.search(r'name="csrf" value="(.*?)"', r.text)
    return m.group(1) if m else None

def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    csrf = get_csrf(session)                    # 有 token 就带上,没有就不用
    payload = {"username": "admin", "password": "admin123"}
    if csrf:
        payload["csrf"] = csrf

    # 第 1 步:POST 登录,登录成功后 Cookie 被 session 自动记住
    r = session.post(LOGIN_URL, data=payload, timeout=5)
    print(f"[*] 登录返回: {r.status_code} | {r.text[:200]}")

    # 第 2 步:带着登录 Cookie 直接 GET 目标页
    r = session.get(TARGET, timeout=5)
    print(r.text)
    # 如果返回 302/403,可能还要 Referer -> 加一行:
    # session.headers["Referer"] = LOGIN_URL

if __name__ == "__main__":
    main()
```

**核心知识点只有一句话:`requests.Session()` 帮你保管 Cookie,别自己手动拼 `Cookie` 头。**

## 模板C:并发抢答 / 窗口期类(中等难度代表)

适用:"服务器给题到必须提交之间的窗口极短"或"同一接口要求你连打多个请求拼数据"。

```python
import requests
import re
import threading
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://node4.buuoj.cn:30003"
NUM_WORKERS = 50

found = []
found_lock = threading.Lock()                # 多线程写共享 list 要加锁

def grab(i):
    """第 i 个并发单元:抢一次,把返回值存进共享列表"""
    try:
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0"})
        r = s.get(BASE_URL + f"/api?index={i}", timeout=5)
        data = r.json()
        with found_lock:
            found.append(data["value"])       # 加锁后再写,避免丢数据
        return data
    except Exception as e:
        return {"error": str(e)}

def main():
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
        list(pool.map(grab, range(50)))       # 并发请求 50 个 index
    with found_lock:
        print("收集到的片段:", found)
    flag = "".join(found)                     # 常见套路:拼起来就是 flag
    print("拼接结果:", flag)

if __name__ == "__main__":
    main()
```

**关键点:**
- `ThreadPoolExecutor(max_workers=N)` 开 N 个线程同时干活,几秒钟顶顺序执行几分钟
- 多线程往同一个 `list` 里写必须用 `Lock`,否则可能丢数据/崩溃
- 窗口期题 = `pool.map` 一次打满;正常接口慎用高并发(小心把题服务器打挂)

## 模板D:翻页收集 / 字典拼接类(中等难度)

适用:"数据分散在每页里,全拿到才能拼出 flag/密码"。

```python
import requests
import re

BASE_URL = "http://node4.buuoj.cn:30004"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})

def fetch_page(page):
    r = SESSION.get(BASE_URL + f"?page={page}", timeout=5)
    r.encoding = r.apparent_encoding
    return r.text

def parse_parts(html):
    # 假设每页有一段 <span class="part">xxx</span>,抠出所有
    return re.findall(r'<span class="part">(.*?)</span>', html)

def main():
    parts = []
    for page in range(1, 11):                 # 共 10 页
        html = fetch_page(page)
        parts += parse_parts(html)
        print(f"[*] 第 {page} 页拿到 {len(parts)} 段")
    print("[+] 全部片段:", parts)
    print("拼接 flag:", "".join(parts))        # 拼完还要注意顺序(按页序拼)

if __name__ == "__main__":
    main()
```

**变体提醒:**
- 有的题片段是散在 JSON 接口里:`data["pages"][i]["frag"]`,照猫画虎换成 `r.json()` 即可
- 有的片段要**按特定顺序**排序,别只按抓取顺序拼——先打印出来肉眼看规律

## 模板E:JS 加密 / 前端参数类(进阶,选学)

适用:"提交前要先算一个前端 JS 生成的 token/签名,比如 md5、时间戳拼接"。

思路分两步:**先看懂前端怎么算的,再在 Python 里算。**

```python
# 第一步:在 F12 里找算 token 的 JS,通常是 <script> 里的一段,例如:
#  var token = md5(user + ":" + passwd + ":" + timestamp);
# 第二步:用 Python 复现(/或用 node 直接执行那段 JS)

import requests
import hashlib
import time

def make_token(user, passwd):
    ts = str(int(time.time()))
    return hashlib.md5((user + ":" + passwd + ":" + ts).encode()).hexdigest()

def main():
    session = requests.Session()
    payload = {
        "username": "admin",
        "password": "secret",
        "timestamp": str(int(time.time())),
        "token": make_token("admin", "secret"),
    }
    r = session.post("http://node4.buuoj.cn:30005/login",
                     data=payload, timeout=5)
    print(r.text)

if __name__ == "__main__":
    main()
```

**JS 逆向三步法:**
1. `Ctrl+F` 在源码里搜提交时用到的参数名(如 `token`、`sign`)看它在哪段 JS 里被赋值
2. 把那段 JS 逻辑读懂,常用库:`hashlib`(md5/sha1)、`hmac`、`base64`、`time` 都能在 Python 里复现
3. 复现不出来就 `execjs`(需装 node)或固定值照样抄:`execjs.compile(js_code).call("func", args)`

---

# 第五部分:BUUCTF 递进题单与做题方法论

## 做题方法论:五步法(每题都走一遍)

```
1. 读题   : 题目描述里往往给线索("先登录"、"一共 100 题"、"flag 藏在响应头")
2. 看页面 : 浏览器打开,肉眼观察结构
3. 抓包   : F12 模拟操作,看请求方法/URL/参数/请求头
4. 写脚本 : 按第四部分的模板套,改解析和业务逻辑
5. 验证   : 跑脚本 -> 拿不到就:
              a. 打印响应前 500 字符,看服务器到底回什么
              b. 回抓包那步,对比你脚本发的和浏览器发的差在哪
              c. 查第六部分常见坑清单
```

**拿不到 flag 时的排错顺序(重要!):** 状态码 -> 请求头(UA/Cookie/Referer) -> 参数名与格式 -> 编码乱码 -> 限速/窗口期 -> 前面某步被重定向。

## 递进题单(按难度排序练习)

> 说明:BUUCTF 平台题目/环境地址会变动,这里给的是**题型顺序**,顺着找同类题练即可;做题优先选 Python 环境能跑、有提示的题。

### 第 1 级:热身(学会跑通 requests)
- 找最简单的 GET 题:打开就看得到 flag,写在源码/响应里的
- 练手点:F12 看响应、`r.text` 输出、`r.headers`(有的 flag 就在响应头!)

### 第 2 级:口算 / 答题集(解析与 POST)
- 页面给算式、提交答案类的题
- 练手点:正则抠题、`eval` 算数、POST 提交、循环多题
- 难度进阶点:算式藏在 JS 里 / 提交字段名要多试几种(`ans`/`answer`/`submit`)

### 第 3 级:登录 / 会话类(状态保持)
- 需要 username/password 登录后访问受限页面的题(账号密码常在源码注释/`robots.txt`/题面里)
- 练手点:`Session()` 自动带 Cookie、csrf token 提取、Referer 校验

### 第 4 级:收集拼 flag 类(翻页/JSON)
- 数据分页/分段,集齐所有片段拼 flag 的题
- 练手点:`r.json()`、循环翻页、顺序拼接、`re.findall`

### 第 5 级:并发 / 抢答类(多线程)
- 要求快速连续请求、或窗口期极短的题
- 练手点:线程池、线程安全锁、限速与重试的配合

### 第 6 级:中等偏上(进阶)
- 限速反爬(429)、UA/Referer/Cookie 组合校验、token 预测、定时任务
- 练手点:代理池、暂停重试、requests 层面模拟全套浏览器行为

## 刷题技巧
- **每解完一道题,写"这题的 3 个要点"**:下次同类题秒解
- **卡 2 小时就放下**:去群里搜题目名,看别人解法,把"没想到的步骤"记下来(这是最快的进步)
- 好题值得二刷:第一遍抄着做,第二遍关掉题解独立做,第三遍换种思路做

---

# 第六部分:常见坑清单(做题前先背)

| # | 坑 | 症状 | 解法 |
|---|---|---|---|
| 1 | 中文乱码 | 响应里中文全是 `â€` | `r.encoding = r.apparent_encoding` 或 `r.content.decode('utf-8', 'ignore')` |
| 2 | 被 UA 识破 | 返回 403/反爬提示 | 伪造浏览器 UA(模板里给了) |
| 3 | 会话失效 | 第二步请求 302/登录页 | 登录和后续请求必须用同一个 `session`,且别 `close()` |
| 4 | 字段名错 | 提交了但一直"答案错误" | F12 抓包看真实字段名,试 `ans/answer/submit/flag` |
| 5 | 被限速 | 大量 429 | `time.sleep(0.2~1)` 加慢;或换 UA/代理轮换 |
| 6 | 卡死不返回 | 脚本像死了一样 | 所有请求加 `timeout=5`,加重试 |
| 7 | 重定向丢状态 | 登录后被踢 | `session.get(url, allow_redirects=False)` 看 Location,手动处理 |
| 8 | 正则抠不对 | `re.search` 返回 None | 先 `print(r.text[:500])` 肉眼对照再写正则;注意标签属性顺序 |
| 9 | 数字/格式问题 | 答案对但判错 | 答案可能要求去空格/保留小数/加 `=答案`;先打印你提交啥 |
| 10 | eval 出危险 | 外来页面代码被执行 | 只在练习环境用;真实站点解析请手写逻辑 |
| 11 | 时间/时区 | 定时题总是差点 | 服务器时间未必是你本地时间,先 `Date` 头/Python 对齐,再 sleep 到点 |

## 保命技能速查

```python
# 重试 + 超时(已经封装进模板的请求层)
for attempt in range(3):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            break
    except requests.ConnectionError:
        time.sleep(0.5)

# 把响应直接落盘,肉眼分析(调试神技)
open("debug.html", "w", encoding="utf-8").write(r.text)

# 打印所有响应头(看有没有 cookie / 权限 / flag)
for k, v in r.headers.items():
    print(f"{k}: {v}")
```

---

# 第七部分:自检清单

## 第 1 周结束自检(能答"是"就过关)
- [ ] 能说出 GET/POST 区别,以及 `data=` 和 `json=` 的适用场景
- [ ] 会用 F12 抓到一次请求的 URL、请求头、提交参数
- [ ] 能独立写完"GET 页面 -> 正则抠数据 -> POST 提交"的脚本
- [ ] 口算类题:不看笔记能独立解出一题
- [ ] 会给所有请求加超时和重试

## 第 2 周结束自检
- [ ] 能说清 `Session()` 为什么能保持登录态
- [ ] 登录 -> 访问受限页 -> 拿 flag,独立完成
- [ ] 会写多线程脚本,且知道为什么要加锁
- [ ] 翻页收集 + 顺序拼接类题敢独立上手
- [ ] 遇到拿不到 flag,能按"状态码->请求头->参数->编码->限速"顺序排错

## 达标标准(中等及以下)
- [ ] 拿到一道题,能先抓包再写脚本(顺序正确)
- [ ] 最常用的四件套(requests/session/正则/线程池)不查笔记直接写
- [ ] 卡住时知道去哪查(响应前 500 字、抓包对比、坑清单)
- [ ] 已经独立解掉至少 5 道 BUUCTF 爬虫类题

---

## 附:学习建议与资源

- 官方文档速查:https://requests.readthedocs.io 、PYPI 的 `requests` 页
- 正则在线调试:https://regex101.com(粘贴测试,别在题页面调试反复请求刷服务器)
- cURL 转 Python:https://curlconverter.com
- 刷题时控制频率与礼貌:爬虫题的服务器是比赛环境,别用极高并发打爆它

> 最后一句老师的忠告:**爬虫题考察的不是"多会爬",而是"多会看"。抓包看得懂,代码就短;抓包糊里糊涂,代码越多越错。做题时永远先打开 F12。**