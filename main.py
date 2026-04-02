import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
from datetime import datetime
import requests

class QWeatherMailSender:
    def __init__(self):
        # 配置
        self.sender_email = os.environ.get('SENDER_EMAIL', '')
        self.sender_auth_code = os.environ.get('SENDER_AUTH_CODE', '')
        self.receiver_emails = os.environ.get('RECEIVER_EMAILS', '').split(',')
        self.location_city = os.environ.get('LOCATION_CITY', '湖州')
        self.weather_api_key = os.environ.get('WEATHER_API_KEY', '')
        
        # 和风天气 API
        self.base_url = "https://devapi.qweather.com/v7/weather"
        self.geo_url = "https://geoapi.qweather.com/v2/city/lookup"
        
        # SMTP
        self.smtp_server = "smtp.sina.com"
        self.smtp_port = 465

    def get_city_id(self):
        """获取城市ID"""
        params = {'key': self.weather_api_key, 'location': self.location_city}
        try:
            resp = requests.get(self.geo_url, params=params, timeout=10)
            data = resp.json()
            if data['code'] == '200' and data['location']:
                return data['location'][0]['id']
        except Exception as e:
            print(f"获取城市ID失败: {e}")
        return None

    def get_weather_3d(self, city_id):
        """获取3天天气预报"""
        url = f"{self.base_url}/3d"
        params = {'key': self.weather_api_key, 'location': city_id}
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if data['code'] == '200':
                return data['daily']
        except Exception as e:
            print(f"获取天气失败: {e}")
        return []

    def format_html(self, weather_data):
        """生成HTML邮件"""
        today = datetime.now().strftime('%Y年%m月%d日')
        
        html = f"""
        <html>
        <head><style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background: #4a90e2; color: white; padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; border: 1px solid #ddd; text-align: center; }}
            th {{ background: #f2f2f2; }}
        </style></head>
        <body>
            <div class="header">
                <h1>{self.location_city}天气预报</h1>
                <p>{today}</p>
            </div>
            <table>
                <tr><th>日期</th><th>天气</th><th>最高温</th><th>最低温</th><th>日出/日落</th></tr>
        """
        
        for day in weather_data[:3]:
            html += f"""
                <tr>
                    <td>{day['fxDate']}</td>
                    <td>{day['textDay']}</td>
                    <td>{day['tempMax']}°C</td>
                    <td>{day['tempMin']}°C</td>
                    <td>{day['sunrise']}/{day['sunset']}</td>
                </tr>
            """
        
        html += """
            </table>
            <p>数据来源：和风天气</p>
        </body>
        </html>
        """
        return html

    def send_email(self, html):
        """发送邮件"""
        subject = f"【{self.location_city}天气预报】{datetime.now().strftime('%Y年%m月%d日')}"
        
        for receiver in self.receiver_emails:
            receiver = receiver.strip()
            if not receiver:
                continue
                
            try:
                msg = MIMEMultipart('alternative')
                msg['From'] = formataddr(("天气助手", self.sender_email))
                msg['To'] = receiver
                msg['Subject'] = subject
                msg['Date'] = formatdate(localtime=True)
                
                msg.attach(MIMEText(html, 'html', 'utf-8'))
                
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender_email, self.sender_auth_code)
                    server.send_message(msg)
                
                print(f"✓ 邮件已发送至: {receiver}")
                
            except Exception as e:
                print(f"✗ 发送失败 {receiver}: {e}")

    def run(self):
        """主程序"""
        print(f"【{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}】开始执行")
        
        # 获取城市ID
        city_id = self.get_city_id()
        if not city_id:
            return {"success": False, "error": "获取城市ID失败"}
        
        # 获取天气
        weather = self.get_weather_3d(city_id)
        if not weather:
            return {"success": False, "error": "获取天气失败"}
        
        # 发送邮件
        html = self.format_html(weather)
        self.send_email(html)
        
        return {"success": True, "city": self.location_city}

if __name__ == "__main__":
    # 检查环境变量
    required = ["SENDER_EMAIL", "SENDER_AUTH_CODE", "RECEIVER_EMAILS", "WEATHER_API_KEY"]
    missing = [var for var in required if not os.environ.get(var)]
    
    if missing:
        print(f"缺少环境变量: {', '.join(missing)}")
        exit(1)
    
    sender = QWeatherMailSender()
    result = sender.run()
    print(f"执行结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
