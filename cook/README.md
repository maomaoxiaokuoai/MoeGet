把你的 B站 cookie 放在这个文件夹里即可。

如果准备上传到 GitHub，记得只保留这个说明文件，不要把真实 cookie 一起传上去，不然小饼干就会偷偷跑出去啦。

支持的文件名优先级：
- `bili_cookies.json`
- `bili_cookie.json`
- `cookies.json`
- `cookie.json`
- `bili_cookies.txt`
- `bili_cookie.txt`
- `cookies.txt`
- `cookie.txt`

JSON 可直接写成对象：

```json
{
  "SESSDATA": "...",
  "bili_jct": "...",
  "DedeUserID": "..."
}
```

TXT 可直接写成整段 Cookie：

```txt
SESSDATA=...; bili_jct=...; DedeUserID=...
```
