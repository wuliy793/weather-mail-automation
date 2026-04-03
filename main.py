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

class OpenWeatherMailSender:
    def __init__(self):
        # 从环境变量读取配置
        self.sender_email = os.environ.get('SENDER_EMAIL', 'wuliying49@sina.com')
        self.sender_auth_code = os.environ.get('SENDER_AUTH_CODE', 'ec1f17a5e11f0d82')
        
        # 收件人列表（更新）
        receivers_str = os.environ.get('RECEIVER_EMAILS', '')
        if receivers_str:
            self.receiver_emails = [email.strip() for email in receivers_str.split(',')]
        else:
            # 默认收件人（包含wuliying49@sina.com和hitiqemoj90@gmail.com）
            self.receiver_emails = [
                "wuliying49@sina.com",        # 您自己
                "hitiqemoj90@gmail.com",       # 新增
                "3907928171@qq.com",
                "1726960087@qq.com", 
                "wuliying2026@outlook.com"
            ]
        
        # OpenWeatherMap 配置
        self.location_city = os.environ.get('LOCATION_CITY', 'Huzhou')
        self.openweather_api_key = os.environ.get('OPENWEATHER_API_KEY', 'f56eb3db2d21132c03abb35243ca60dc')
        
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
        
        # 生活指数图标
        self.life_index_icons = {
            "感冒指数": "🤧", "运动指数": "🏃", "穿衣指数": "👕", "洗车指数": "🚗",
            "紫外线指数": "☀️", "空气污染扩散": "🏭", "钓鱼指数": "🎣", "旅游指数": "✈️",
            "防晒指数": "🧴", "交通指数": "🚦", "舒适度指数": "😊", "过敏指数": "🤧"
        }
        
        print(f"发件人: {self.sender_email}")
        print(f"收件人: {', '.join(self.receiver_emails)}")
        print(f"城市: {self.location_city}")
        print(f"OpenWeatherMap API Key: {self.openweather_api_key[:8]}...")

    def _get_coordinates(self) -> Optional[Tuple[float, float]]:
        """获取城市经纬度坐标"""
        try:
            print("📍 获取城市坐标...")
            url = "http://api.openweathermap.org/geo/1.0/direct"
            params = {
                'q': self.location_city,
                'limit': 1,
                'appid': self.openweather_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ 坐标API错误 {response.status_code}: {response.text}")
                return None
            
            data = response.json()
            if not data:
                print(f"❌ 未找到城市: {self.location_city}")
                return None
            
            lat = data[0]['lat']
            lon = data[0]['lon']
            city_name = data[0].get('name', self.location_city)
            
            print(f"✅ 城市坐标: {city_name} ({lat}, {lon})")
            return lat, lon, city_name
            
        except Exception as e:
            print(f"❌ 获取坐标失败: {e}")
            return None

    def _get_onecall_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """使用One Call API 3.0获取天气数据（免费）"""
        try:
            print("🌤️ 获取One Call API数据...")
            url = f"https://api.openweathermap.org/data/3.0/onecall"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.openweather_api_key,
                'units': 'metric',
                'lang': 'zh',
                'exclude': 'minutely,hourly'  # 排除分钟和小时数据
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ One Call API错误 {response.status_code}: {response.text}")
                return None
            
            data = response.json()
            return data
            
        except Exception as e:
            print(f"❌ 获取One Call数据失败: {e}")
            return None

    def _get_current_weather_detailed(self) -> Optional[Dict]:
        """获取当前天气详细信息"""
        try:
            print("🌡️ 获取当前天气详情...")
            coords = self._get_coordinates()
            if not coords:
                return None
            
            lat, lon, city_name = coords
            onecall_data = self._get_onecall_weather(lat, lon)
            if not onecall_data:
                return None
            
            current = onecall_data.get('current', {})
            daily = onecall_data.get('daily', [])
            
            if not daily:
                return None
            
            today = daily[0]
            
            # 计算露点温度
            temp = current.get('temp', 0)
            humidity = current.get('humidity', 0)
            dew_point = self._calculate_dew_point(temp, humidity)
            frost_point = dew_point if dew_point <= 0 else None
            
            # 获取风向
            wind_deg = current.get('wind_deg', 0)
            wind_dir = self._get_wind_direction(wind_deg)
            
            # 获取日出日落时间
            sunrise_time = datetime.fromtimestamp(current.get('sunrise', 0)).strftime('%H:%M')
            sunset_time = datetime.fromtimestamp(current.get('sunset', 0)).strftime('%H:%M')
            
            current_weather = {
                'city': city_name,
                'temp': round(temp, 1),
                'feels_like': round(current.get('feels_like', temp), 1),
                'dew_point': round(dew_point, 1),
                'frost_point': round(frost_point, 1) if frost_point else None,
                'temp_min': round(today.get('temp', {}).get('min', temp), 1),
                'temp_max': round(today.get('temp', {}).get('max', temp), 1),
                'humidity': humidity,
                'pressure': current.get('pressure', 1013),
                'weather_main': current.get('weather', [{}])[0].get('main', '未知'),
                'weather_desc': current.get('weather', [{}])[0].get('description', '未知'),
                'weather_icon': current.get('weather', [{}])[0].get('icon', '01d'),
                'wind_speed': current.get('wind_speed', 0),
                'wind_deg': wind_deg,
                'wind_dir': wind_dir,
                'clouds': current.get('clouds', 0),
                'uvi': current.get('uvi', 0),  # 紫外线指数
                'visibility': current.get('visibility', 10000) / 1000,
                'sunrise': sunrise_time,
                'sunset': sunset_time,
                'time': datetime.fromtimestamp(current.get('dt', 0)).strftime('%Y-%m-%d %H:%M')
            }
            
            print(f"✅ 当前天气: {current_weather['temp']}°C, {current_weather['weather_desc']}")
            return current_weather
            
        except Exception as e:
            print(f"❌ 获取当前天气详情失败: {e}")
            return None

    def _get_8day_forecast(self) -> Optional[List[Dict]]:
        """获取8天天气预报（One Call API免费版）"""
        try:
            print("📅 获取8天天气预报...")
            coords = self._get_coordinates()
            if not coords:
                return None
            
            lat, lon, _ = coords
            onecall_data = self._get_onecall_weather(lat, lon)
            if not onecall_data:
                return None
            
            daily_forecasts = onecall_data.get('daily', [])
            
            if not daily_forecasts:
                return None
            
            forecasts = []
            
            for i, day in enumerate(daily_forecasts[:8]):  # 最多8天
                date_obj = datetime.fromtimestamp(day['dt'])
                weekday = ["一", "二", "三", "四", "五", "六", "日"][date_obj.weekday()]
                
                # 计算露点和霜点
                temp_day = day.get('temp', {}).get('day', 0)
                humidity = day.get('humidity', 0)
                dew_point = self._calculate_dew_point(temp_day, humidity)
                frost_point = dew_point if dew_point <= 0 else None
                
                # 获取风向
                wind_deg = day.get('wind_deg', 0)
                wind_dir = self._get_wind_direction(wind_deg)
                
                # 获取月出月落（如果有）
                moonrise = day.get('moonrise')
                moonset = day.get('moonset')
                moonrise_time = datetime.fromtimestamp(moonrise).strftime('%H:%M') if moonrise else '--:--'
                moonset_time = datetime.fromtimestamp(moonset).strftime('%H:%M') if moonset else '--:--'
                
                # 月相
                moon_phase = day.get('moon_phase', 0)
                moon_phase_desc = self._get_moon_phase_desc(moon_phase)
                
                forecast = {
                    'date': date_obj.strftime('%Y-%m-%d'),
                    'date_display': f"{date_obj.month}/{date_obj.day} 周{weekday}",
                    'temp_day': round(day.get('temp', {}).get('day', 0), 1),
                    'temp_night': round(day.get('temp', {}).get('night', 0), 1),
                    'temp_min': round(day.get('temp', {}).get('min', 0), 1),
                    'temp_max': round(day.get('temp', {}).get('max', 0), 1),
                    'feels_like_day': round(day.get('feels_like', {}).get('day', 0), 1),
                    'feels_like_night': round(day.get('feels_like', {}).get('night', 0), 1),
                    'dew_point': round(dew_point, 1),
                    'frost_point': round(frost_point, 1) if frost_point else None,
                    'weather': day.get('weather', [{}])[0].get('description', '未知'),
                    'weather_icon': day.get('weather', [{}])[0].get('icon', '01d'),
                    'humidity': humidity,
                    'pressure': day.get('pressure', 1013),
                    'wind_speed': day.get('wind_speed', 0),
                    'wind_deg': wind_deg,
                    'wind_dir': wind_dir,
                    'clouds': day.get('clouds', 0),
                    'uvi': day.get('uvi', 0),  # 紫外线指数
                    'pop': round(day.get('pop', 0) * 100, 0),  # 降水概率百分比
                    'sunrise': datetime.fromtimestamp(day.get('sunrise', 0)).strftime('%H:%M'),
                    'sunset': datetime.fromtimestamp(day.get('sunset', 0)).strftime('%H:%M'),
                    'moonrise': moonrise_time,
                    'moonset': moonset_time,
                    'moon_phase': moon_phase,
                    'moon_phase_desc': moon_phase_desc
                }
                forecasts.append(forecast)
            
            print(f"✅ 获取到 {len(forecasts)} 天预报")
            return forecasts
            
        except Exception as e:
            print(f"❌ 获取天气预报失败: {e}")
            return None

    def _calculate_life_indices(self, current: Dict, forecast: Dict) -> Dict:
        """计算生活指数"""
        indices = {}
        
        # 感冒指数
        temp_diff = current['temp_max'] - current['temp_min']
        humidity = current['humidity']
        
        if temp_diff > 8 or humidity > 80:
            indices['感冒指数'] = {
                'level': 4,
                'desc': '极易发',
                'suggestion': '天气变化大，湿度高，极易感冒，请注意保暖防寒',
                'icon': '🤧'
            }
        elif temp_diff > 5 or humidity > 70:
            indices['感冒指数'] = {
                'level': 3,
                'desc': '易发',
                'suggestion': '昼夜温差较大，注意增减衣物',
                'icon': '🤧'
            }
        else:
            indices['感冒指数'] = {
                'level': 1,
                'desc': '不易发',
                'suggestion': '天气条件不易感冒',
                'icon': '🤧'
            }
        
        # 运动指数
        weather_main = current['weather_main'].lower()
        if weather_main in ['rain', 'snow', 'thunderstorm']:
            indices['运动指数'] = {
                'level': 4,
                'desc': '不宜',
                'suggestion': '恶劣天气，不建议户外运动',
                'icon': '🏃'
            }
        elif weather_main in ['clouds', 'mist', 'haze']:
            indices['运动指数'] = {
                'level': 2,
                'desc': '较适宜',
                'suggestion': '天气一般，可进行室内运动',
                'icon': '🏃'
            }
        else:
            indices['运动指数'] = {
                'level': 1,
                'desc': '适宜',
                'suggestion': '天气良好，适宜户外运动',
                'icon': '🏃'
            }
        
        # 穿衣指数
        temp = current['temp']
        if temp >= 28:
            indices['穿衣指数'] = {
                'level': 1,
                'desc': '炎热',
                'suggestion': '建议穿短袖、短裙、薄短裙、短裤等清凉夏季服装',
                'icon': '👕'
            }
        elif temp >= 20:
            indices['穿衣指数'] = {
                'level': 2,
                'desc': '舒适',
                'suggestion': '建议穿单层棉麻面料的短套装、T恤衫、薄牛仔衫裤等',
                'icon': '👕'
            }
        elif temp >= 10:
            indices['穿衣指数'] = {
                'level': 3,
                'desc': '较冷',
                'suggestion': '建议穿套装、夹衣、风衣、休闲装、夹克衫、西装、薄毛衣等',
                'icon': '👕'
            }
        else:
            indices['穿衣指数'] = {
                'level': 4,
                'desc': '寒冷',
                'suggestion': '建议穿棉衣、冬大衣、皮夹克、厚呢外套、呢帽、手套、羽绒服等',
                'icon': '👕'
            }
        
        # 洗车指数
        pop = forecast.get('pop', 0)  # 降水概率
        if pop > 50:
            indices['洗车指数'] = {
                'level': 4,
                'desc': '不宜',
                'suggestion': '未来有雨，不适宜洗车',
                'icon': '🚗'
            }
        elif pop > 20:
            indices['洗车指数'] = {
                'level': 3,
                'desc': '较不宜',
                'suggestion': '可能有雨，建议暂缓洗车',
                'icon': '🚗'
            }
        else:
            indices['洗车指数'] = {
                'level': 1,
                'desc': '适宜',
                'suggestion': '天气较好，适合擦洗汽车',
                'icon': '🚗'
            }
        
        # 紫外线指数
        uvi = current.get('uvi', 0)
        if uvi >= 8:
            indices['紫外线指数'] = {
                'level': 4,
                'desc': '很强',
                'suggestion': '紫外线辐射极强，必须涂抹防晒霜，避免在户外活动',
                'icon': '☀️'
            }
        elif uvi >= 6:
            indices['紫外线指数'] = {
                'level': 3,
                'desc': '强',
                'suggestion': '紫外线辐射强，建议涂擦SPF20左右防晒护肤品',
                'icon': '☀️'
            }
        elif uvi >= 3:
            indices['紫外线指数'] = {
                'level': 2,
                'desc': '中等',
                'suggestion': '紫外线辐射中等，外出时建议涂擦SPF15左右的防晒护肤品',
                'icon': '☀️'
            }
        else:
            indices['紫外线指数'] = {
                'level': 1,
                'desc': '弱',
                'suggestion': '紫外线辐射较弱，无需特别防护',
                'icon': '☀️'
            }
        
        return indices

    def _get_moon_data(self) -> Dict:
        """获取月球相关数据（简化版）"""
        today = datetime.now()
        
        # 计算月相（基于农历日期简化计算）
        base_date = datetime(2000, 1, 6)  # 2000年第一个新月
        days_diff = (today - base_date).days
        moon_age = days_diff % 29.530588
        moon_phase = moon_age / 29.530588
        
        # 获取星座
        zodiac_index = (today.month - 1) % 12
        zodiac_signs = [
            "♈ 白羊座 (3.21-4.19)", "♉ 金牛座 (4.20-5.20)", "♊ 双子座 (5.21-6.21)",
            "♋ 巨蟹座 (6.22-7.22)", "♌ 狮子座 (7.23-8.22)", "♍ 处女座 (8.23-9.22)",
            "♎ 天秤座 (9.23-10.23)", "♏ 天蝎座 (10.24-11.22)", "♐ 射手座 (11.23-12.21)",
            "♑ 摩羯座 (12.22-1.19)", "♒ 水瓶座 (1.20-2.18)", "♓ 双鱼座 (2.19-3.20)"
        ]
        zodiac_sign = zodiac_signs[zodiac_index]
        
        # 计算季节
        month = today.month
        if 3 <= month <= 5:
            season = "春季"
        elif 6 <= month <= 8:
            season = "夏季"
        elif 9 <= month <= 11:
            season = "秋季"
        else:
            season = "冬季"
        
        # 月亮亮度（近似值）
        moon_brightness = round((1 - abs(2 * moon_phase - 1)) * 100, 1)
        
        # 明天的日期
        tomorrow = today + timedelta(days=1)
        
        return {
            'moon_phase': moon_phase,
            'moon_phase_desc': self._get_moon_phase_desc(moon_phase),
            'moon_age': round(moon_age, 1),
            'moon_brightness': f"{moon_brightness}%",
            'zodiac_sign': zodiac_sign,
            'season': season,
            'tomorrow_date': tomorrow.strftime('%Y-%m-%d')
        }

    def _calculate_dew_point(self, temp: float, humidity: float) -> float:
        """计算露点温度（Magnus公式）"""
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

    def _get_moon_phase_desc(self, moon_phase: float) -> str:
        """获取月相描述"""
        if moon_phase < 0.03 or moon_phase >= 0.97:
            return "🌑 新月"
        elif moon_phase < 0.22:
            return "🌒 娥眉月"
        elif moon_phase < 0.28:
            return "🌓 上弦月"
        elif moon_phase < 0.47:
            return "🌔 盈凸月"
        elif moon_phase < 0.53:
            return "🌕 满月"
        elif moon_phase < 0.72:
            return "🌖 亏凸月"
        elif moon_phase < 0.78:
            return "🌗 下弦月"
        else:
            return "🌘 残月"

    def _format_html_email(self, current: Dict, forecasts: List[Dict], life_indices: Dict, moon_data: Dict) -> str:
        """生成HTML邮件内容"""
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
                    <div style="opacity: 0.9;">体感温度: {current['feels_like']}°C</div>
                </div>
                
                <div style="flex: 1; min-width: 250px;">
                    <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div><strong>🌡️ 最低/最高</strong><br>{current['temp_min']}°C / {current['temp_max']}°C</div>
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
        
        # 生活指数卡片
        life_indices_html = ""
        if life_indices:
            life_indices_html = """
            <div style="background: #f8f9fa; padding: 25px; border-radius: 15px; margin: 25px 0;">
                <h3 style="color: #2c3e50; border-left: 5px solid #3498db; padding-left: 15px; margin-top: 0;">📊 生活指数</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
            """
            
            for index_name, index_data in life_indices.items():
                level_color = {
                    1: "#27ae60",  # 绿色
                    2: "#f39c12",  # 橙色
                    3: "#e67e22",  # 深橙色
                    4: "#e74c3c"   # 红色
                }.get(index_data['level'], "#95a5a6")
                
                life_indices_html += f"""
                <div style="background: white; padding: 20px; border-radius: 10px; border-left: 5px solid {level_color};">
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <span style="font-size: 1.5em; margin-right: 10px;">{index_data.get('icon', '📊')}</span>
                        <strong style="font-size: 1.1em;">{index_name}</strong>
                    </div>
                    <div style="margin-bottom: 8px;">
                        <span style="background: {level_color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.9em;">
                            {index_data['desc']}
                        </span>
                    </div>
                    <div style="color: #555; font-size: 0.95em; line-height: 1.4;">
                        {index_data['suggestion']}
                    </div>
                </div>
                """
            
            life_indices_html += """
                </div>
            </div>
            """
        
        # 月球数据卡片
        moon_html = f"""
        <div style="background: #2c3e50; color: white; padding: 25px; border-radius: 15px; margin: 25px 0;">
            <h3 style="margin-top: 0; color: #ecf0f1;">🌌 天文信息</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div>
                    <strong>🌙 月相</strong><br>{moon_data.get('moon_phase_desc', '未知')}
                </div>
                <div>
                    <strong>🔢 月龄</strong><br>{moon_data.get('moon_age', 0)} 天
                </div>
                <div>
                    <strong>💡 月亮亮度</strong><br>{moon_data.get('moon_brightness', '0%')}
                </div>
                <div>
                    <strong>♈ 星座</strong><br>{moon_data.get('zodiac_sign', '未知')}
                </div>
                <div>
                    <strong>🌱 季节</strong><br>{moon_data.get('season', '未知')}
                </div>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px;">
                <h4 style="margin-top: 0; color: #bdc3c7;">📅 明天({moon_data.get('tomorrow_date', '')})</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                    <div><strong>☀️ 日出</strong><br>{forecasts[1].get('sunrise', '--:--') if len(forecasts) > 1 else '--:--'}</div>
                    <div><strong>🌙 日落</strong><br>{forecasts[1].get('sunset', '--:--') if len(forecasts) > 1 else '--:--'}</div>
                    <div><strong>🌄 月出</strong><br>{forecasts[1].get('moonrise', '--:--') if len(forecasts) > 1 else '--:--'}</div>
                    <div><strong>🌅 月落</strong><br>{forecasts[1].get('moonset', '--:--') if len(forecasts) > 1 else '--:--'}</div>
                </div>
            </div>
        </div>
        """
        
        # 8天预报表格
        forecast_html = ""
        if forecasts:
            forecast_html = """
            <h3 style="color: #2c3e50; border-left: 5px solid #3498db; padding-left: 15px; margin: 25px 0 20px 0;">📅 未来8天天气预报</h3>
            
            <div style="overflow-x: auto; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.05);">
                <table style="width: 100%; border-collapse: collapse; min-width: 800px;">
                    <thead>
                        <tr style="background: #2c3e50; color: white;">
                            <th style="padding: 12px; text-align: left;">日期</th>
                            <th style="padding: 12px; text-align: left;">天气</th>
                            <th style="padding: 12px; text-align: left;">温度 (°C)</th>
                            <th style="padding: 12px; text-align: left;">体感</th>
                            <th style="padding: 12px; text-align: left;">降水</th>
                            <th style="padding: 12px; text-align: left;">湿度</th>
                            <th style="padding: 12px; text-align: left;">UV</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for i, day in enumerate(forecasts[:8]):
                bg_color = "#f8f9fa" if i % 2 == 0 else "white"
                day_icon = self.weather_icon_map.get(day.get('weather_icon', '01d')[:2], '🌤️')
                
                forecast_html += f"""
                <tr style="background: {bg_color};">
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        <strong>{day['date_display']}</strong>
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        {day_icon} {day['weather']}
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        {day['temp_min']}~{day['temp_max']}°C
                        <div style="font-size: 0.85em; color: #666;">
                            昼: {day['temp_day']}°C | 夜: {day['temp_night']}°C
                        </div>
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        昼: {day['feels_like_day']}°C<br>夜: {day['feels_like_night']}°C
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        {day.get('pop', 0)}%
                    </td>
                    <td style="padding: 12px; border-bottom: 1px solid #eaeaea;">
                        {day['humidity']}%
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
                    {life_indices_html}
                    {moon_html}
                    {forecast_html}
                </div>
                <div class="footer">
                    <p>数据来源: OpenWeatherMap One Call API 3.0 | 自动发送服务 | 更新频率: 每日00:00</p>
                    <p>© {today.year} 天气助手 | 本邮件包含8天预报、生活指数和天文信息 | 收件人: {len(self.receiver_emails)}人</p>
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
        current_weather = self._get_current_weather_detailed()
        if not current_weather:
            return {"success": False, "error": "获取当前天气失败"}
        
        # 2. 获取8天预报
        forecast = self._get_8day_forecast()
        if not forecast:
            return {"success": False, "error": "获取天气预报失败"}
        
        # 3. 计算生活指数
        life_indices = self._calculate_life_indices(current_weather, forecast[0] if forecast else {})
        
        # 4. 获取月球数据
        moon_data = self._get_moon_data()
        
        # 5. 生成HTML邮件
        html_content = self._format_html_email(current_weather, forecast, life_indices, moon_data)
        
        # 6. 发送邮件
        print(f"📧 开始发送邮件到 {len(self.receiver_emails)} 个收件人...")
        success, failure = self.send_email(html_content)
        
        if success > 0:
            return {
                "success": True,
                "message": f"邮件发送完成: 成功 {success} 封, 失败 {failure} 封",
                "city": self.location_city,
                "recipients": len(self.receiver_emails),
                "current_temp": current_weather['temp'],
                "weather": current_weather['weather_desc'],
                "forecast_days": len(forecast),
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
