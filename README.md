# proxy_pool
适用于Scrapy的IP代理池middleware, 针对单个IP不能连续爬取需要延时的需求

### 使用说明
在scrapy的settings文件中设置
```
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
    'yourproject.middlewares.proxy_pool.ProxyPool': 100,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
}
```
即可添加该middleware  
使用前需要手动将ip地址按照每行一个的格式放置在文本文件中  
如:  
```
https://1.1.1.1:100
http://2.2.2.2:200
```

### 相关配置
```
PROXY_POOL_ENABLED     # 代理IP池是否启用  
PROXY_FILE_PATH        # 代理IP文件路径  
PROXY_ERROR_THRESHOLD  # 代理IP最大允许错误次数
```
