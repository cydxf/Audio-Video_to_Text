import websocket
import datetime
import hashlib
import base64
import hmac
import json
import logging
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
from pydub import AudioSegment
import os
from tqdm import tqdm  # 导入tqdm库用于显示进度条
from concurrent.futures import ThreadPoolExecutor, as_completed

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class Ws_Param(object):
    def __init__(self, APPID, APIKey, APISecret):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)
        self.BusinessArgs = {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo": 1, "vad_eos": 10000}

    def create_url(self):
        url = 'wss://ws-api.xfyun.cn/v2/iat'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: ws-api.xfyun.cn\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET /v2/iat HTTP/1.1"
        # 进行hmac-sha256加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        return url

def convert_audio(input_file, output_file):
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio.export(output_file, format="wav")

def split_audio(input_file, output_folder, chunk_length_ms=60000):
    audio = AudioSegment.from_file(input_file)
    duration_ms = len(audio)
    chunks = duration_ms // chunk_length_ms + (1 if duration_ms % chunk_length_ms != 0 else 0)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for i in range(chunks):
        start_time = i * chunk_length_ms
        end_time = min(start_time + chunk_length_ms, duration_ms)
        chunk = audio[start_time:end_time]
        chunk.export(os.path.join(output_folder, f"chunk_{i}.wav"), format="wav")

def on_message(ws, message, index, results):
    try:
        print(f"Received message: {message}")
        data = json.loads(message)
        code = data.get("code")
        sid = data.get("sid")
        if code != 0:
            errMsg = data.get("message")
            print(f"sid:{sid} call error:{errMsg} code is:{code}")
        else:
            result_data = data.get("data", {}).get("result", {}).get("ws", [])
            result = ""
            for i in result_data:
                if "cw" in i:
                    for w in i["cw"]:
                        if "w" in w:
                            result += w["w"]
            # 确保 results 列表的长度足够
            while len(results) <= index:
                results.append([])
            # 将结果添加到对应 chunk 的列表中
            results[index].append(result)
    except Exception as e:
        print(f"Exception while processing message: {e}")
        print(f"Message details: {message}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, a, b, chunk_path, progress_bar):
    progress_bar.update(1)
    os.remove(chunk_path)  # 删除音频分片文件
    print("### closed ###")

def process_chunk(chunk_path, index, results, progress_bar):
    print(f"Processing chunk: {chunk_path}")
    wsParam = Ws_Param(APPID='91f7bf93',  # 输入APPID
                       APIKey='03d0245a398713654de95df630faaf30',  # 输入APIKey
                       APISecret='MGI0NGRiNDgxNDAzMjk5ZjZiZTc4NTVk')  # 输入APISecret

    def on_open(ws):
        print("WebSocket connection opened")
        def run():
            frameSize = 8000  # 每一帧的音频大小
            interval = 0.0001  # 发送音频间隔(单位:s)
            status = STATUS_FIRST_FRAME

            with open(chunk_path, "rb") as fp:
                while True:
                    buf = fp.read(frameSize)
                    if not buf:
                        status = STATUS_LAST_FRAME

                    if status == STATUS_FIRST_FRAME:
                        d = {"common": wsParam.CommonArgs,
                             "business": wsParam.BusinessArgs,
                             "data": {"status": 0, "format": "audio/L16;rate=16000",
                                      "audio": str(base64.b64encode(buf), 'utf-8'),
                                      "encoding": "raw"}}
                        ws.send(json.dumps(d))
                        status = STATUS_CONTINUE_FRAME
                    elif status == STATUS_CONTINUE_FRAME:
                        d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                                      "audio": str(base64.b64encode(buf), 'utf-8'),
                                      "encoding": "raw"}}
                        ws.send(json.dumps(d))
                    elif status == STATUS_LAST_FRAME:
                        d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                                      "audio": str(base64.b64encode(buf), 'utf-8'),
                                      "encoding": "raw"}}
                        ws.send(json.dumps(d))
                        time.sleep(1)
                        break

                    # 模拟音频采样间隔
                    time.sleep(interval)

            ws.close()

        thread.start_new_thread(run, ())

    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl,
                                on_message=lambda ws, msg: on_message(ws, msg, index, results),
                                on_error=on_error,
                                on_close=lambda ws, a, b: on_close(ws, a, b, chunk_path, progress_bar))
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: process_audio.py <input_audio_file> <output_txt_file>")
        sys.exit(1)

    input_audio_file = sys.argv[1]
    output_txt_file = sys.argv[2]
    chunk_path = "./chunks"

    # 音频文件转换
    converted_audio_file = input_audio_file.replace('.wav', '_converted.wav')
    convert_audio(input_audio_file, converted_audio_file)

    # 切分音频
    output_folder = "chunks"
    split_audio(converted_audio_file, output_folder)

    # 处理每个音频分片
    chunk_files = [os.path.join(output_folder, f"chunk_{i}.wav") for i in range(len(os.listdir(output_folder)))]

    results = []  # 使用列表来存储每个 chunk 的结果

    # 创建进度条
    with tqdm(total=len(chunk_files), desc="Processing") as pbar:
        with ThreadPoolExecutor(max_workers=50) as executor:
            future_to_chunk = {executor.submit(process_chunk, chunk_file, index, results, pbar): (chunk_file, index) for index, chunk_file in enumerate(chunk_files)}

            for future in as_completed(future_to_chunk):
                future.result()

    # 等待所有线程完成
    time.sleep(5)  # 确保所有WebSocket连接关闭并更新进度条

    # 将结果写入指定路径的txt文件
    with open(output_txt_file, "w", encoding="utf-8") as f:
        for chunk_result in results:
            combined_result = ''.join(chunk_result)
            f.write(combined_result.strip() + '\n')
