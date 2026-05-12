import os
import logging
import json

from agent_core.actions.registry import ANIMATION_ACTIONS
from agent_core.prompts import LLM_ACTION_PROMPT, LLM_ROLE_PROMPT


# Set Version
VERSION = "v3.0.0"

## Set logger
log_directory = 'logs'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
logger = logging.getLogger('Logger')
logger.setLevel(logging.DEBUG)

debug_handler = logging.FileHandler(os.path.join(log_directory, 'debug.log'))
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

error_handler = logging.FileHandler(os.path.join(log_directory, 'error.log'))
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

info_handler = logging.FileHandler(os.path.join(log_directory, 'info.log'))
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))

logger.addHandler(debug_handler)
logger.addHandler(error_handler)
logger.addHandler(info_handler)
logger.addHandler(stream_handler)


# LLM voices
gpt_voice_list = [
    {'Onyx', 'onyx'},
    {'Alloy', 'alloy'},
    {'Echo', 'echo'},
    {'Fable', 'fable'},
    {'Nova', 'nova'},
    {'Shimmer', 'shimmer'}]

volcano_voice_list = [
    {"灿灿 2.0", "BV700_V2_streaming"}, 
    {"炀炀", "BV705_streaming"}, 
    {"擎苍 2.0", "BV701_V2_streaming"}, 
    {"通用女声 2.0", "BV001_V2_streaming"}, 
    {"灿灿", "BV700_streaming"}, 
    {"超自然音色-梓梓2.0", "BV406_V2_streaming"}, 
    {"超自然音色-梓梓", "BV406_streaming"}, 
    {"超自然音色-燃燃2.0", "BV407_V2_streaming"}, 
    {"超自然音色-燃燃", "BV407_streaming"}, 
    {"通用女声", "BV001_streaming"}, 
    {"通用男声", "BV002_streaming"}, 
    {"擎苍", "BV701_streaming"}, 
    {"阳光青年", "BV123_streaming"}, 
    {"反卷青年", "BV120_streaming"}, 
    {"通用赘婿", "BV119_streaming"}, 
    {"古风少御", "BV115_streaming"}, 
    {"霸气青叔", "BV107_streaming"}, 
    {"质朴青年", "BV100_streaming"}, 
    {"温柔淑女", "BV104_streaming"}, 
    {"开朗青年", "BV004_streaming"}, 
    {"甜宠少御", "BV113_streaming"}, 
    {"儒雅青年", "BV102_streaming"}, 
    {"甜美小源", "BV405_streaming"}, 
    {"亲切女声", "BV007_streaming"}, 
    {"知性女声", "BV009_streaming"}, 
    {"诚诚", "BV419_streaming"}, 
    {"童童", "BV415_streaming"}, 
    {"亲切男声", "BV008_streaming"}, 
    {"译制片男声", "BV408_streaming"}, 
    {"懒小羊", "BV426_streaming"}, 
    {"清新文艺女声", "BV428_streaming"}, 
    {"鸡汤女声", "BV403_streaming"}, 
    {"智慧老者", "BV158_streaming"}, 
    {"慈爱姥姥", "BV157_streaming"}, 
    {"说唱小哥", "BR001_streaming"}, 
    {"活力解说男", "BV410_streaming"}, 
    {"影视解说小帅", "BV411_streaming"}, 
    {"解说小帅-多情感", "BV437_streaming"}, 
    {"影视解说小美", "BV412_streaming"}, 
    {"纨绔青年", "BV159_streaming"}, 
    {"直播一姐", "BV418_streaming"}, 
    {"反卷青年", "BV120_streaming"}, 
    {"沉稳解说男", "BV142_streaming"}, 
    {"潇洒青年", "BV143_streaming"}, 
    {"阳光男声", "BV056_streaming"}, 
    {"活泼女声", "BV005_streaming"}, 
    {"小萝莉", "BV064_streaming"}, 
    {"奶气萌娃", "BV051_streaming"}, 
    {"动漫海绵", "BV063_streaming"},
    {"动漫海星", "BV417_streaming"}, 
    {"动漫小新", "BV050_streaming"}, 
    {"天才童声", "BV061_streaming"}, 
    {"促销男声", "BV401_streaming"}, 
    {"促销女声", "BV402_streaming"}, 
    {"磁性男声", "BV006_streaming"}, 
    {"新闻女声", "BV011_streaming"}, 
    {"新闻男声", "BV012_streaming"}, 
    {"知性姐姐-双语", "BV034_streaming"}, 
    {"温柔小哥", "BV033_streaming"}, 
    {"东北老铁", "BV021_streaming"}, 
    {"东北丫头", "BV020_streaming"}, 
    {"方言灿灿", "BV704_streaming"}, 
    {"西安佟掌柜", "BV210_streaming"}, 
    {"沪上阿姐", "BV217_streaming"}, 
    {"广西表哥", "BV213_streaming"}, 
    {"甜美台妹", "BV025_streaming"}, 
    {"台普男声", "BV227_streaming"}, 
    {"港剧男神", "BV026_streaming"}, 
    {"广东女仔", "BV424_streaming"}, 
    {"相声演员", "BV212_streaming"}, 
    {"重庆小伙", "BV019_streaming"}, 
    {"四川甜妹儿", "BV221_streaming"}, 
    {"重庆幺妹儿", "BV423_streaming"}, 
    {"乡村企业家", "BV214_streaming"}, 
    {"湖南妹坨", "BV226_streaming"}, 
    {"长沙靓女", "BV216_streaming"}
]


# Command button list
eye_button_list = [
    ("眨眼", "eye_blink"),
    ("快乐", "eye_happy"),
    ("难过", "eye_sad"),
    ("生气", "eye_anger"),
    ("惊讶", "eye_surprise"),
    ("向左看", "eye_left"),
    ("向右看", "eye_right"),
]


head_button_list = [
    ("左转", "head_left"),
    ("右转", "head_right"),
    ("抬头", "head_up"),
    ("低头", "head_down"),
    ("点头", "head_nod"),
    ("摇头", "head_shake"),
    ("向左环绕", "head_roll_left"),
    ("向右环绕", "head_roll_right"),
    ("归中", "head_center"),
]


animations_list = list(ANIMATION_ACTIONS)


# Prompts
llm_role = LLM_ROLE_PROMPT
llm_prompt = LLM_ACTION_PROMPT


def error(e="", msg=""):
    print(f"[Error] {msg}. See details in logs/error.log")
    logger.error(msg)
    logger.error(e)


class BaseLLM(object):

    def __init__(self, key):
        self.json_path = ''
        self.headers = ''
        self.client = None
        self.key = key
        self.api_url = ''
        self.api_key = ''

    def _create_empty_json(self):
        if not os.path.exists(self.json_path):
            self.write_json()

    def read_json(self):
        with open(self.json_path, 'r') as json_file:
            data = json.load(json_file)
        return data.get(self.key).get('api_url', ''), data.get(self.key).get('api_key', '')

    def write_json(self, api_url="", api_key=""):
        data = {
            self.key: 
            {
                "api_url": api_url,
                "api_key": api_key
            }
        }
        with open(self.json_path, 'w') as fp:
            json.dump(data, fp, indent=4)


if __name__ == "__main__":
    print(animations_list)
