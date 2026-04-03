import json
import os
import smtplib
import math
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional, Tuple

class WeatherMailSender:
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
                "wuliying49@sina.com",
                "hitiqemoj90@gmail.com",
                "3907928171@qq.com",
                "1726960087@qq.com", 
                "wuliying2026@outlook.com"
            ]
        
        # OpenWeatherMap 配置
        self.location_city = os.environ.get('LOCATION_CITY', 'Huzhou')
        self.openweather_api_key = os.environ.get('OPENWEATHER_API_KEY', 'f56eb3db2d21132c03abb35243ca60dc')
        
        # 免费API端点
        self.current_weather_url = "https://api.openweathermap.org/data/2.5/weather"
        self.forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        
        # SMTP 配置
        self.smtp_server = "smtp.sina.com"
        self.smtp_port = 465
        
        # 天气图标映射
        self.weather_icon_map = {
            "01": "☀️",  "02": "⛅",  "03": "☁️",  "04": "☁️",
            "09": "🌧️",  "10": "🌧️",  "11": "⛈️",  "13": "❄️",  "50": "🌫️"
        }
        
        print(f"📧 发件人: {self.sender_email}")
        print(f"📧 收件人: {', '.join(self.receiver_emails)}")
        print(f"📍 城市: {self.location_city}")
        print(f"🔑 API Key: {self.openweather_api_key[:8]}...")

    def _get_current_weather(self) -> Optional[Dict]:
        """获取当前天气（使用免费API）"""
        try:
            print("🌤️ 获取当前天气...")
            
            params = {
                'q': self.location_city,
                'appid': self.openweather_api_key,
                'units': 'metric',
                'lang': 'zh_cn'
            }
            
            response = requests.get(self.current_weather_url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ 当前天气API错误 {response.status_code}: {response.text}")
                return None
            
            data = response.json()
            
            # 计算露点温度
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            dew_point = self._calculate_dew_point(temp, humidity)
            frost_point = dew_point if dew_point <= 0 else None
            
            # 风向
            wind_deg = data['wind'].get('deg', 0)
            wind_dir = self._get_wind_direction(wind_deg)
            
            current = {
                'city': data.get('name', self.location_city),
                'temp': round(temp, 1),
                'feels_like': round(data['main']['feels_like'], 1),
                'dew_point': round(dew_point, 1),
                'frost_point': round(frost_point, 1) if frost_point else None,
                'temp_min': round(data['main']['temp_min'], 1),
                'temp_max': round(data['main']['temp_max'], 1),
                'humidity': humidity,
                'pressure': data['main']['pressure'],
                'weather_main': data['weather'][0]['main'],
                'weather_desc': data['weather'][0]['description'],
                'weather_icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'wind_deg': wind_deg,
                'wind_dir': wind_dir,
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

    def _get_5day_forecast(self) -> Optional[List[Dict]]:
        """获取5天天气预报（使用免费API）"""
        try:
            print("📅 获取5天天气预报...")
            
            params = {
                'q': self.location_city,
                'appid': self.openweather_api_key,
                'units': 'metric',
                'lang': 'zh_cn',
                'cnt': 40  # 5天 * 8个时间段
            }
            
            response = requests.get(self.forecast_url, params=params, timeout=10)
            
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
                        'temps': [], 'weathers': [], 'humidity': [], 'timestamps': []
                    }
                daily_forecasts[date]['temps'].append(item['main']['temp'])
                daily_forecasts[date]['weathers'].append(item['weather'][0]['description'])
                daily_forecasts[date]['humidity'].append(item['main']['humidity'])
                daily_forecasts[date]['timestamps'].append(item['dt_txt'])
            
            # 转换为每日预报
            forecasts = []
            for i, (date, values) in enumerate(daily_forecasts.items()):
                if i >= 5:  # 只取5天
                    break
                    
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                weekday = ["一", "二", "三", "四", "五", "六", "日"][date_obj.weekday()]
                
                forecasts.append({
                    'date': date,
                    'date_display': f"{date_obj.month}/{date_obj.day} 周{weekday}",
                    'temp_min': round(min(values['temps']), 1),
                    'temp_max': round(max(values['temps']), 1),
                    'temp_avg': round(sum(values['temps']) / len(values['temps']), 1),
                    'weather': max(set(values['weathers']), key=values['weathers'].count),
                    'humidity_avg': round(sum(values['humidity']) / len(values['humidity']), 1)
                })
            
            print(f"✅ 获取到 {len(forecasts)} 天预报")
            return forecasts
            
        except Exception as e:
            print(f"❌ 获取天气预报失败: {e}")
            return None

    def _calculate_life_indices(self, current: Dict) -> Dict:
        """计算生活指数"""
        indices = {}
        
        # 感冒指数
        temp_diff = current['temp_max'] - current['temp_min']
        if temp_diff > 8 or current['humidity'] > 80:
            indices['感冒指数'] = {'level': 4, 'desc': '极易发', '建议': '注意保暖防寒'}
        elif temp_diff > 5 or current['humidity'] > 70:
            indices['感冒指数'] = {'level': 3, 'desc': '易发', '建议': '注意增减衣物'}
        else:
            indices['感冒指数'] = {'level': 1, 'desc': '不易发', '建议': '天气舒适'}
        
        # 运动指数
        if current['weather_main'].lower() in ['rain', 'snow', 'thunderstorm']:
            indices['运动指数'] = {'level': 4, 'desc': '不宜', '建议': '建议室内运动'}
        elif current['weather_main'].lower() in ['clouds', 'mist', 'haze']:
            indices['运动指数'] = {'level': 2, 'desc': '较适宜', '建议': '可进行户外运动'}
        else:
            indices['运动指数'] = {'level': 1, 'desc': '适宜', '建议': '适宜户外运动'}
        
        return indices

    def _calculate_dew_point(self, temp: float, humidity: float) -> float:
        """计算露点温度"""
        alpha = 17.27
        beta = 237.7
        gamma = (alpha * temp) / (beta + temp) + math.log(humidity / 100.0)
        dew_point = (beta * gamma) / (alpha - gamma)
        return round(dew_point, 1)

    def _get_wind_direction(self, degrees: float) -> str:
        """将角度转换为风向"""
        directions = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
        index = round(degrees / 45) % 8
        return directions[index]

    def _format_html_email(self, current: Dict, forecasts: List[Dict], life_indices: Dict) -> str:
        """生成HTML邮件"""
        today = datetime.now()
        today_str = today.strftime('%Y年%m月%d日')
        
        icon = self.weather_icon_map.get(current.get('weather_icon', '01d')[:2], '🌤️')
        
        # 当前天气
        current_html = f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 15px; margin-bottom: 20px;">
            <h1 style="margin: 0; text-align: center;">{icon} {current['city']} 天气预报</h1>
            <p style="text-align: center; opacity: 0.9;">{today_str}</p>
            
            <div style="display: flex; align-items: center; justify-content: center; margin: 20px 0;">
                <div style="text-align: center;">
                    <div style="font-size: 4em; font-weight: 300;">{current['temp']}°C</div>
                    <div style="font-size: 1.2em;">{current['weather_desc']}</div>
                    <div style="opacity: 0.9;">体感: {current['feels_like']}°C</div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 20px;">
                <div><strong>🌡️ 最低/最高</strong><br>{current['temp_min']}°C / {current['temp_max']}°C</div>
                <div><strong>💧 湿度</strong><br>{current['humidity']}%</div>
                <div><strong>💨 风速</strong><br>{current['wind_speed']} m/s {current['wind_dir']}风</div>
                <div><strong>📊 气压</strong><br>{current['pressure']} hPa</div>
                <div><strong>🌡️ 露点</strong><br>{current['dew_point']}°C</div>
                <div><strong>☀️ 日出/日落</strong><br>{current['sunrise']} / {current['sunset']}</div>
            </div>
        </div>
        """
        
        # 生活指数
        life_indices_html = ""
        if life_indices:
            life_indices_html = """
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #2c3e50;">📊 生活指数</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
            """
            
            for name, data in life_indices.items():
                level_color = "#27ae60" if data['level'] <= 2 else "#e74c3c"
                life_indices_html += f"""
                <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {level_color};">
                    <strong>{name}</strong>
                    <div style="margin: 5px 0;">
                        <span style="background: {level_color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.9em;">
                            {data['desc']}
                        </span>
                    </div>
                    <div style="color: #666; font-size: 0.9em;">{data['建议']}</div>
                </div>
                """
            
            life_indices_html += "</div></div>"
        
        # 5天预报
        forecast_html = ""
        if forecasts:
            forecast_html = """
            <h3 style="color: #2c3e50; border-left: 4px solid #3498db; padding-left: 10px;">📅 5天天气预报</h3>
            <div style="overflow-x: auto; margin: 20px 0;">
                <table style="width: 100%; border-collapse: collapse; min-width: 500px;">
                    <thead>
                        <tr style="background: #2c3e50; color: white;">
                            <th style="padding: 12px; text-align: left;">日期</th>
                            <th style="padding: 12px; text-align: left;">天气</th>
                            <th style="padding: 12px; text-align: left;">温度 (°C)</th>
                            <th style="padding: 12px; text-align: left;">湿度</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for day in forecasts:
                forecast_html += f"""
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 12px;"><strong>{day['date_display']}</strong></td>
                    <td style="padding: 12px;">{day['weather']}</td>
                    <td style="padding: 12px;">{day['temp_min']}~{day['temp_max']}°C</td>
                    <td style="padding: 12px;">{day['humidity_avg']}%</td>
                </tr>
                """
            
            forecast_html += "</tbody></table></div>"
        
        # 完整HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: 'Microsoft YaHei', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: #f5f7fa;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    overflow: hidden;
                    box-shadow: 0 10px 20px rgba(0,0,0,0.1);
                }}
                .content {{
                    padding: 25px;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    background: #f8f9fa;
                    color: #666;
                    font-size: 13px;
                    border-top: 1px solid #eee;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    {current_html}
                    {life_indices_html}
                    {forecast_html}
                </div>
                <div class="footer">
                    <p>数据来源: OpenWeatherMap 免费API | 自动发送服务</p>
                    <p>© {today.year} 天气助手 | 本邮件自动生成，无需付费订阅</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html

    def send_email(self, html: str) -> Tuple[int, int]:
        """发送邮件"""
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
                
                msg.attach(MIMEText(html, 'html', 'utf-8'))
                
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
        print(f"【{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}】开始执行")
        
        # 获取当前天气
        current = self._get_current_weather()
        if not current:
            return {"success": False, "error": "获取当前天气失败"}
        
        # 获取5天预报
        forecasts = self._get_5day_forecast()
        
        # 计算生活指数
        life_indices = self._calculate_life_indices(current)
        
        # 生成邮件
        html = self._format_html_email(current, forecasts or [], life_indices)
        
        # 发送邮件
        print(f"📧 开始发送邮件到 {len(self.receiver_emails)} 个收件人...")
        success, failure = self.send_email(html)
        
        if success > 0:
            return {
                "success": True,
                "message": f"成功 {success} 封, 失败 {failure} 封",
                "city": self.location_city,
                "recipients": len(self.receiver_emails),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {"success": False, "error": "所有邮件发送失败"}


if __name__ == "__main__":
    # 检查环境变量
    required = ["SENDER_EMAIL", "SENDER_AUTH_CODE", "RECEIVER_EMAILS", "OPENWEATHER_API_KEY"]
    missing = [var for var in required if not os.environ.get(var)]
    
    if missing:
        print(f"❌ 缺少环境变量: {', '.join(missing)}")
        exit(1)
    
    # 运行
    sender = WeatherMailSender()
    result = sender.run()
    
    print(f"📊 执行结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
