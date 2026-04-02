import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Any, Optional

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
        
        # 城市ID映射（需要根据您所在城市调整）
        self.city_id_map = {
            "湖州": "101210201",
            "杭州": "101210101",
            "上海": "101020100",
            "北京": "101010100"
        }
        
        # 天气图标映射
        self.weather_icon_map = {
            "0": "☀️",  # 晴
            "1": "⛅",  # 多云
            "2": "☁️",  # 阴
            "3": "🌧️",  # 阵雨
            "4": "⛈️",  # 雷阵雨
            "5": "🌧️",  # 雷阵雨伴有冰雹
            "6": "🌦️",  # 雨夹雪
            "7": "🌧️",  # 小雨
            "8": "🌧️",  # 中雨
            "9": "🌧️",  # 大雨
            "10": "🌧️",  # 暴雨
            "11": "🌧️",  # 大暴雨
            "12": "🌧️",  # 特大暴雨
            "13": "🌨️",  # 阵雪
            "14": "❄️",  # 小雪
            "15": "❄️",  # 中雪
            "16": "❄️",  # 大雪
            "17": "❄️",  # 暴雪
            "18": "🌫️",  # 雾
            "19": "🌫️",  # 冻雨
            "20": "🌫️",  # 沙尘暴
            "21": "🌦️",  # 小雨-中雨
            "22": "🌧️",  # 中雨-大雨
            "23": "🌧️",  # 大雨-暴雨
            "24": "🌧️",  # 暴雨-大暴雨
            "25": "🌧️",  # 大暴雨-特大暴雨
            "26": "🌨️",  # 小雪-中雪
            "27": "❄️",  # 中雪-大雪
            "28": "❄️",  # 大雪-暴雪
            "29": "🌫️",  # 浮尘
            "30": "🌫️",  # 扬沙
            "31": "🌫️",  # 强沙尘暴
            "32": "🌫️",  # 浓雾"
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
        """格式化天气信息为HTML"""
        if not weather_data:
            return "<p>天气数据获取失败</p>"
        
        # 获取当前时间
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        
        # 实时天气
        realtime = weather_data.get("realtime", {})
        # 今天天气
        today_weather = weather_data.get("weathers", [{}])[0] if weather_data.get("weathers") else {}
        # 7天预报
        forecast_7d = weather_data.get("weathers", [])[:7] if weather_data.get("weathers") else []
        # 空气质量
        pm25_info = weather_data.get("pm25", {})
        # 生活指数
        indexes = weather_data.get("indexes", [])
        # 3小时详细预报
        weather_details = weather_data.get("weatherDetailsInfo", {}).get("weather3HoursDetailsInfos", [])[:8]
        
        # 获取当前温度
        current_temp = realtime.get("temp", "N/A")
        current_weather = realtime.get("weather", "N/A")
        weather_icon = self.weather_icon_map.get(realtime.get("img", "0"), "🌤️")
        
        # 生活指数表格
        indexes_html = ""
        if indexes:
            indexes_html = "<h3>📊 生活指数</h3>"
            indexes_html += "<table>"
            indexes_html += "<tr><th>指数</th><th>等级</th><th>建议</th></tr>"
            for idx in indexes[:6]:  # 只显示前6个指数
                indexes_html += f"""
                <tr>
                    <td><strong>{idx.get('name', '')}</strong></td>
                    <td>{idx.get('level', '')}</td>
                    <td>{idx.get('content', '')}</td>
                </tr>
                """
            indexes_html += "</table>"
        
        # 7天预报表格
        forecast_html = ""
        if forecast_7d:
            forecast_html = "<h3>📅 7天天气预报</h3>"
            forecast_html += "<table>"
            forecast_html += "<tr><th>日期</th><th>天气</th><th>最高温</th><th>最低温</th><th>日出/日落</th><th>AQI</th></tr>"
            
            for day in forecast_7d:
                date_str = day.get("date", "")
                if date_str:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                    weekday = weekdays[date_obj.weekday()]
                    date_display = f"{date_obj.month}/{date_obj.day} {weekday}"
                else:
                    date_display = day.get("week", "")
                
                weather_icon_day = self.weather_icon_map.get(day.get("img", "0"), "🌤️")
                
                forecast_html += f"""
                <tr>
                    <td><strong>{date_display}</strong></td>
                    <td>{weather_icon_day} {day.get('weather', '')}</td>
                    <td>{day.get('temp_day_c', '')}°C</td>
                    <td>{day.get('temp_night_c', '')}°C</td>
                    <td>{day.get('sun_rise_time', '')}/{day.get('sun_down_time', '')}</td>
                    <td>{day.get('aqi', '')}</td>
                </tr>
                """
            forecast_html += "</table>"
        
        # 3小时预报表格
        hourly_html = ""
        if weather_details:
            hourly_html = "<h3>⏳ 未来24小时预报</h3>"
            hourly_html += "<table>"
            hourly_html += "<tr><th>时间段</th><th>天气</th><th>温度</th><th>降水</th></tr>"
            
            for detail in weather_details[:8]:  # 显示未来24小时
                start_time = detail.get("startTime", "").split(" ")[1][:5] if detail.get("startTime") else ""
                end_time = detail.get("endTime", "").split(" ")[1][:5] if detail.get("endTime") else ""
                time_range = f"{start_time}-{end_time}" if start_time and end_time else ""
                
                weather_icon_hour = self.weather_icon_map.get(detail.get("img", "0"), "🌤️")
                precipitation = detail.get("precipitation", "0")
                
                hourly_html += f"""
                <tr>
                    <td>{time_range}</td>
                    <td>{weather_icon_hour} {detail.get('weather', '')}</td>
                    <td>{detail.get('lowerestTemperature', '')}°C</td>
                    <td>{precipitation}%</td>
                </tr>
                """
            hourly_html += "</table>"
        
        # 构建完整的HTML邮件
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: 'Microsoft YaHei', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0 0 10px 0;
                    font-size: 2.5em;
                }}
                .header .subtitle {{
                    font-size: 1.2em;
                    opacity: 0.9;
                }}
                .current-weather {{
                    display: flex;
                    justify-content: space-around;
                    align-items: center;
                    padding: 30px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #eaeaea;
                }}
                .temp-section {{
                    text-align: center;
                }}
                .temp {{
                    font-size: 4em;
                    font-weight: 300;
                    color: #2c3e50;
                }}
                .weather-status {{
                    font-size: 1.8em;
                    color: #34495e;
                    margin-top: 10px;
                }}
                .aqi-section {{
                    text-align: center;
                    padding: 20px;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                }}
                .aqi-value {{
                    font-size: 3em;
                    font-weight: bold;
                    color: #27ae60;
                }}
                .aqi-quality {{
                    font-size: 1.2em;
                    color: #7f8c8d;
                }}
                .content-section {{
                    padding: 30px;
                }}
                h3 {{
                    color: #2c3e50;
                    border-left: 5px solid #3498db;
                    padding-left: 15px;
                    margin-top: 40px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                }}
                th {{
                    background: #2c3e50;
                    color: white;
                    padding: 15px;
                    text-align: left;
                }}
                td {{
                    padding: 15px;
                    border-bottom: 1px solid #eaeaea;
                }}
                tr:nth-child(even) {{
                    background: #f8f9fa;
                }}
                tr:hover {{
                    background: #e3f2fd;
                }}
                .footer {{
                    text-align: center;
                    padding: 30px;
                    background: #2c3e50;
                    color: white;
                    font-size: 0.9em;
                }}
                .warning {{
                    color: #e74c3c;
                    font-weight: bold;
                }}
                .good {{
                    color: #27ae60;
                }}
                .moderate {{
                    color: #f39c12;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- 头部 -->
                <div class="header">
                    <h1>🌤️ {self.location_city} 天气预报</h1>
                    <div class="subtitle">数据更新时间: {current_time}</div>
                </div>
                
                <!-- 当前天气 -->
                <div class="current-weather">
                    <div class="temp-section">
                        <div class="temp">{current_temp}°C</div>
                        <div class="weather-status">{weather_icon} {current_weather}</div>
                        <div style="margin-top: 10px; color: #7f8c8d;">
                            湿度: {realtime.get('sD', 'N/A')}% | 风向: {realtime.get('wD', 'N/A')} {realtime.get('wS', 'N/A')}级
                        </div>
                    </div>
                    
                    <div class="aqi-section">
                        <div class="aqi-value">{pm25_info.get('aqi', 'N/A')}</div>
                        <div class="aqi-quality">空气质量: {pm25_info.get('quality', 'N/A')}</div>
                        <div style="margin-top: 10px; font-size: 0.9em; color: #95a5a6;">
                            PM2.5: {pm25_info.get('pm25', 'N/A')}μg/m³
                        </div>
                    </div>
                </div>
                
                <!-- 生活指数 -->
                <div class="content-section">
                    {indexes_html}
                    
                    <!-- 小时预报 -->
                    {hourly_html}
                    
                    <!-- 7天预报 -->
                    {forecast_html}
                    
                    <!-- 温馨提示 -->
                    <div style="margin-top: 40px; padding: 20px; background: #e3f2fd; border-radius: 10px;">
                        <h4 style="margin-top: 0; color: #2c3e50;">🌱 温馨提示</h4>
                        <p>今天天气{current_weather}，气温{current_temp}°C。根据预报，未来几天温差较大，请注意适时增减衣物，合理安排出行。</p>
                        <p><strong>天气趋势:</strong> 未来一周以{forecast_7d[1].get('weather', '') if len(forecast_7d) > 1 else '变化'}为主，{today_weather.get('nightWeather', '')}，请携带雨具。</p>
                    </div>
                </div>
                
                <!-- 页脚 -->
                <div class="footer">
                    <p>此天气预报由魅族天气API提供 | 自动发送服务</p>
                    <p>© 2024 天气助手 | 每日为您提供最新天气资讯</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content

    def send_email(self, html_content: str) -> bool:
        """发送邮件到所有收件人"""
        if not self.receiver_emails or not self.receiver_emails[0]:
            print("错误: 没有设置收件人邮箱")
            return False
        
        subject = f"【{self.location_city}天气预报】{datetime.now().strftime('%Y年%m月%d日')}"
        
        success_count = 0
        failure_count = 0
        
        for receiver in self.receiver_emails:
            receiver = receiver.strip()
            if not receiver:
                continue
                
            try:
                # 创建邮件
                msg = MIMEMultipart('alternative')
                msg['From'] = formataddr(("天气助手", self.sender_email))
                msg['To'] = receiver
                msg['Subject'] = subject
                msg['Date'] = formatdate(localtime=True)
                
                # 添加HTML内容
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
                
                # 连接SMTP服务器并发送
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.sender_email, self.sender_auth_code)
                    server.send_message(msg)
                
                print(f"✓ 邮件已发送至: {receiver}")
                success_count += 1
                
            except Exception as e:
                print(f"✗ 发送邮件到 {receiver} 失败: {e}")
                failure_count += 1
        
        print(f"\n📧 邮件发送完成: 成功 {success_count} 封, 失败 {failure_count} 封")
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
        print("请在GitHub仓库的Settings -> Secrets中添加以下变量:")
        print("  - SENDER_EMAIL: 发件邮箱")
        print("  - SENDER_AUTH_CODE: 邮箱授权码")
        print("  - RECEIVER_EMAILS: 收件邮箱（多个用逗号分隔）")
        exit(1)
    
    # 运行天气邮件发送程序
    sender = MeizuWeatherMailSender()
    result = sender.run()
    
    print(f"执行结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
