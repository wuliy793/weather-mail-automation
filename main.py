import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional, Tuple

class OpenWeatherMailSender:
    def __init__(self):
        # 从环境变量读取配置
        self.sender_email = os.environ.get('SENDER_EMAIL', 'wuliying49@sina.com')
        self.sender_auth_code = os.environ.get('SENDER_AUTH_CODE', 'ec1f17a5e11f0d82')
        
        # 收件人列表
        receivers_str = os.environ.get('RECEIVER_EMAILS', '')
        if receivers_str:
            self.receiver_emails = [email.strip() for email in receivers_str.split(',')]
        else:
            # 默认收件人
            self.receiver_emails = [
                "3907928171@qq.com",
                "1726960087@qq.com", 
                "wuliying2026@outlook.com"
            ]
        
        # OpenWeatherMap 配置
        self.location_city = os.environ.get('LOCATION_CITY', 'Huzhou')
        self.openweather_api_key = os.environ.get('OPENWEATHER_API_KEY', 'f56eb3db2d21132c03abb35243ca60dc')
        
        # API 端点
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
        # SMTP 配置
        self.smtp_server = "smtp.sina.com"
        self.smtp_port = 465
        
        # 天气图标映射
        self.weather_icon_map = {
            "01": "☀️",  # 晴
            "02": "⛅",  # 少云
            "03": "☁️",  # 多云
            "04": "☁️",  # 阴
            "09": "🌧️",  # 小雨
            "10": "🌧️",  # 中雨/大雨
            "11": "⛈️",  # 雷暴
            "13": "❄️",  # 雪
            "50": "🌫️",  # 雾/霾
        }
        
        print(f"发件人: {self.sender_email}")
        print(f"收件人: {', '.join(self.receiver_emails)}")
        print(f"城市: {self.location_city}")
        print(f"OpenWeatherMap API Key: {self.openweather_api_key[:8]}...")

    def _get_current_weather(self) -> Optional[Dict]:
        """获取当前天气"""
        try:
            print("🌤️ 获取当前天气数据...")
            url = f"{self.base_url}/weather"
            params = {
                'q': self.location_city,
                'appid': self.openweather_api_key,
                'units': 'metric',  # 摄氏度
                'lang': 'zh_cn'     # 中文
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ API错误 {response.status_code}: {response.text}")
                return None
            
            data = response.json()
            
            # 提取当前天气信息
            current = {
                'city': data.get('name', self.location_city),
                'country': data.get('sys', {}).get('country', ''),
                'temp': round(data['main']['temp'], 1),
                'feels_like': round(data['main']['feels_like'], 1),
                'temp_min': round(data['main']['temp_min'], 1),
                'temp_max': round(data['main']['temp_max'], 1),
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'weather_main': data['weather'][0]['main'],
                'weather_desc': data['weather'][0]['description'],
                'weather_icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'wind_deg': data['wind'].get('deg', 0),
                'clouds': data['clouds']['all'],
                'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M'),
                'sunset': datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M'),
                'time': datetime.fromtimestamp(data['dt']).strftime('%Y-%m-%d %H:%M')
            }
            
            print(f"✅ 当前天气: {current['temp']}°C, {current['weather_desc']}")
            return current
            
        except Exception as e:
            print(f"❌ 获取当前天气失败: {e}")
            return None

    def _get_forecast_5d(self) -> Optional[List[Dict]]:
        """获取5天天气预报（每3小时）"""
        try:
            print("📅 获取5天天气预报...")
            url = f"{self.base_url}/forecast"
            params = {
                'q': self.location_city,
                'appid': self.openweather_api_key,
                'units': 'metric',
                'lang': 'zh_cn',
                'cnt': 40  # 5天 * 8个时间段
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ 预报API错误 {response.status_code}: {response.text}")
                return None
            
            data = response.json()
            
            # 按天分组
            daily_forecasts = {}
            for item in data['list']:
                date = item['dt_txt'].split()[0]  # 提取日期
                if date not in daily_forecasts:
                    daily_forecasts[date] = {
                        'temps': [],
                        'feels_like': [],
                        'weathers': [],
                        'humidity': [],
                        'wind_speed': [],
                        'timestamps': []
                    }
                
                daily_forecasts[date]['temps'].append(item['main']['temp'])
                daily_forecasts[date]['feels_like'].append(item['main']['feels_like'])
                daily_forecasts[date]['weathers'].append(item['weather'][0]['description'])
                daily_forecasts[date]['humidity'].append(item['main']['humidity'])
                daily_forecasts[date]['wind_speed'].append(item['wind']['speed'])
                daily_forecasts[date]['timestamps'].append(item['dt_txt'])
            
            # 转换为每日预报
            forecast_list = []
            for date, values in list(daily_forecasts.items())[:5]:  # 只取5天
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                weekday = ["一", "二", "三", "四", "五", "六", "日"][date_obj.weekday()]
                
                # 找到最常出现的天气描述
                most_common_weather = max(set(values['weathers']), key=values['weathers'].count)
                
                forecast_list.append({
                    'date': date,
                    'date_display': f"{date_obj.month}/{date_obj.day} 周{weekday}",
                    'weather': most_common_weather,
                    'temp_avg': round(sum(values['temps']) / len(values['temps']), 1),
                    'temp_min': round(min(values['temps']), 1),
                    'temp_max': round(max(values['temps']), 1),
                    'feels_like_avg': round(sum(values['feels_like']) / len(values['feels_like']), 1),
                    'humidity_avg': round(sum(values['humidity']) / len(values['humidity']), 1),
                    'wind_speed_avg': round(sum(values['wind_speed']) / len(values['wind_speed']), 1)
                })
            
            print(f"✅ 获取到 {len(forecast_list)} 天预报")
            return forecast_list
            
        except Exception as e:
            print(f"❌ 获取天气预报失败: {e}")
            return None

    def _format_wind_direction(self, degree: float) -> str:
        """将风向角度转换为中文方向"""
        directions = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
        index = round(degree / 45) % 8
        return directions[index]

    def _format_html_email(self, current: Dict, forecast: List[Dict]) -> str:
        """生成HTML邮件内容"""
        today = datetime.now()
        today_str = today.strftime('%Y年%m月%d日')
        weekday = ["一", "二", "三", "四", "五", "六", "日"][today.weekday()]
        
        # 获取天气图标
        icon_code = current.get('weather_icon', '01d')
        icon = self.weather_icon_map.get(icon_code[:2], '🌤️')
        
        # 风向
        wind_direction = self._format_wind_direction(current.get('wind_deg', 0))
        
        # 构建当前天气卡片
        current_html = f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 25px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        ">
            <div style="text-align: center;">
                <h1 style="margin: 0 0 10px 0; font-size: 2.2em;">{icon} {current['city']}天气预报</h1>
                <p style="opacity: 0.9; font-size: 1.1em;">{today_str} 周{weekday} | 数据更新时间: {current.get('time', '')}</p>
            </div>
            
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 25px;
                flex-wrap: wrap;
            ">
                <div style="text-align: center; flex: 1; min-width: 200px;">
                    <div style="font-size: 4.5em; font-weight: 300; line-height: 1;">{current['temp']}°C</div>
                    <div style="font-size: 1.3em; margin: 10px 0;">{current['weather_desc']}</div>
                    <div style="opacity: 0.9;">体感: {current['feels_like']}°C</div>
                </div>
                
                <div style="flex: 1; min-width: 250px;">
                    <div style="
                        background: rgba(255,255,255,0.1);
                        padding: 20px;
                        border-radius: 10px;
                        backdrop-filter: blur(10px);
                    ">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div><strong>🌡️ 最低/最高</strong><br>{current['temp_min']}°C / {current['temp_max']}°C</div>
                            <div><strong>💧 湿度</strong><br>{current['humidity']}%</div>
                            <div><strong>💨 风速</strong><br>{current['wind_speed']} m/s {wind_direction}风</div>
                            <div><strong>☁️ 云量</strong><br>{current.get('clouds', 0)}%</div>
                            <div><strong>☀️ 日出</strong><br>{current.get('sunrise', '--:--')}</div>
                            <div><strong>🌙 日落</strong><br>{current.get('sunset', '--:--')}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        # 构建预报表格
        forecast_html = ""
        if forecast:
            forecast_html = """
            <h3 style="
                color: #2c3e50;
                border-left: 5px solid #3498db;
                padding-left: 15px;
                margin: 40px 0 20px 0;
            ">📅 未来5天预报</h3>
            
            <div style="
                overflow-x: auto;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            ">
                <table style="
                    width: 100%;
                    border-collapse: collapse;
                    min-width: 600px;
                ">
                    <thead>
                        <tr style="background: #2c3e50; color: white;">
                            <th style="padding: 16px; text-align: left;">日期</th>
                            <th style="padding: 16px; text-align: left;">天气</th>
                            <th style="padding: 16px; text-align: left;">温度</th>
                            <th style="padding: 16px; text-align: left;">体感</th>
                            <th style="padding: 16px; text-align: left;">湿度</th>
                            <th style="padding: 16px; text-align: left;">风速</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for i, day in enumerate(forecast):
                bg_color = "#f8f9fa" if i % 2 == 0 else "white"
                day_icon = self.weather_icon_map.get(day.get('weather_icon', '01d')[:2], '🌤️')
                
                forecast_html += f"""
                <tr style="background: {bg_color};">
                    <td style="padding: 16px; border-bottom: 1px solid #eaeaea;">
                        <strong>{day['date_display']}</strong>
                    </td>
                    <td style="padding: 16px; border-bottom: 1px solid #eaeaea;">
                        {day_icon} {day['weather']}
                    </td>
                    <td style="padding: 16px; border-bottom: 1px solid #eaeaea;">
                        {day['temp_min']}°C ~ {day['temp_max']}°C
                    </td>
                    <td style="padding: 16px; border-bottom: 1px solid #eaeaea;">
                        {day['feels_like_avg']}°C
                    </td>
                    <td style="padding: 16px; border-bottom: 1px solid #eaeaea;">
                        {day['humidity_avg']}%
                    </td>
                    <td style="padding: 16px; border-bottom: 1px solid #eaeaea;">
                        {day['wind_speed_avg']} m/s
                    </td>
                </tr>
                """
            
            forecast_html += """
                    </tbody>
                </table>
            </div>
            """
        
        # 温馨提示
        tips_html = ""
        if current['weather_main'].lower() in ['rain', 'snow', 'thunderstorm']:
            weather_type = {
                'rain': '雨天',
                'snow': '雪天',
                'thunderstorm': '雷暴天气'
            }.get(current['weather_main'].lower(), '特殊天气')
            
            tips_html = f"""
            <div style="
                background: #e3f2fd;
                padding: 20px;
                border-radius: 10px;
                margin: 25px 0;
                border-left: 5px solid #2196f3;
            ">
                <h4 style="margin-top: 0; color: #1565c0;">⚠️ {weather_type}温馨提示</h4>
                <p>今天有{current['weather_desc']}，气温{current['temp']}°C。请注意携带雨具，出行注意安全。</p>
                {"<p>路面可能湿滑，驾车请减速慢行。</p>" if current['weather_main'].lower() in ['rain', 'snow'] else ""}
            </div>
            """
        
        # 完整HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: #f5f7fa;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    overflow: hidden;
                    box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                }}
                .content {{
                    padding: 30px;
                }}
                .footer {{
                    text-align: center;
                    padding: 25px;
                    background: #f8f9fa;
                    color: #6c757d;
                    font-size: 13px;
                    border-top: 1px solid #eaeaea;
                }}
                table {{
                    width: 100%;
                }}
                th, td {{
                    text-align: left;
                }}
                @media (max-width: 768px) {{
                    .container {{
                        border-radius: 10px;
                    }}
                    .content {{
                        padding: 20px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    {current_html}
                    {tips_html}
                    {forecast_html}
                </div>
                <div class="footer">
                    <p>数据来源: OpenWeatherMap | 自动发送服务 | 更新频率: 每日00:00</p>
                    <p>© {today.year} 天气助手 | 本邮件由自动化脚本生成，祝您有美好的一天！</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html

    def send_email(self, html_content: str) -> Tuple[int, int]:
        """发送邮件到所有收件人"""
        subject = f"【{self.location_city}天气预报】{datetime.now().strftime('%Y年%m月%d日')}"
        
        success = 0
        failure = 0
        
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
                
                msg.attach(MIMEText(html_content, 'html', 'utf-8'))
                
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30) as server:
                    server.login(self.sender_email, self.sender_auth_code)
                    server.send_message(msg)
                
                print(f"✅ 邮件已发送至: {receiver}")
                success += 1
                
            except Exception as e:
                print(f"❌ 发送失败 {receiver}: {e}")
                failure += 1
        
        return success, failure

    def run(self) -> Dict:
        """主程序"""
        print(f"【{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}】开始执行天气邮件任务")
        
        # 1. 获取当前天气
        current_weather = self._get_current_weather()
        if not current_weather:
            return {"success": False, "error": "获取当前天气失败"}
        
        # 2. 获取5天预报
        forecast = self._get_forecast_5d()
        
        # 3. 生成HTML邮件
        html_content = self._format_html_email(current_weather, forecast or [])
        
        # 4. 发送邮件
        print(f"📧 开始发送邮件到 {len(self.receiver_emails)} 个收件人...")
        success, failure = self.send_email(html_content)
        
        if success > 0:
            return {
                "success": True,
                "message": f"邮件发送完成: 成功 {success} 封, 失败 {failure} 封",
                "city": self.location_city,
                "current_temp": current_weather['temp'],
                "weather": current_weather['weather_desc'],
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {"success": False, "error": "所有邮件发送失败"}


if __name__ == "__main__":
    # 检查必要的环境变量
    required_vars = ["SENDER_EMAIL", "SENDER_AUTH_CODE", "RECEIVER_EMAILS", "OPENWEATHER_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ 缺少必要的环境变量: {', '.join(missing_vars)}")
        print("请在GitHub Secrets中配置以下变量:")
        for var in missing_vars:
            print(f"  - {var}")
        exit(1)
    
    # 运行天气邮件发送程序
    sender = OpenWeatherMailSender()
    result = sender.run()
    
    print(f"📊 执行结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
