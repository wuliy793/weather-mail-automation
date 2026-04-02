import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
from datetime import datetime
import requests
from typing import Dict, Any, Optional

class MeizuWeatherMailSender:
    def __init__(self):
        # 从环境变量读取配置
        self.sender_email = os.environ.get('SENDER_EMAIL', 'wuliying49@sina.com')
        self.sender_auth_code = os.environ.get('SENDER_AUTH_CODE', '')
        self.receiver_emails = os.environ.get('RECEIVER_EMAILS', '').split(',')
        self.location_city = os.environ.get('LOCATION_CITY', '湖州')
        
        # 魅族天气 API
        self.base_url = "http://aider.meizu.com/app/weather/listWeather"
        
        # SMTP 配置
        self.smtp_server = "smtp.sina.com"
        self.smtp_port = 465
        
        # 城市ID映射
        self.city_id_map = {
            "湖州": "101210201",
            "杭州": "101210101",
            "上海": "101020100",
            "北京": "101010100"
        }
        
        # 天气图标映射
        self.weather_icon_map = {
            "0": "☀️", "1": "⛅", "2": "☁️", "3": "🌧️", "4": "⛈️",
            "5": "🌧️", "6": "🌦️", "7": "🌧️", "8": "🌧️", "9": "🌧️",
            "10": "🌧️", "11": "🌧️", "12": "🌧️", "13": "🌨️", "14": "❄️",
            "15": "❄️", "16": "❄️", "17": "❄️", "18": "🌫️", "19": "🌫️"
        }

    def _get_city_id(self) -> str:
        """根据城市名称获取城市ID"""
        return self.city_id_map.get(self.location_city, "101210201")

    def fetch_weather_data(self) -> Optional[Dict]:
        """从魅族天气API获取天气数据"""
        city_id = self._get_city_id()
        url = f"{self.base_url}?cityIds={city_id}"
        
        try:
            print(f"正在获取 {self.location_city} 的天气数据...")
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get("code") == "200" and data.get("value"):
                return data["value"][0]
            else:
                print(f"API返回错误: {data}")
                return None
                
        except Exception as e:
            print(f"获取天气数据失败: {e}")
            return None

    def format_weather_info(self, weather_data: Dict) -> str:
        """格式化天气信息为HTML邮件内容"""
        if not weather_data:
            return "<p>天气数据获取失败</p>"
        
        # 提取数据
        realtime = weather_data.get("realtime", {})
        forecast_7d = weather_data.get("weathers", [])[:7]
        pm25_info = weather_data.get("pm25", {})
        indexes = weather_data.get("indexes", [])
        
        # 构建HTML内容
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .header {{ background: #4a90e2; color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌤️ {self.location_city} 天气预报</h1>
                    <p>更新时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
                </div>
                
                <!-- 当前天气 -->
                <h3>当前天气</h3>
                <p>温度: {realtime.get('temp', 'N/A')}°C | 天气: {realtime.get('weather', 'N/A')} | 湿度: {realtime.get('sD', 'N/A')}%</p>
                
                <!-- 7天预报 -->
                <h3>7天天气预报</h3>
                <table>
                    <tr>
                        <th>日期</th><th>天气</th><th>最高温</th><th>最低温</th><th>日出/日落</th>
                    </tr>
        """
        
        for day in forecast_7d:
            html_content += f"""
                    <tr>
                        <td>{day.get('date', '')} {day.get('week', '')}</td>
                        <td>{day.get('weather', '')}</td>
                        <td>{day.get('temp_day_c', '')}°C</td>
                        <td>{day.get('temp_night_c', '')}°C</td>
                        <td>{day.get('sun_rise_time', '')}/{day.get('sun_down_time', '')}</td>
                    </tr>
            """
        
        html_content += """
                </table>
                
                <!-- 空气质量 -->
                <h3>空气质量</h3>
                <p>AQI: {aqi} | 等级: {quality} | PM2.5: {pm25}μg/m³</p>
                
                <div class="footer">
                    <p>此邮件由自动化脚本发送，祝您有美好的一天！</p>
                </div>
            </div>
        </body>
        </html>
        """.format(
            aqi=pm25_info.get('aqi', 'N/A'),
            quality=pm25_info.get('quality', 'N/A'),
            pm25=pm25_info.get('pm25', 'N/A')
        )
        
        return html_content

    def send_email(self, html_content: str) -> bool:
        """发送邮件到所有收件人"""
        if not self.receiver_emails or not self.receiver_emails[0]:
            print("错误: 没有设置收件人邮箱")
            return False
        
        subject = f"【{self.location_city}天气预报】{datetime.now().strftime('%Y年%m月%d日')}"
        
        success_count = 0
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
                
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
                
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender_email, self.sender_auth_code)
                    server.send_message(msg)
                
                print(f"✓ 邮件已发送至: {receiver}")
                success_count += 1
                
            except Exception as e:
                print(f"✗ 发送邮件到 {receiver} 失败: {e}")
        
        print(f"📧 邮件发送完成: 成功 {success_count} 封")
        return success_count > 0

    def run(self) -> Dict[str, Any]:
        """主执行函数"""
        print(f"【{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}】开始执行天气邮件任务")
        print(f"城市: {self.location_city}")
        print(f"收件人: {', '.join(self.receiver_emails) if self.receiver_emails else '未设置'}")
        
        # 获取天气数据
        weather_data = self.fetch_weather_data()
        if not weather_data:
            return {"success": False, "error": "获取天气数据失败"}
        
        # 格式化邮件内容
        html_content = self.format_weather_info(weather_data)
        
        # 发送邮件
        success = self.send_email(html_content)
        
        if success:
            return {
                "success": True,
                "city": self.location_city,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "recipients": self.receiver_emails
            }
        else:
            return {"success": False, "error": "邮件发送失败"}


if __name__ == "__main__":
    # 检查必要的环境变量
    required_env_vars = ["SENDER_EMAIL", "SENDER_AUTH_CODE", "RECEIVER_EMAILS"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"错误: 缺少必要的环境变量: {', '.join(missing_vars)}")
        exit(1)
    
    # 运行天气邮件发送程序
    sender = MeizuWeatherMailSender()
    result = sender.run()
    
    print(f"执行结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
