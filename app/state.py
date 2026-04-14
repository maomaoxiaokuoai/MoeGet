from __future__ import annotations

import random
from pathlib import Path

from PyQt6.QtGui import QColor

from utils.bili_cookie import load_bili_cookies, save_bili_cookies

HITOKOTO_LIST = [
    # 🌸 治愈系
    "🌸 生活明朗，万物可爱。要开心呀~", "🍓 愿一切美好，都如期而至。", "🎐 宇宙山河浪漫，生活点滴温暖，都值得我前进。",
    "🌙 晚风踩着云朵，月亮贩售快乐。", "🍀 愿所有的后会有期，都是它日的别来无恙。", "☕ 世界那么大，总有一个角落为你留着温暖。",
    "🌻 只要心里有阳光，到哪里都是晴天。", "🍃 允许一切发生，做最真实的自己就好啦。", "📖 慢慢来，好戏都在平淡的烟火里。",
    "🕊️ 阳光碎在桌面上，今天也是温柔的一天。", "🕯️ 愿你三冬暖，愿你春不寒，愿你天黑有灯，下雨有伞。", "💌 把烦恼写在纸上，折成纸飞机扔进风里吧！",
    "🍵 喝杯热茶，揉揉小猫，日子慢一点也没关系。", "🌾 所有的失去，都会以另一种方式归来。", "💡 你是一个特别美好的人，要永远相信这一点。",
    "🛁 泡个热水澡，把一天的疲惫都洗掉吧~", "🧸 累了就抱抱小熊，明天依然是个好天气。", "📻 听一首老歌，看一部老电影，时光温柔。",
    "🪴 种自己的花，爱自己的宇宙。", "🥛 睡前喝杯温牛奶，做一个甜甜的梦。",
    # 🐾 卖萌系
    "🐾 别着急，好运正在骑着小黄车赶来的路上。", "🍡 甜甜的句子还没想好，甜甜的我你可以先尝一口。", "🧸 只要一直可爱，烦恼就会变成泡沫飞走啦！",
    "🚀 哔哔哔——接收到宇宙级别的可爱信号！", "🍩 生活不仅有苦，还有满是糖霜的甜甜圈。", "🐰 揪住兔子的耳朵，悄悄把好运塞进你口袋。",
    "🐣 破壳而出的小鸡说：今天也要叽叽喳喳地快乐！", "🐷 哼哧哼哧，我要把所有的快乐都拱到你面前。", "👻 偷偷发个芽，变成一朵超级可爱的小蘑菇。",
    "🪄 妈咪妈咪哄！把你今天的坏心情全部变没！", "🎀 报告！你的小可爱已上线，请查收~", "🎈 抓紧手中的气球，不要让好心情飞走咯~",
    "🦆 冲鸭！就算摔倒也要保持可爱的姿势！", "🦖 小恐龙嗷呜一口，吃掉了所有的不开心。", "🦄 骑上我的小独角兽，去彩虹桥上溜一圈。",
    "🐟 吐个泡泡，咕噜咕噜，把烦恼沉到水底。", "🐹 像仓鼠一样把脸颊塞满，是对美食最大的尊重。", "🦦 海獭搓搓脸，今天又是精神满满的一天！",
    "🦔 虽然长了刺，但内心依然柔软呀。", "🐛 即使是一条毛毛虫，也要努力变成漂亮的蝴蝶！",
    # 🎨 唯美系
    "🐳 往心里装一片大海，再装一些少女心。", "🎨 你是落日弥漫的橘，天边透亮的星。", "🎵 戴上耳机，把世界调成自己的频道。",
    "🍧 夏天的风，带有草莓刨冰的甜味。", "☁️ 凡是过往，皆为序章。冲鸭！", "🌌 星光即使微弱，也会为迷路的人指引方向。",
    "❄️ 每一片雪花，都是冬日寄给大地的信。", "🍂 秋风拂过，落叶写满了对季节的思念。", "🌊 海浪拍打礁石，那是大海在诉说古老的秘密。",
    "⛰️ 山川不语，却有着包容万物的力量。", "🌅 晨曦微露，又是全新且充满希望的开始。", "🌃 城市灯火阑珊，总有一盏为你而亮。",
    "🎇 烟花绽放的瞬间，许下的愿望一定能实现。", "🌉 走过长长的桥，对岸是繁花似锦的未来。", "🛤️ 沿着铁轨一直走，去寻找诗和远方。",
    "🎠 旋转木马不停歇，兜兜转转总会相遇。", "🎡 摩天轮转到最高处，离星星会更近一点吗？", "🎈 升空的不仅是气球，还有无尽的幻想。",
    "🕊️ 白鸽飞过广场，带走了最后一点忧愁。", "🌿 树叶间漏下的光斑，是时光作的画。",
    # ✨ 元气系
    "✨ 保持热爱，奔赴山海。今天也是元气满满！", "🎀 祝你今天愉快，明天的愉快留着我明天再祝。", "🍉 揣着一口袋的开心，满载而归。",
    "🍋 开启每天的元气，需要一颗酸甜的柠檬糖！", "🔥 哪怕只有一点点光，也要努力发亮！", "🏃‍♀️ 跑起来吧，风会为你欢呼！",
    "🧗‍♂️ 每一次攀登，都是为了看到更广阔的风景。", "💪 拍拍肩膀，告诉自己：你已经做得很棒啦！", "🌟 披星戴月走过的路，终将会繁花满地。",
    "🌱 每天进步一点点，小草也能长成大树。", "🚀 目标是星辰大海，怎么能在这里停下脚步！", "🌈 风雨过后一定会有彩虹，再坚持一下下！",
    "☀️ 把太阳装进心里，走到哪里都有光芒。", "🏆 今天的努力，是为了明天能更骄傲地微笑。", "🔋 电量已充满，准备好迎接新的挑战啦！",
    "🦅 像鹰一样展翅高飞，去触摸云端的梦想。", "🦁 保持雄狮般的勇气，无惧前方的艰难险阻。", "⛵ 扬起风帆，向着名为未来的彼岸航行。",
    "⏰ 滴答滴答，不要辜负每一寸宝贵的时光。", "🗺️ 世界那么大，快去地图上画下自己的足迹。",
    # 😜 吃货俏皮系
    "🍟 万物皆可炸，只要火候足，烦恼也能炸得酥脆！", "🍔 卡路里是什么？好吃才是王道！", "🍦 冰淇淋在化掉之前，一定要被我吃掉！",
    "🍕 披萨的拉丝，是对嘴巴最深情的挽留。", "🌭 热狗说：我不是狗，我是美食的化身！", "🌮 卷饼卷起了一切，唯独卷不住我的胃口。",
    "🥞 煎饼翻个面，生活也要有滋有味。", "🥪 三明治夹着火腿，也夹着我对你的想念。", "🥟 饺子包着福气，一口咬下去全是幸福。",
    "🍜 面条顺溜溜，日子也要顺顺利利。", "🍲 火锅咕噜咕噜，没有什么是一顿火锅解决不了的！", "🍣 寿司蘸点芥末，生活偶尔也需要一点刺激。",
    "🍰 蛋糕切一块，甜蜜分享给你一半。", "🍫 巧克力在嘴里融化，甜到了心里。", "🍬 糖果是五颜六色的梦，含在嘴里慢慢品。",
    "🍎 苹果咬一口，清脆的不仅是声音，还有心情。", "🍊 橘子剥开皮，酸酸甜甜就是我。", "🍌 香蕉弯弯像个月亮，笑一笑十年少。",
    "🍇 葡萄一串串，快乐也一串串。", "🥥 椰子敲一敲，里面藏着夏天的味道。"
]

