#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Description: 链接地址快览,调用的outline接口(此插件仅面向不支持某些卡片预览的QQ(win10应用商店版),outline接口需跨海)
@Date     :2021/07/19 15:22:04
@Author      :yuejieyao
@version      :1.0
'''

from ..miraiPlugin import MiraiMessagePluginProcessor
from modules.message.messageChain import MessageChain
from modules.message.messageType import Plain, Image, App, Xml
from modules.http.miraiMessageRequest import MiraiMessageRequest as MsgReq
from .modules.utils.drawBilibiliImg import binfo_image_create
import requests
import re
import os
from lxml import etree
from PIL import Image as IMG
from io import BytesIO
import time
import json


@MiraiMessagePluginProcessor.mirai_group_message_plugin_register('UrlThumb')
class UrlThumb:
    NAME = "Url快览"
    DESCRIPTION = """发送内容包含url地址时触发"""

    # 缓存目录
    temp_path = os.path.join(os.path.dirname(__file__), 'cache')

    def process(self, chains: MessageChain, group: int, target: int,  quote: int):
        urls = []
        if chains.has(App):
            json_msg = json.loads(chains.get(App)[0].content)
            try:
                desc = json_msg['desc']
                if desc == '新闻':
                    urls.append(json_msg['meta']['news']['jumpUrl'])
            except KeyError:
                pass
            else:
                urls.append(json_msg['meta']['detail_1']['qqdocurl'])
        if chains.has(Xml):
            xml_msg = etree.fromstring(chains.get(Xml)[0].xml.encode('utf-8'))
            try:
                urls.append(xml_msg.xpath('/msg/@url')[0])
            except IndexError:
                pass
            else:
                pass
        else:
            urls.extend(re.findall(
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', chains.asDisplay()))
        if len(urls) > 0:
            for url in urls:
                if "b23.tv" in url:
                    url = self.b23_extract(url)
                p = re.compile(r'av(\d{1,12})|BV(1[A-Za-z0-9]{2}4.1.7[A-Za-z0-9]{2})')
                video_number = p.search(url)
                if video_number:
                    video_number = video_number.group(0)
                    if video_number:
                        video_info = self.video_info_get(video_number)
                        if video_info:
                            if video_info["code"] != 0:
                                MsgReq().sendGroupMessage(msg=MessageChain(
                                    [Plain(text=f'解析到B站视频:{video_number},但视频不存在')]), target=group)
                            else:
                                try:
                                    save_path = os.path.join(self.temp_path, 'bilibili_thumb.jpg')
                                    if binfo_image_create(video_info=video_info, save_path=save_path):
                                        MsgReq().sendGroupMessage(msg=MessageChain(
                                            [Image(image_type='group', file_path=save_path)]), target=group)
                                except Exception:
                                    MsgReq().sendGroupMessage(msg=MessageChain(
                                        [Plain(text=f"B站视频{video_number}解析失败")]), target=group)
                else:
                    MsgReq().sendGroupMessage(msg=self.outline(url), target=group)
                time.sleep(1)  # 防调用频率过快

    def outline(self, url: str) -> MessageChain:
        api_url = f"https://api.outline.com/v3/parse_article?source_url=%s" % url
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36",
            "Referer": "https://outline.com/",
        }

        try:
            response = self.get(url=api_url, headers=headers)
            result = response.json()
            if 'data' in result:
                msg = MessageChain([Plain(text='[快览] %s\n' % url),
                                    Plain(text='[title] %s\n' % result['data']['title'])])
                if 'description' in result['data']:
                    msg.append(Plain(text='[description] %s\n' %
                                     result['data']['description']))
                if 'domain' in result['data']:
                    domain = result['data']['domain']

                    # icon缓存文件名
                    path = os.path.join(self.temp_path, f"{domain.replace('.','_')}.png")
                    # 如果没有就创建,有就直接调取发送
                    if not os.path.exists(path):
                        try:
                            resp = self.get(
                                url=f'https://www.google.com/s2/favicons?domain={domain}')
                            image = IMG.open(BytesIO(resp.content))
                            image.save(path)
                        except:
                            pass
                    if os.path.exists(path):
                        msg.extend([
                            Plain(text='[favicon]\n'),
                            Image(image_type='group', file_path=path)
                        ])
                return msg
            else:
                msg = MessageChain([Plain(text='outline未返回数据')])
                return msg
        except:
            msg = MessageChain([Plain(text='outline调用失败')])
            return msg

    def get(self, url, headers=None) -> requests.Response:
        response = requests.session().get(url=url, headers=headers)
        response.raise_for_status()
        return response

    def b23_extract(self, text):
        b23 = re.compile(r'b23.tv\\/(\w+)').search(text)
        if not b23:
            b23 = re.compile(r'b23.tv/(\w+)').search(text)
        url = f'https://b23.tv/{b23[1]}'
        resp = self.get(url)
        r = str(resp.url)
        return r

    def video_info_get(self, id):
        if id[:2] == "av":
            video_info = self.get(f"http://api.bilibili.com/x/web-interface/view?aid={id[2:]}")
            video_info = video_info.json()
        elif id[:2] == "BV":
            video_info = self.get(f"http://api.bilibili.com/x/web-interface/view?bvid={id}")
            video_info = video_info.json()
        return video_info
