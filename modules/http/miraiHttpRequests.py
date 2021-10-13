# encoding utf-8
# name:httpRequest.py
from modules.conf import config
from modules.utils import log as Log
import requests
import time
import threading
import traceback

mirai_config = config.getMiraiConf()


class MiraiHttpRequests:
    sessionKey: str
    host = 'http://%s:%s' % (mirai_config['server'], mirai_config['port'])
    verifyKey = mirai_config['verifyKey']
    botQQ = mirai_config['botQQ']

    _instance_lock = threading.Lock()

    def __new__(cls) -> 'MiraiHttpRequests':
        if not hasattr(MiraiHttpRequests, "_instance"):
            with MiraiHttpRequests._instance_lock:
                if not hasattr(MiraiHttpRequests, "_instance"):
                    MiraiHttpRequests._instance = object.__new__(cls)
        return MiraiHttpRequests._instance

    def __init__(self) -> None:
        pass

    def get(self, func):
        response = self.request.get(
            "%s/%s?sessionKey=%s" % (self.host, func, self.sessionKey))
        response.raise_for_status()
        return response.json()

    def post(self, func, data):
        headers = {'Content-Type': 'application/json'}
        response = self.request.post(
            url="%s/%s" % (self.host, func), json=data, headers=headers)
        response.raise_for_status()
        return response.json()

    def login(self):
        self.request = requests.session()
        last_sessionKey = config.getMiraiConf('sessionKey')
        if last_sessionKey:
            rs = self.post(
                'release', {'sessionKey': last_sessionKey, 'qq': self.botQQ})
            if rs['code'] == 0:
                Log.info(msg=f"release success,sessionKey = {last_sessionKey}")
            else:
                Log.error(msg=f"release error: sessionKey = {last_sessionKey}")
        while True:
            try:
                response = self.post('verify', {'verifyKey': self.verifyKey})
                self.sessionKey = response['session']
                response = self.post(
                    'bind', {'sessionKey': self.sessionKey, 'qq': self.botQQ})
                if response['code'] == 0:
                    Log.info(msg=f'login success,sessionKey = {self.sessionKey}')
                    config.setMiraiConf('sessionKey', self.sessionKey)
                    break
            except Exception:
                Log.error(msg=traceback.format_exc())
                Log.info(msg='login error ---- retry in 5 seconds')
                time.sleep(5)

    def release(self):
        try:
            rs = self.post(
                'release', {'sessionKey': self.sessionKey, 'qq': self.botQQ})
            if rs['code'] == 0:
                Log.info(msg=f"release success,sessionKey = {self.sessionKey}")
                config.setMiraiConf('sessionKey', '')
            else:
                Log.error(msg=f"release error: sessionKey = {self.sessionKey}")
        except Exception:
            Log.error(msg=traceback.format_exc())
