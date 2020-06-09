import tornado.ioloop
import tornado.web
import hashlib
import web
import requests
import time
import os

import recieve
import generateResponseText as grt


# ----------------------------------------------------------------
# 基本配置
# ----------------------------------------------------------------
PORT = 8000
APPID = 'wx63a775ce1f72fbcd' # 公众号ID
APPSECRET = '9f9e596b13d6d5439e0b11b00ec9c415' # 公众号密钥
REDIRECT_URI = 'http://c2m.tq.yhlcps.com/backend/getUserInfo' # 回调URL，需要在公众号中配置
SCOPE = 'snsapi_userinfo' # 弹出授权页面，可通过openid拿到昵称、性别、所在地。并且， 即使在未关注的情况下，只要用户授权，也能获取其信息
# ----------------------------------------------------------------


# ----------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------
class Hello(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")


# 等待用户同意(如果需要的话)，然后重定向到第二步负责的Handler, 发送带有'code'的请求
class GetUserInfoFirstStep(tornado.web.RequestHandler):
    def get(self):
        # 第一步：后端重定位到微信提供的接口URL，让用户同意授权后，微信服务器会跳转到回调地址并携带code参数
        source_url = 'https://open.weixin.qq.com/connect/oauth2/authorize'\
            + '?appid={APPID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPE}'\
            + '#wechat_redirect'
        url = source_url.format(APPID = APPID, REDIRECT_URI = REDIRECT_URI, SCOPE = SCOPE)
        
        # 准备重定向参数
        self._url = url
        self._permanent = True

        # 重定向
        self.redirect(self._url, permanent=self._permanent)


# 拿到'code', 向wx服务器请求用户信息, 收到信息后解析
class GetUserInfoSecondStep(tornado.web.RequestHandler):
    def get(self):
        # 第二步：通过code换取网页授权access_token
        code = self.get_argument('code')
        print('code', code)
        source_url = 'https://api.weixin.qq.com/sns/oauth2/access_token?'\
            +'appid={APPID}&secret={APPSECRET}&code={CODE}&grant_type=authorization_code'
        access_token_url = source_url.format(APPID=APPID, APPSECRET=APPSECRET, CODE=code)
        resp = requests.get(access_token_url)
        data = eval(resp.text) # 将字符串转为字典
        print('data:\n', data)
        access_token = data['access_token']
        openid = data['openid']

        # 第三步：刷新access_token（如果需要）

        # 第四步：拉取用户信息(需scope为 snsapi_userinfo)
        source_url = 'https://api.weixin.qq.com/sns/userinfo'\
            + '?access_token={ACCESS_TOKEN}&openid={OPENID}&lang=zh_CN'
        useinfo_url = source_url.format(ACCESS_TOKEN = access_token, OPENID = openid)
        resp = requests.get(useinfo_url)
        data = eval(resp.text)
        # print(data)``
        userinfo = {
            'nickname': data['nickname'],
            'sex': data['sex'],
            'province': data['province'],
            'city': data['city'],
            'country': data['country'],
            'headimgurl': data['headimgurl']
        }

        print(userinfo)
        # 准备重定向参数
        self._url = 'http://www.baidu.com'
        self._permanent = True

        # 重定向
        self.redirect(self._url, permanent=self._permanent)


# 识别用户消息的关键字并自动回复
class HandleWeiXinMessage(tornado.web.RequestHandler):
        
    def get(self):
        signature = self.get_argument('signature')
        timestamp = self.get_argument('timestamp')
        nonce = self.get_argument('nonce')
        echostr = self.get_argument('echostr')
        token = "dropofsinodropofsino"

        list = [token, timestamp, nonce]
        list.sort()
        s = list[0] + list[1] + list[2]
        hashcode = hashlib.sha1(s.encode('utf-8')).hexdigest()
        # print( "handle/GET func: hashcode, signature: ", hashcode, signature)
        if hashcode == signature:
            self.write(echostr)
        else:
            self.write('fail...')
 
    def post(self):
        app_root = os.path.dirname(__file__)
        templates_root = os.path.join(app_root, 'templates')
        render = web.template.render(templates_root)
        # try:
        webData = self.request.body
        webData = str(webData, encoding='utf8')
        # print("Handle Post webdata is:\n", webData)
        # 打印消息体日志
        recMsg = recieve.parse_xml(webData)
        # print('recMsg', recMsg)
        
        if isinstance(recMsg, recieve.Msg) and recMsg.MsgType == 'text':
            toUser = recMsg.FromUserName
            fromUser = recMsg.ToUserName

            # get content from grt
            content = grt.producer(recMsg.Content)

            # content = "欢迎关注云海流工业互联网平台系统！您发送的文字我们收到了哟～"
            #  + str(recMsg.Content)
            print('Reply message info:')
            print('toUser =', toUser)
            print('fromUser = ', fromUser)
            print('content = ', content)
            print('# ' + '-' * 40 + ' #')
            res = str(render.reply_text(toUser, fromUser, int(time.time()), content))
            self.write(bytes(res, encoding = "utf8"))

        elif isinstance(recMsg, recieve.Msg) and recMsg.MsgType == 'image':
            toUser = recMsg.FromUserName
            fromUser = recMsg.ToUserName
            content = "欢迎关注云海流工业互联网平台系统！您发送的是图片嗷～"
            res = str(render.reply_text(toUser, fromUser, int(time.time()), content))
            self.write(bytes(res, encoding = "utf8"))

        else:
            if isinstance(recMsg, recieve.Msg):
                print("不支持的消息类型：", recMsg.MsgType)
                toUser = recMsg.FromUserName
                fromUser = recMsg.ToUserName
                content = "欢迎关注云海流工业互联网平台系统！当前还不支持这种消息呢～"
                res = str(render.reply_text(toUser, fromUser, int(time.time()), content))
                self.write(bytes(res, encoding = "utf8"))
            else:
                print("这是一个不支持的消息类型，recMsg的值为：", recMsg)

            


def make_app():
    return tornado.web.Application([
        (r"/backend/hello", Hello),
        (r"/backend", GetUserInfoFirstStep),
        (r"/backend/getUserInfo", GetUserInfoSecondStep),
        (r'/backend/wx', HandleWeiXinMessage)
    ], debug=True)

if __name__ == "__main__":
    app = make_app()
    app.listen(PORT)
    print(f'server start at {PORT}......')
    tornado.ioloop.IOLoop.current().start()