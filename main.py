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
            "01": "☀️",  "02": "⛅",  "03": "☁️",  "04": "☁️",
            "09": "🌧️",  "10": "🌧️",  "11": "⛈️",  "13": "❄️",  "50": "🌫️"
        }
        
        # 风向映射
        self.wind_direction_map = {
            "N": "北", "NNE": "东北偏北", "NE": "东北", "ENE": "东北偏东",
            "E": "东", "ESE": "东南偏东", "SE": "东南", "SSE": "东南偏南",
            "S": "南", "SSW": "西南偏南", "SW": "西南", "WSW": "西南偏西",
            "W": "西", "WNW": "西北偏西", "NW": "西北", "NNW": "西北偏北"
        }
        
        # 月相映射
        self.moon_phase_map = {
            0: "🌑 新月", 0.25: "🌓 上弦月", 0.5: "🌕 满月", 0.75: "🌗 下弦月",
            0.125: "🌒 娥眉月", 0.375: "🌔 盈凸月", 0.625: "🌖 亏凸月", 0.875: "🌘 残月"
        }
        
        # 星座映射
        self.zodiac_signs = [
            "♈ 白羊座 (3.21-4.19)", "♉ 金牛座 (4.20-5.20)", "♊ 双子座 (5.21-6.21)",
            "♋ 巨蟹座 (6.22-7.22)", "♌ 狮子座 (7.23-8.22)", "♍ 处女座 (8.23-9.22)",
            "♎ 天秤座 (9.23-10.23)", "♏ 天蝎座 (10.24-11.22)", "♐ 射手座 (11.23-12.21)",
            "♑ 摩羯座 (12.22-1.19)", "♒ 水瓶座 (1.20-2.18)", "♓ 双鱼座 (2.19-3.20)"
        ]

    def _get_current_weather(self) -> Optional[Dict]:
        """获取当前天气"""
        try:
            print("🌤️ 获取当前天气数据...")
            url = f"{self.base_url}/weather"
            params = {
                'q': self.location_city,
                'appid': self.openweather_api_key,
                'units': 'metric',
                'lang': 'zh_cn'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ API错误 {response.status_code}: {response.text}")
                return None
            
            data = response.json()
            
            # 计算露点温度 (近似计算)
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            dew_point = self._calculate_dew_point(temp, humidity)
            
            # 计算霜点温度 (近似等于露点温度，当温度低于0°C时)
            frost_point = dew_point if dew_point <= 0 else None
            
            # 获取风向
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
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'weather_main': data['weather'][0]['main'],
                'weather_desc': data['weather'][0]['description'],
                'weather_icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'wind_deg': wind_deg,
                'wind_dir': wind_dir,
                'clouds': data['clouds']['all'],
                'visibility': data.get('visibility', 10000) / 1000,
                'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M'),
                'sunset': datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M'),
                'time': datetime.fromtimestamp(data['dt']).strftime('%Y-%m-%d %H:%M')
            }
            
            print(f"✅ 当前天气: {current['temp']}°C, {current['weather_desc']}")
            return current
            
        except Exception as e:
            print(f"❌ 获取当前天气失败: {e}")
            return None

    def _get_forecast_16d(self) -> Optional[List[Dict]]:
        """获取16天天气预报"""
        try:
            print("📅 获取16天天气预报...")
            # OpenWeatherMap 的 forecast/daily 端点最多返回16天
            url = f"{self.base_url}/forecast/daily"
            params = {
                'q': self.location_city,
                'appid': self.openweather_api_key,
                'units': 'metric',
                'cnt': 16,  # 16天预报
                'lang': 'zh_cn'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ 预报API错误 {response.status_code}: {response.text}")
                return None
            
            data = response.json()
            forecasts = []
            
            for i, day in enumerate(data.get('list', [])[:14]):  # 只取14天
                date_obj = datetime.fromtimestamp(day['dt'])
                weekday = ["一", "二", "三", "四", "五", "六", "日"][date_obj.weekday()]
                
                # 计算露点和霜点
                temp = (day['temp']['day'] + day['temp']['night']) / 2
                humidity = day['humidity']
                dew_point = self._calculate_dew_point(temp, humidity)
                frost_point = dew_point if dew_point <= 0 else None
                
                # 获取风向
                wind_deg = day.get('deg', 0)
                wind_dir = self._get_wind_direction(wind_deg)
                
                forecast = {
                    'date': date_obj.strftime('%Y-%m-%d'),
                    'date_display': f"{date_obj.month}/{date_obj.day} 周{weekday}",
                    'temp_day': round(day['temp']['day'], 1),
                    'temp_night': round(day['temp']['night'], 1),
                    'temp_min': round(day['temp']['min'], 1),
                    'temp_max': round(day['temp']['max'], 1),
                    'feels_like_day': round(day.get('feels_like', {}).get('day', day['temp']['day']), 1),
                    'feels_like_night': round(day.get('feels_like', {}).get('night', day['temp']['night']), 1),
                    'dew_point': round(dew_point, 1),
                    'frost_point': round(frost_point, 1) if frost_point else None,
                    'weather': day['weather'][0]['description'],
                    'weather_icon': day['weather'][0]['icon'],
                    'humidity': day['humidity'],
                    'pressure': day.get('pressure', 1013),
                    'wind_speed': day.get('speed', 0),
                    'wind_deg': wind_deg,
                    'wind_dir': wind_dir,
                    'clouds': day.get('clouds', 0),
                    'uvi': day.get('uvi', 0),  # 紫外线指数
                }
                forecasts.append(forecast)
            
            print(f"✅ 获取到 {len(forecasts)} 天预报")
            return forecasts
            
        except Exception as e:
            print(f"❌ 获取天气预报失败: {e}")
            return None

    def _get_astronomical_data(self) -> Optional[Dict]:
        """获取天文数据（月出、月落、月相等）"""
        try:
            print("🌙 获取天文数据...")
            # 注意：OpenWeatherMap 不直接提供月出月落数据
            # 这里使用一个简单的近似算法
            today = datetime.now()
            
            # 获取月相近似值（基于农历日期计算）
            lunar_date = self._get_lunar_date(today)
            moon_phase = lunar_date.get('moon_phase', 0)
            moon_phase_desc = self._get_moon_phase_desc(moon_phase)
            
            # 计算月出月落时间（近似计算）
            moonrise, moonset = self._calculate_moon_times(today, self.location_city)
            
            # 获取星座
            zodiac_index = (today.month - 1) % 12
            zodiac_sign = self.zodiac_signs[zodiac_index]
            
            # 计算季节
            season = self._get_season(today)
            
            # 计算月龄
            moon_age = lunar_date.get('moon_age', 0)
            
            # 月亮亮度（近似值）
            moon_brightness = round((1 - abs(2 * moon_phase - 1)) * 100, 1)
            
            # 明天的日期
            tomorrow = today + timedelta(days=1)
            tomorrow_sunrise, tomorrow_sunset = self._calculate_sun_times(tomorrow, self.location_city)
            tomorrow_moonrise, tomorrow_moonset = self._calculate_moon_times(tomorrow, self.location_city)
            
            astronomical_data = {
                'moonrise': moonrise,
                'moonset': moonset,
                'moon_phase': moon_phase,
                'moon_phase_desc': moon_phase_desc,
                'moon_age': moon_age,
                'moon_brightness': f"{moon_brightness}%",
                'zodiac': zodiac_sign,
                'season': season,
                'tomorrow_sunrise': tomorrow_sunrise,
                'tomorrow_sunset': tomorrow_sunset,
                'tomorrow_moonrise': tomorrow_moonrise,
                'tomorrow_moonset': tomorrow_moonset
            }
            
            print(f"✅ 天文数据: {moon_phase_desc}")
            return astronomical_data
            
        except Exception as e:
            print(f"❌ 获取天文数据失败: {e}")
            return None

    def _calculate_dew_point(self, temp: float, humidity: float) -> float:
        """计算露点温度（近似公式）"""
        # 使用 Magnus 公式近似计算
        alpha = 17.27
        beta = 237.7
        gamma = (alpha * temp) / (beta + temp) + math.log(humidity / 100.0)
        dew_point = (beta * gamma) / (alpha - gamma)
        return round(dew_point, 1)

    def _get_wind_direction(self, degrees: float) -> str:
        """将角度转换为风向"""
        directions = list(self.wind_direction_map.keys())
        index = round(degrees / (360.0 / len(directions))) % len(directions)
        return self.wind_direction_map.get(directions[index], "未知")

    def _get_lunar_date(self, date: datetime) -> Dict:
        """获取农历日期（简化版）"""
        # 这是一个简化的农历计算，实际应该使用完整的农历库
        # 这里返回近似值用于演示
        year, month, day = date.year, date.month, date.day
        
        # 简化计算月龄（基于朔望月周期29.53天）
        base_date = datetime(2000, 1, 6)  # 2000年第一个新月
        days_diff = (date - base_date).days
        moon_age = days_diff % 29.530588
        
        # 计算月相
        moon_phase = moon_age / 29.530588
        
        return {
            'moon_age': round(moon_age, 1),
            'moon_phase': round(moon_phase, 3)
        }

    def _get_moon_phase_desc(self, moon_phase: float) -> str:
        """获取月相描述"""
        phases = [
            (0, 0.03, "🌑 新月"),
            (0.03, 0.22, "🌒 娥眉月"),
            (0.22, 0.28, "🌓 上弦月"),
            (0.28, 0.47, "🌔 盈凸月"),
            (0.47, 0.53, "🌕 满月"),
            (0.53, 0.72, "🌖 亏凸月"),
            (0.72, 0.78, "🌗 下弦月"),
            (0.78, 0.97, "🌘 残月"),
            (0.97, 1.0, "🌑 新月")
        ]
        
        for start, end, desc in phases:
            if start <= moon_phase < end:
                return desc
        return "🌑 新月"

    def _calculate_sun_times(self, date: datetime, city: str) -> Tuple[str, str]:
        """计算日出日落时间（简化版）"""
        # 这里使用固定时间作为演示
        # 实际应该使用精确的天文计算
        month = date.month
        if 3 <= month <= 5:  # 春季
            sunrise, sunset = "06:00", "18:30"
        elif 6 <= month <= 8:  # 夏季
            sunrise, sunset = "05:30", "19:30"
        elif 9 <= month <= 11:  # 秋季
            sunrise, sunset = "06:30", "18:00"
        else:  # 冬季
            sunrise, sunset = "07:00", "17:30"
        return sunrise, sunset

    def _calculate_moon_times(self, date: datetime, city: str) -> Tuple[str, str]:
        """计算月出月落时间（简化版）"""
        # 这里使用固定时间作为演示
        # 实际应该使用精确的天文计算
        moonrise = "18:45"
        moonset = "07:20"
        return moonrise, moonset

    def _get_season(self, date: datetime) -> str:
        """获取季节"""
        month = date.month
        if 3 <= month <= 5:
            return "春季"
        elif 6 <= month <= 8:
            return "夏季"
        elif 9 <= month <= 11:
            return "秋季"
        else:
            return "冬季"

    def _format_html_email(self, current: Dict, forecasts: List[Dict], astro: Dict) -> str:
        """生成包含14天预报和天文数据的HTML邮件"""
        today = datetime.now()
        today_str = today.strftime('%Y年%m月%d日')
        weekday = ["一", "二", "三", "四", "五", "六", "日"][today.weekday()]
        
        # 获取天气图标
        icon_code = current.get('weather_icon', '01d')
        icon = self.weather_icon_map.get(icon_code[:2], '🌤️')
        
        # 当前天气卡片
        current_html = f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 25px;">
            <div style="text-align: center;">
                <h1 style="margin: 0 0 10px 0; font-size: 2.2em;">{icon} {current['city']}天气预报</h1>
                <p style="opacity: 0.9; font-size: 1.1em;">{today_str} 周{weekday} | 数据更新时间: {current.get('time', '')}</p>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 25px; flex-wrap: wrap;">
                <div style="text-align: center; flex: 1; min-width: 200px;">
                    <div style="font-size: 4.5em; font-weight: 300; line-height: 1;">{current['temp']}°C</div>
                    <div style="font-size: 1.3em; margin: 10px 0;">{current['weather_desc']}</div>
                    <div style="opacity: 0.9;">体感: {current['feels_like']}°C</div>
                </div>
                
                <div style="flex: 1; min-width: 250px;">
                    <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div><strong>🌡️ 体感温度</strong><br>{current['feels_like']}°C</div>
                            <div><strong>💧 湿度</strong><br>{current['humidity']}%</div>
                            <div><strong>💨 风速/风向</strong><br>{current['wind_speed']} m/s {current['wind_dir']}</div>
                            <div><strong>📊 气压</strong><br>{current['pressure']} hPa</div>
                            <div><strong>🌡️ 露点温度</strong><br>{current['dew_point']}°C</div>
                            <div><strong>❄️ 霜点温度</strong><br>{current.get('frost_point', 'N/A')}°C</div>
                            <div><strong>☀️ 日出</strong><br>{current.get('sunrise', '--:--')}</div>
                            <div><strong>🌙 日落</strong><br>{current.get('sunset', '--:--')}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        # 天文数据卡片
        astro_html = f"""
        <div style="background: #2c3e50; color: white; padding: 25px; border-radius: 15px; margin: 25px 0;">
            <h3 style="margin-top: 0; color: #ecf0f1;">🌌 天文信息</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div>
                    <strong>🌙 月相</strong><br>{astro.get('moon_phase_desc', '未知')}
                </div>
                <div>
                    <strong>🌄 月出</strong><br>{astro.get('moonrise', '--:--')}
                </div>
                <div>
                    <strong>🌅 月落</strong><br>{astro.get('moonset', '--:--')}
                </div>
                <div>
                    <strong>🔢 月龄</strong><br>{astro.get('moon_age', 0)} 天
                </div>
                <div>
                    <strong>💡 月亮亮度</strong><br>{astro.get('moon_brightness', '0%')}
                </div>
                <div>
                    <strong>♈ 星座</strong><br>{astro.get('zodiac', '未知')}
                </div>
                <div>
                    <strong>🌱 季节</strong><br>{astro.get('season', '未知')}
                </div>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px;">
                <h4 style="margin-top: 0; color: #bdc3c7;">📅 明天信息</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                    <div><strong>☀️ 日出</strong><br>{astro.get('tomorrow_sunrise', '--:--')}</div>
                    <div><strong>🌙 日落</strong><br>{astro.get('tomorrow_sunset', '--:--')}</div>
                    <div><strong>🌄 月出</strong><br>{astro.get('tomorrow_moonrise', '--:--')}</div>
                    <div><strong>🌅 月落</strong><br>{astro.get('tomorrow_moonset', '--:--')}</div>
                </div>
            </div>
        </div>
        """
        
        # 14天预报表格
        forecast_html = ""
        if forecasts:
            forecast_html = """
            <h3 style="color: #2c3e50; border-left: 5px solid #3498db; padding-left: 15px; margin: 25px 0 20px 0;">📅 14天天气预报</h3>
            
            <div style="overflow-x: auto; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.05);">
                <table style="width: 100%; border-collapse: collapse; min-width: 800px;">
                    <thead>
                        <tr style="background: #2c3e50; color: white;">
                            <th style="padding: 12px; text-align: left;">日期</th>
                            <th style="padding: 12px; text-align: left;">天气</th>
                            <th style="padding: 12px; text-align: left;">温度 (°C)</th>
                            <th style="padding: 12px; text-align: left;">体感</th>
                            <th style="padding: 12px; text-align: left;">湿度</th>
                            <th style="padding: 12px; text-align: left;">风速</th>
                            <th style="padding: 12px; text-align: left;">风向</th>
                            <th style="padding: 12px; text-align: left;">UV</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for i, day in enumerate(forecasts[:14]):  # 确保只显示14天
                bg_color = "#f8f9fa" if i % 2 == 0 else "white"
                day_icon = self.weather_icon_map.get(day.get('weather_icon', '01d')[:2], '🌤️')
                
                # 温度范围
                temp_range = f"{day['temp_min']}~{day['temp_max']}"
                
                forecast_html += f"""
                <tr style="background: {bg_color};">
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        <strong>{day['date_display']}</strong>
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        {day_icon} {day['weather']}
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        {temp_range}
                        <div style="font-size: 0.85em; color: #666;">
                            昼: {day['temp_day']}°C | 夜: {day['temp_night']}°C
                        </div>
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        昼: {day['feels_like_day']}°C<br>夜: {day['feels_like_night']}°C
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        {day['humidity']}%
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        {day['wind_speed']} m/s
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        {day['wind_dir']}
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        {day.get('uvi', 0)}
                    </td>
                </tr>
                """
            
            forecast_html += """
                    </tbody>
                </table>
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
                    max-width: 1200px;
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
                    {astro_html}
                    {forecast_html}
                </div>
                <div class="footer">
                    <p>数据来源: OpenWeatherMap | 自动发送服务 | 更新频率: 每日00:00</p>
                    <p>© {today.year} 天气助手 | 本邮件由自动化脚本生成，包含14天预报和天文数据</p>
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
        
        # 2. 获取14天预报
        forecast = self._get_forecast_16d()
        
        # 3. 获取天文数据
        astronomical_data = self._get_astronomical_data() or {}
        
        # 4. 生成HTML邮件
        html_content = self._format_html_email(current_weather, forecast or [], astronomical_data)
        
        # 5. 发送邮件
        print(f"📧 开始发送邮件到 {len(self.receiver_emails)} 个收件人...")
        success, failure = self.send_email(html_content)
        
        if success > 0:
            return {
                "success": True,
                "message": f"邮件发送完成: 成功 {success} 封, 失败 {failure} 封",
                "city": self.location_city,
                "current_temp": current_weather['temp'],
                "weather": current_weather['weather_desc'],
                "forecast_days": len(forecast) if forecast else 0,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {"success": False, "error": "所有邮件发送失败"}


if __name__ == "__main__":
    # 需要导入 math 模块用于计算
    import math
    
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
