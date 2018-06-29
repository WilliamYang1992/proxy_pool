# coding: utf-8

import base64
import logging
import re
import time


class ProxyPool:
    def __init__(self, settings):
        # 是否开启代理ip池
        self.enabled = settings.get('PROXY_POOL_ENABLED')
        if not self.enabled:
            return
        # 默认下载延时
        self.download_delay = settings.get('DOWNLOAD_DELAY')
        # 代理ip, 格式为(proxy, user_pass, error_count)
        self.proxies = []
        # 代理ip文件路径
        self.proxy_file_path = settings.get('PROXY_FILE_PATH')
        # 代理ip总数
        self.proxies_count = 0
        # 代理ip最大的错误次数限制值, 超过即将其删除
        self.proxy_error_threshold = settings.get('PROXY_ERROR_THRESHOLD')
        self.logger = logging.getLogger('scrapy.downloadermiddlewares.proxy_pool')

        if self.proxy_file_path is None:
            raise KeyError('PROXY_LIST setting is missing')

        with open(self.proxy_file_path) as f:
            for line in f.readlines():
                line = line.strip()
                parts = re.match('(\w+://)([^:]+?:[^@]+?@)?(.+)', line)
                if not parts:
                    continue
                proxy = parts.group(1) + parts.group(3)
                if parts.group(2):
                    # 同时删除后面的`@`
                    user_pass = parts.group(2)[:-1]
                else:
                    user_pass = ''
                proxy_item = [proxy, user_pass, None, 0]
                self.proxies.append(proxy_item)
        self.proxies_count = len(self.proxies)
        print('Proxies count: {}'.format(self.proxies_count))

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        if not self.enabled:
            return
        if len(self.proxies) == 0:
            raise ValueError('All proxies are unusable, cannot proceed')

        proxy_item = self.proxies.pop(0)
        request.meta['proxy_item'] = proxy_item
        proxy_address, proxy_user_pass, last_used, _ = proxy_item
        request.meta['proxy'] = proxy_address
        # 如果含有认证信息, 则加入认证Header
        if proxy_user_pass:
            basic_auth = 'Basic ' + base64.b64encode(proxy_user_pass.encode()).decode()
            request.headers['Proxy-Authorization'] = basic_auth
        # 检查距离上次使用时间
        now = time.time()
        if last_used is None:
            delay = 0
        else:
            interval = now - last_used
            if interval >= self.download_delay:
                delay = 0
            elif 0 <= interval < self.download_delay:
                delay = self.download_delay - interval
            else:
                delay = self.download_delay
        # 设置下一次延时
        spider.download_delay = delay

        self.logger.info('Using proxy <{}>, {} proxies left, delay {:.3f}s'.format(
            proxy_address, len(self.proxies), delay)
        )

    def process_response(self, request, response, spider):
        if not self.enabled:
            return response
        proxy_item = request.meta.get('proxy_item')
        if proxy_item:
            # 如果该proxy成功返回响应, 即清空错误记录
            proxy_item[-1] = 0
            proxy_item[2] = time.time()
            self.proxies.append(proxy_item)
        return response

    def process_exception(self, request, exception, spider):
        if not self.enabled or 'proxy' not in request.meta:
            return
        proxy_item = request.meta.get('proxy_item')
        if proxy_item:
            self.logger.error('Proxy: {}, {} failed'.format(proxy_item[0], proxy_item[-1]))
            proxy_item[-1] += 1
            proxy_item[2] = time.time()
            if proxy_item[-1] <= self.proxy_error_threshold:
                self.proxies.append(proxy_item)
            else:
                self.logger.info(
                    'Removing failed proxy <%s>, %d proxies left'.format(proxy_item[0], len(self.proxies))
                )
