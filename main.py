# coding=utf-8
import json
import re
import time

import jieba.analyse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
from flask import Flask, redirect, render_template, request, url_for
from scipy.misc import imread
from weibo import APIClient
from wordcloud import ImageColorGenerator, WordCloud

from config import *


app = Flask(__name__)


def name2uid(username):
    """ 昵称转uid """
    client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET,
                       redirect_uri=CALLBACK_URL)
    client.set_access_token(ACCESS_TOKEN, EXPIRES_IN)
    try:
        results = client.users__show(screen_name=username)
        uid = client.users__show(screen_name=username)['id']
    except:
        return ''
    return str(uid)


def save_file(all_text):
    fname = str(int(time.time()*1000))
    with open('userWeibo/' + fname + '.txt', 'wb') as f:
        for i in range(len(all_text)):
            f.writelines(all_text[i].encode('utf-8'))
            f.writelines('\n')
    f.close()
    return fname


def read_file(fname):
    all_text = []
    del_words = DEL_WORDS
    with open('userWeibo/' + fname + '.txt', 'rb') as f:
        for line in f:
            text = re.sub('\[.*\]|\n', '', line.decode('utf-8'))
            for w in del_words:
                text = re.sub(w, '', text)
            all_text.append(text)
        f.close()
    return all_text


def word2cloud(textlist, fname):
    """ 生成词云 """
    fulltext = ''
    isCN = 1
    fname += '.png'
    back_coloring = imread("bg.png")
    cloud = WordCloud(font_path='font.ttf',  # 若是有中文必须添加font.tff
                      background_color="white",  # 背景颜色
                      max_words=1800,  # 词云显示的最大词数
                      mask=back_coloring,  # 背景图片
                      max_font_size=100,  # 字体最大值
                      random_state=42,
                      width=1000, height=860, margin=2,  # 设置图片大小和词边距
                      )
    for li in textlist:
        fulltext += ' '.join(jieba.analyse.extract_tags(li, topK=4))
    wc = cloud.generate(fulltext)
    image_colors = ImageColorGenerator(back_coloring)
    plt.figure("wordc")
    plt.imshow(wc.recolor(color_func=image_colors))
    wc.to_file('static/userImg/' + fname)
    return fname


@app.route('/getContent', methods=['POST', 'GET'])
def weibo_spider():
    """ 开始爬取微博 """
    username = None
    number = None
    headers = {
        'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0',
        'Host': 'm.weibo.cn',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cookie': '_T_WM=e25a28bec35b27c72d37ae2104433873; WEIBOCN_WM=3349; H5_wentry=H5; backURL=http%3A%2F%2Fm.weibo.cn%2F; SUB=_2A250zXayDeThGeVJ7VYV8SnJyTuIHXVUThr6rDV6PUJbkdBeLRDzkW1FrGCo75fsx_qRR822fcI2HoErRQ..; SUHB=0sqRDiYRHXFJdM; SCF=Ag4UgBbd7u4DMdyvdAjGRMgi7lfo6vB4Or8nQI4-9HQ4cLYm_RgdaeTdAH_68X4EbewMK-X4JMj5IQeuQUymxxc.; SSOLoginState=1506346722; M_WEIBOCN_PARAMS=featurecode%3D20000320%26oid%3D3638527344076162%26luicode%3D10000011%26lfid%3D1076031239246050; H5_INDEX=3; H5_INDEX_TITLE=%E8%8A%82cao%E9%85%B1',
        'DNT': '1',
        'Connection': 'keep-alive',
    }
    if request.method == 'POST':
        username = request.form['uid']
        number = request.form['num']
        number = int(number)
    uid = name2uid(username)

    if (uid == ''):
        return 'User does not exist'

    url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value=' + uid + '&containerid=107603'+uid+'&page={page}'
    refer = 'https://m.weibo.cn/api/container/getIndex?type=uid&value=' + uid + '&containerid=107603' + uid
    r = requests.get(url=refer)
    all_counts = json.loads(r.text)['data']['cardlistInfo']['total']  # 获取用户所有微博数量

    if (number > all_counts):
        return u"你所有的微博条数小于%s，请重新输入" % number
    else:
        all_counts = number

    all_text = []  # 保存所有微博内容
    flag = 1
    page = 1
    weibo_counts = 0

    while True:
        try:
            # print(u'正在爬取第%s页' % page)
            req = requests.get(url=url.format(page=page), headers=headers)
            weibo_content = json.loads(req.text)['data']['cards']
            page += 1
        except:
            pass
        if req.status_code == 200:
            for i in weibo_content:
                try:
                    weibo_text = re.sub('<.*?>', '', i['mblog']['text'])  # 文本内容
                    # weibo_time = i['mblog']['created_at']  # 时间
                    weibo_counts += 1
                    if weibo_counts == all_counts or weibo_counts == all_counts:
                        flag = 0
                        break
                    all_text.append(weibo_text)
                except:
                    return "未知错误"
        if flag == 0:
            break

    fname = save_file(all_text)  # 保存微博文本内容
    image = fname + '.png'
    text = read_file(fname)
    word2cloud(text, fname)  # 文本转图片
    return redirect(url_for('show_img', img=image))


@app.route('/')
def index():
    return render_template('weibocloud.html')


@app.route('/img=<img>', methods=['POST', 'GET'])
def show_img(img):
    return render_template('img.html', img=img)


if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0')