THEMES = {
    "蜜桃粉": {"light": {"accent": "#FF9EBB", "bg": "stop:0 #FFF0F5, stop:1 #FFE4E1"}, "dark": {"accent": "#D96C8E", "bg": "stop:0 #2B1920, stop:1 #1A0F13"}},
    "海盐蓝": {"light": {"accent": "#82CFFD", "bg": "stop:0 #F0F8FF, stop:1 #E1FFFF"}, "dark": {"accent": "#5B96BA", "bg": "stop:0 #131E29, stop:1 #0A1118"}},
    "香芋紫": {"light": {"accent": "#CBA0E8", "bg": "stop:0 #F8F4FF, stop:1 #E6E6FA"}, "dark": {"accent": "#9675AD", "bg": "stop:0 #221A2E, stop:1 #130E1A"}},
    "薄荷绿": {"light": {"accent": "#8EE5A5", "bg": "stop:0 #F0FFF0, stop:1 #E0EEE0"}, "dark": {"accent": "#5E9E70", "bg": "stop:0 #15261A, stop:1 #0A140D"}},
    "奶昔橘": {"light": {"accent": "#FFB86C", "bg": "stop:0 #FFF8DC, stop:1 #FFE4B5"}, "dark": {"accent": "#CC8A47", "bg": "stop:0 #2E1F10, stop:1 #1A1005"}},
}


def mix_color(color: str, target: str, ratio: float) -> str:
    base = QColor(color)
    target_color = QColor(target)
    ratio = max(0.0, min(ratio, 1.0))

    mixed = QColor(
        round(base.red() + (target_color.red() - base.red()) * ratio),
        round(base.green() + (target_color.green() - base.green()) * ratio),
        round(base.blue() + (target_color.blue() - base.blue()) * ratio),
    )
    return mixed.name(QColor.NameFormat.HexRgb)


def rgba_color(color: str, alpha: int) -> str:
    qcolor = QColor(color)
    alpha = max(0, min(alpha, 255))
    return f"rgba({qcolor.red()}, {qcolor.green()}, {qcolor.blue()}, {alpha})"


class AppState:
    current_theme = random.choice(list(THEMES.keys()))
    is_dark_mode = False
    save_path = Path.home() / "Downloads"
    download_cover = False
    create_title_folder = False
    last_quote = ""
    bili_cookies = load_bili_cookies()

    @classmethod
    def get_new_quote(cls) -> str:
        available = [quote for quote in HITOKOTO_LIST if quote != cls.last_quote]
        cls.last_quote = random.choice(available)
        return cls.last_quote

    @classmethod
    def refresh_bili_cookies(cls) -> dict[str, str]:
        cls.bili_cookies = load_bili_cookies()
        return cls.bili_cookies

    @classmethod
    def save_bili_cookies(cls, cookies: dict[str, str]):
        cls.bili_cookies = dict(cookies)
        return save_bili_cookies(cls.bili_cookies)

    @classmethod
    def set_save_path(cls, save_path: str | Path) -> Path:
        cls.save_path = Path(save_path).expanduser()
        return cls.save_path
