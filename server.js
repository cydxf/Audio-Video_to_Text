const express = require('express');
const WebSocket = require('ws');
const http = require('http');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const cors = require('cors');
const { spawn } = require('child_process');
const port = 5501;

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// 使用 CORS 中间件
app.use(cors());

// 配置文件上传
const upload = multer({ dest: 'uploads/' });

// 提供静态文件服务
app.use('/js', express.static(path.join(__dirname, '../../../js')));
app.use('/css', express.static(path.join(__dirname, '../../../css')));

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.post('/upload', upload.single('audioFile'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ success: false, message: '请上传文件' });
    }
    res.json({ success: true, file: req.file.filename });
});

// WebSocket 处理
wss.on('connection', ws => {
    console.log('WebSocket 连接已建立');

    ws.on('message', message => {
        let data;
        try {
            data = JSON.parse(message);
        } catch (error) {
            ws.send(JSON.stringify({ error: '无效的 JSON 格式' }));
            return;
        }

        if (data.command === 'start' && data.file) {
            let filePath = path.join('uploads', data.file);
            let outputTxtFile = path.join('output_file_txt', data.file.replace('.wav', '.txt'));

            // 确保输出目录存在
            if (!fs.existsSync('output_file_txt')) {
                fs.mkdirSync('output_file_txt');
            }

            console.log(`处理文件: ${filePath}`);

            let pythonProcess = spawn('python', ['process_audio.py', filePath, outputTxtFile]);

            pythonProcess.stdout.on('data', (data) => {
                console.log(`进度数据: ${data.toString()}`);
                ws.send(JSON.stringify({ progress: data.toString().trim() }));
            });

            pythonProcess.stderr.on('data', (data) => {
                console.error(`Python 错误: ${data.toString()}`);
                ws.send(JSON.stringify({ error: '处理音频文件时出错' }));
            });

            pythonProcess.on('close', (code) => {
                if (code !== 0) {
                    console.error(`Python 进程退出，退出码: ${code}`);
                    ws.send(JSON.stringify({ error: '处理音频文件时出错' }));
                    return;
                }

                fs.readFile(outputTxtFile, 'utf8', (err, data) => {
                    if (err) {
                        console.error('读取文本文件失败:', err);
                        ws.send(JSON.stringify({ error: '读取文件失败' }));
                        return;
                    }
                    ws.send(JSON.stringify({ text: data }));
                });
            });

            // 处理超时情况
            setTimeout(() => {
                pythonProcess.kill();
                ws.send(JSON.stringify({ error: '处理音频文件超时' }));
                // Optionally close WebSocket here if you want
                // ws.close();
            }, 150000);  // 设置超时时间为150秒

        } else {
            ws.send(JSON.stringify({ error: '无效的命令或文件' }));
        }
    });

    ws.on('error', (error) => {
        console.error('WebSocket 错误:', error);
    });

    // Optionally handle WebSocket close here if needed
    ws.on('close', (code, reason) => {
        if (code === 1001) {
            console.log('WebSocket 连接关闭: 由于网络故障或设备离线');
            // 你可以在这里进行一些清理操作，或者记录日志
        } else {
            console.log(`WebSocket 连接关闭，状态码: ${code}，原因: ${reason}`);
        }
    });   
});

server.listen(5501,'0.0.0.0', () => {
    console.log('服务器正在监听端口 5501');
});
