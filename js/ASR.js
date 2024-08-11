document.addEventListener('DOMContentLoaded', function () {
    const uploadButton = document.getElementById('uploadButton');
    const audioFileInput = document.getElementById('audioFile');
    const progressBar = document.getElementById('progressBar');
    const resultText = document.getElementById('resultText');
    const downloadButton = document.getElementById('downloadButton');

    uploadButton.addEventListener('click', function (event) {
        event.preventDefault();  // 阻止默认行为
        
        console.log('上传按钮点击');

        const file = audioFileInput.files[0];
        if (!file) {
            alert('请先选择一个文件！');
            return;
        }

        const formData = new FormData();
        formData.append('audioFile', file);

        fetch('http://localhost:5501/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('文件上传成功:', data.file);

                const ws = new WebSocket('ws://localhost:5501');

                ws.onopen = () => {
                    console.log('WebSocket 连接已建立');
                    ws.send(JSON.stringify({ command: 'start', file: data.file }));
                };

                ws.onmessage = (event) => {
                    console.log('收到 WebSocket 消息:', event.data);
                    const message = JSON.parse(event.data);
                    console.log('解析后的消息:', message);

                    if (message.text) {
                        resultText.textContent = message.text;

                        downloadButton.style.display = 'block';
                        downloadButton.onclick = () => {
                            const editedText = resultText.value;  // 获取用户编辑后的内容
                            const blob = new Blob([editedText], { type: 'text/plain' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = 'result.txt';
                            a.click();
                            URL.revokeObjectURL(url);
                        };
                    }

                    if (message.error) {
                        console.error('WebSocket 错误:', message.error);
                    }
                };

                ws.onerror = (error) => {
                    console.error('WebSocket 错误:', error);
                };

                ws.onclose = () => {
                    console.log('WebSocket 连接关闭');
                };
            } else {
                console.error('文件上传失败:', data.message);
            }
        })
        .catch(error => {
            console.error('上传失败:', error);
        });
    });
});
