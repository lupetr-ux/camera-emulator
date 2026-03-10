#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ONVIF сервер для эмуляции реальных камер
Поддерживает различные модели и производителей
"""

import logging
import time
import uuid
import random
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

logger = logging.getLogger(__name__)

# База данных реальных камер для эмуляции
CAMERA_MODELS = {
    'hikvision': {
        'manufacturer': 'Hikvision',
        'models': [
            {'name': 'DS-2CD2345FWD-I', 'resolution': '2688x1520', 'fps': 30, 'description': 'Network Camera'},
            {'name': 'DS-2CD2143G0-I', 'resolution': '2048x1536', 'fps': 25, 'description': 'Network Camera'},
            {'name': 'DS-2CD2385G1-I', 'resolution': '3840x2160', 'fps': 20, 'description': '4K Camera'},
            {'name': 'DS-2CD2T45FWD-I', 'resolution': '2560x1440', 'fps': 30, 'description': 'TurboHD Camera'}
        ],
        'firmware': 'V5.5.8',
        'hardware': '0x0001'
    },
    'dahua': {
        'manufacturer': 'Dahua',
        'models': [
            {'name': 'IPC-HFW4431R-Z', 'resolution': '2688x1520', 'fps': 30, 'description': 'IR Bullet Camera'},
            {'name': 'IPC-HDBW4231F-AS', 'resolution': '2048x1536', 'fps': 30, 'description': 'Dome Camera'},
            {'name': 'IPC-HFW5831E-ZE', 'resolution': '3840x2160', 'fps': 25, 'description': '4K IR Camera'},
            {'name': 'SD49225T-HN', 'resolution': '1920x1080', 'fps': 30, 'description': 'PTZ Camera'}
        ],
        'firmware': '2.800.0000.0',
        'hardware': '1.00'
    },
    'axis': {
        'manufacturer': 'Axis Communications',
        'models': [
            {'name': 'AXIS P1448-LE', 'resolution': '2592x1944', 'fps': 25, 'description': 'Bullet Camera'},
            {'name': 'AXIS Q1615-LE', 'resolution': '1920x1080', 'fps': 60, 'description': 'Network Camera'},
            {'name': 'AXIS M3045-V', 'resolution': '2592x1944', 'fps': 15, 'description': 'Dome Camera'},
            {'name': 'AXIS P5655-E', 'resolution': '1920x1080', 'fps': 30, 'description': 'PTZ Camera'}
        ],
        'firmware': '9.80.1',
        'hardware': '1.0'
    },
    'bosch': {
        'manufacturer': 'Bosch Security',
        'models': [
            {'name': 'NBN-921V', 'resolution': '1920x1080', 'fps': 30, 'description': 'DINION IP'},
            {'name': 'NDI-5703', 'resolution': '2688x1520', 'fps': 30, 'description': 'AUTODOME IP'},
            {'name': 'FLEXIDOME IP', 'resolution': '1920x1080', 'fps': 30, 'description': 'Dome Camera'},
            {'name': 'MIC IP', 'resolution': '1920x1080', 'fps': 30, 'description': 'PTZ Camera'}
        ],
        'firmware': '7.80.0095',
        'hardware': '1.2'
    },
    'sony': {
        'manufacturer': 'Sony',
        'models': [
            {'name': 'SNC-VB770', 'resolution': '1920x1080', 'fps': 30, 'description': 'Box Camera'},
            {'name': 'SNC-EP580', 'resolution': '1920x1080', 'fps': 30, 'description': 'Fixed Camera'},
            {'name': 'SNC-XM631', 'resolution': '1280x720', 'fps': 30, 'description': 'Mini Dome'},
            {'name': 'SNC-WR600', 'resolution': '1920x1080', 'fps': 30, 'description': 'PTZ Camera'}
        ],
        'firmware': '2.10',
        'hardware': '1.0'
    }
}

class ONVIFHandler(BaseHTTPRequestHandler):
    """Обработчик ONVIF запросов"""

    def _send_soap_response(self, xml_body):
        """Отправка SOAP ответа"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/soap+xml; charset=utf-8')
        self.send_header('Server', 'ONVIF Device Service')
        self.end_headers()

        # Формируем полный SOAP ответ
        response = f'''<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope
    xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope"
    xmlns:SOAP-ENC="http://www.w3.org/2003/05/soap-encoding"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:wsa="http://www.w3.org/2005/08/addressing"
    xmlns:wsdd="http://schemas.xmlsoap.org/ws/2005/04/discovery"
    xmlns:tt="http://www.onvif.org/ver10/schema"
    xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
    xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
    <SOAP-ENV:Header>
        <wsa:Action>{self._get_action()}</wsa:Action>
        <wsa:MessageID>urn:uuid:{uuid.uuid4()}</wsa:MessageID>
    </SOAP-ENV:Header>
    <SOAP-ENV:Body>
        {xml_body}
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>'''

        # Форматируем для читаемости
        dom = minidom.parseString(response)
        pretty_response = dom.toprettyxml(indent='  ')

        self.wfile.write(pretty_response.encode('utf-8'))

    def _get_action(self):
        """Получение Action для заголовка"""
        return f"http://www.onvif.org/ver10/device/wsdl/{self.path.split('/')[-1]}"

    def do_GET(self):
        """Обработка GET запросов"""
        if self.path == '/onvif/device_service':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body>ONVIF Device Service</body></html>')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Обработка SOAP запросов"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b''
        # Отладка ONVIF запросов
        print(f"\n=== ПОЛУЧЕН ONVIF ЗАПРОС НА ПОРТУ {self.server.onvif_port} ===")
        print(f"Headers: {dict(self.headers)}")
        if post_data:
            print(f"Body: {post_data[:200]}...")
        try:
            # Парсим SOAP запрос
            root = ET.fromstring(post_data)

            # Ищем тело запроса
            body = root.find('.//{http://www.w3.org/2003/05/soap-envelope}Body')
            if body is None:
                body = root.find('.//SOAP-ENV:Body', {'SOAP-ENV': 'http://www.w3.org/2003/05/soap-envelope'})

            if body is not None:
                # Определяем тип запроса по первому дочернему элементу
                for child in body:
                    tag = child.tag
                    if 'GetDeviceInformation' in tag:
                        self._handle_get_device_information()
                    elif 'GetCapabilities' in tag:
                        self._handle_get_capabilities()
                    elif 'GetServices' in tag:
                        self._handle_get_services()
                    elif 'GetProfiles' in tag:
                        self._handle_get_profiles()
                    elif 'GetStreamUri' in tag:
                        self._handle_get_stream_uri()
                    elif 'GetSnapshotUri' in tag:
                        self._handle_get_snapshot_uri()
                    elif 'GetVideoEncoderConfigurations' in tag:
                        self._handle_get_video_encoder_configs()
                    elif 'GetVideoSources' in tag:
                        self._handle_get_video_sources()
                    elif 'GetSystemDateAndTime' in tag:
                        self._handle_get_system_date_and_time()
                    elif 'SystemReboot' in tag:
                        self._handle_system_reboot()
                    elif 'GetScopes' in tag:
                        self._handle_get_scopes()
                    elif 'GetDeviceInfo' in tag:
                        self._handle_get_device_info()
                    else:
                        self._send_error_response(f'Unknown request: {tag}')
                    return

        except Exception as e:
            logger.error(f"Ошибка обработки ONVIF запроса: {e}")
            self._send_error_response(str(e))

    def _handle_get_device_information(self):
        """Отправка информации об устройстве"""
        camera_info = self.server.camera_info
        xml_body = f'''
            <tds:GetDeviceInformationResponse>
                <tds:Manufacturer>Hikvision</tds:Manufacturer>
                <tds:Model>{camera_info.get('model', 'DS-2CD2343G0-I')}</tds:Model>
                <tds:FirmwareVersion>V5.5.0</tds:FirmwareVersion>
                <tds:SerialNumber>DS-2CD2343G0-I{camera_info.get('id', '001')}</tds:SerialNumber>
                <tds:HardwareId>IPC-HFW1230S</tds:HardwareId>
            </tds:GetDeviceInformationResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_get_capabilities(self):
        """Отправка возможностей устройства"""
        camera_info = self.server.camera_info
        host = self.server.camera_ip
        onvif_port = self.server.onvif_port
        rtsp_port = self.server.rtsp_port

        xml_body = f'''
            <tds:GetCapabilitiesResponse>
                <tds:Capabilities>
                    <tds:Device>
                        <tds:XAddr>http://{host}:{onvif_port}/onvif/device_service</tds:XAddr>
                    </tds:Device>
                    <tds:Media>
                        <tds:XAddr>http://{host}:{onvif_port}/onvif/media_service</tds:XAddr>
                        <tds:StreamingCapabilities>
                            <tds:RTPMulticast>false</tds:RTPMulticast>
                            <tds:RTP_TCP>true</tds:RTP_TCP>
                            <tds:RTP_RTSP_TCP>true</tds:RTP_RTSP_TCP>
                            <tds:NonAggregateControl>false</tds:NonAggregateControl>
                        </tds:StreamingCapabilities>
                    </tds:Media>
                    <tds:Events>
                        <tds:XAddr>http://{host}:{onvif_port}/onvif/events_service</tds:XAddr>
                        <tds:WSSubscriptionPolicySupport>true</tds:WSSubscriptionPolicySupport>
                        <tds:WSPullPointSupport>true</tds:WSPullPointSupport>
                    </tds:Events>
                    <tds:Imaging>
                        <tds:XAddr>http://{host}:{onvif_port}/onvif/imaging_service</tds:XAddr>
                    </tds:Imaging>
                    <tds:PTZ>
                        <tds:XAddr>http://{host}:{onvif_port}/onvif/ptz_service</tds:XAddr>
                    </tds:PTZ>
                </tds:Capabilities>
            </tds:GetCapabilitiesResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_get_services(self):
        """Отправка списка сервисов"""
        xml_body = '''
            <tds:GetServicesResponse>
                <tds:Service>
                    <tds:Namespace>http://www.onvif.org/ver10/device/wsdl</tds:Namespace>
                    <tds:XAddr>http://192.168.30.130:9202/onvif/device_service</tds:XAddr>
                    <tds:Version>
                        <tt:Major>2</tt:Major>
                        <tt:Minor>6</tt:Minor>
                    </tds:Version>
                </tds:Service>
                <tds:Service>
                    <tds:Namespace>http://www.onvif.org/ver10/media/wsdl</tds:Namespace>
                    <tds:XAddr>http://192.168.30.130:9202/onvif/media_service</tds:XAddr>
                    <tds:Version>
                        <tt:Major>2</tt:Major>
                        <tt:Minor>6</tt:Minor>
                    </tds:Version>
                </tds:Service>
            </tds:GetServicesResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_get_profiles(self):
        """Отправка профилей медиа"""
        camera_info = self.server.camera_info
        resolution = camera_info['resolution'].split('x')
        width = int(resolution[0])
        height = int(resolution[1])
        fps = camera_info['fps']

        xml_body = f'''
            <trt:GetProfilesResponse>
                <trt:Profiles token="Profile_1" fixed="true">
                    <tt:Name>main_stream</tt:Name>
                    <tt:VideoEncoderConfiguration token="VideoEncoder_1">
                        <tt:Name>Main Stream</tt:Name>
                        <tt:Encoding>H264</tt:Encoding>
                        <tt:Resolution>
                            <tt:Width>{width}</tt:Width>
                            <tt:Height>{height}</tt:Height>
                        </tt:Resolution>
                        <tt:Quality>5</tt:Quality>
                        <tt:RateControl>
                            <tt:FrameRateLimit>{fps}</tt:FrameRateLimit>
                            <tt:BitrateLimit>8192</tt:BitrateLimit>
                        </tt:RateControl>
                        <tt:H264>
                            <tt:GovLength>30</tt:GovLength>
                            <tt:H264Profile>Main</tt:H264Profile>
                        </tt:H264>
                    </tt:VideoEncoderConfiguration>
                    <tt:PTZConfiguration token="PTZ_1">
                        <tt:Name>PTZ</tt:Name>
                        <tt:NodeToken>PTZNode_1</tt:NodeToken>
                        <tt:DefaultAbsolutePantTiltPositionSpace>http://www.onvif.org/ver10/tptz/PanTiltSpaces/PositionGenericSpace</tt:DefaultAbsolutePantTiltPositionSpace>
                        <tt:DefaultAbsoluteZoomPositionSpace>http://www.onvif.org/ver10/tptz/ZoomSpaces/PositionGenericSpace</tt:DefaultAbsoluteZoomPositionSpace>
                        <tt:DefaultRelativePanTiltTranslationSpace>http://www.onvif.org/ver10/tptz/PanTiltSpaces/TranslationGenericSpace</tt:DefaultRelativePanTiltTranslationSpace>
                        <tt:DefaultRelativeZoomTranslationSpace>http://www.onvif.org/ver10/tptz/ZoomSpaces/TranslationGenericSpace</tt:DefaultRelativeZoomTranslationSpace>
                    </tt:PTZConfiguration>
                </trt:Profiles>
                <trt:Profiles token="Profile_2" fixed="true">
                    <tt:Name>sub_stream</tt:Name>
                    <tt:VideoEncoderConfiguration token="VideoEncoder_2">
                        <tt:Name>Sub Stream</tt:Name>
                        <tt:Encoding>H264</tt:Encoding>
                        <tt:Resolution>
                            <tt:Width>640</tt:Width>
                            <tt:Height>360</tt:Height>
                        </tt:Resolution>
                        <tt:Quality>3</tt:Quality>
                        <tt:RateControl>
                            <tt:FrameRateLimit>15</tt:FrameRateLimit>
                            <tt:BitrateLimit>1024</tt:BitrateLimit>
                        </tt:RateControl>
                        <tt:H264>
                            <tt:GovLength>15</tt:GovLength>
                            <tt:H264Profile>Baseline</tt:H264Profile>
                        </tt:H264>
                    </tt:VideoEncoderConfiguration>
                </trt:Profiles>
            </trt:GetProfilesResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_get_stream_uri(self):
        """Отправка URI потока"""
        host = self.server.camera_ip
        rtsp_port = self.server.rtsp_port
        username = self.server.username
        password = self.server.password

        xml_body = f'''
            <trt:GetStreamUriResponse>
                <trt:MediaUri>
                    <trt:Uri>rtsp://{username}:{password}@192.168.30.130:{rtsp_port}/Streaming/Channels/101</trt:Uri>
                    <trt:InvalidAfterConnect>false</trt:InvalidAfterConnect>
                    <trt:InvalidAfterReboot>true</trt:InvalidAfterReboot>
                    <trt:Timeout>PT10M</trt:Timeout>
                </trt:MediaUri>
            </trt:GetStreamUriResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_get_snapshot_uri(self):
        """Отправка URI снимка"""
        host = self.server.camera_ip
        onvif_port = self.server.onvif_port

        xml_body = f'''
            <trt:GetSnapshotUriResponse>
                <trt:MediaUri>
                    <trt:Uri>http://{host}:{onvif_port}/onvif/snapshot</trt:Uri>
                </trt:MediaUri>
            </trt:GetSnapshotUriResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_get_video_encoder_configs(self):
        """Отправка конфигураций видео энкодера"""
        camera_info = self.server.camera_info
        resolution = camera_info['resolution'].split('x')
        width = int(resolution[0])
        height = int(resolution[1])
        fps = camera_info['fps']

        xml_body = f'''
            <trt:GetVideoEncoderConfigurationsResponse>
                <trt:Configurations token="VideoEncoder_1">
                    <tt:Name>Main Stream</tt:Name>
                    <tt:Encoding>H264</tt:Encoding>
                    <tt:Resolution>
                        <tt:Width>{width}</tt:Width>
                        <tt:Height>{height}</tt:Height>
                    </tt:Resolution>
                    <tt:Quality>5</tt:Quality>
                    <tt:RateControl>
                        <tt:FrameRateLimit>{fps}</tt:FrameRateLimit>
                        <tt:BitrateLimit>8192</tt:BitrateLimit>
                    </tt:RateControl>
                    <tt:H264>
                        <tt:GovLength>30</tt:GovLength>
                        <tt:H264Profile>Main</tt:H264Profile>
                    </tt:H264>
                </trt:Configurations>
            </trt:GetVideoEncoderConfigurationsResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_get_video_sources(self):
        """Отправка информации о видео источниках"""
        camera_info = self.server.camera_info
        resolution = camera_info['resolution'].split('x')
        width = int(resolution[0])
        height = int(resolution[1])

        xml_body = f'''
            <trt:GetVideoSourcesResponse>
                <trt:VideoSources token="VideoSource_1">
                    <tt:Framerate>{camera_info['fps']}</tt:Framerate>
                    <tt:Resolution>
                        <tt:Width>{width}</tt:Width>
                        <tt:Height>{height}</tt:Height>
                    </tt:Resolution>
                    <tt:Imaging>
                        <tt:BacklightCompensation>
                            <tt:Mode>OFF</tt:Mode>
                        </tt:BacklightCompensation>
                        <tt:Brightness>50</tt:Brightness>
                        <tt:ColorSaturation>50</tt:ColorSaturation>
                        <tt:Contrast>50</tt:Contrast>
                        <tt:Exposure>
                            <tt:Mode>AUTO</tt:Mode>
                        </tt:Exposure>
                        <tt:Focus>
                            <tt:AutoFocusMode>AUTO</tt:AutoFocusMode>
                        </tt:Focus>
                        <tt:IrCutFilter>AUTO</tt:IrCutFilter>
                        <tt:Sharpness>50</tt:Sharpness>
                        <tt:WideDynamicRange>
                            <tt:Mode>OFF</tt:Mode>
                        </tt:WideDynamicRange>
                        <tt:WhiteBalance>
                            <tt:Mode>AUTO</tt:Mode>
                        </tt:WhiteBalance>
                    </tt:Imaging>
                </trt:VideoSources>
            </trt:GetVideoSourcesResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_get_system_date_and_time(self):
        """Отправка системного времени"""
        from datetime import datetime
        
        now = datetime.utcnow()
        
        xml_body = f'''
            <tds:GetSystemDateAndTimeResponse>
                <tds:SystemDateAndTime>
                    <tt:DateTimeType>Manual</tt:DateTimeType>
                    <tt:DaylightSavings>false</tt:DaylightSavings>
                    <tt:TimeZone>
                        <tt:TZ>UTC</tt:TZ>
                    </tt:TimeZone>
                    <tt:UTCDateTime>
                        <tt:Date>
                            <tt:Year>{now.year}</tt:Year>
                            <tt:Month>{now.month}</tt:Month>
                            <tt:Day>{now.day}</tt:Day>
                        </tt:Date>
                        <tt:Time>
                            <tt:Hour>{now.hour}</tt:Hour>
                            <tt:Minute>{now.minute}</tt:Minute>
                            <tt:Second>{now.second}</tt:Second>
                        </tt:Time>
                    </tt:UTCDateTime>
                </tds:SystemDateAndTime>
            </tds:GetSystemDateAndTimeResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_system_reboot(self):
        """Обработка запроса перезагрузки"""
        xml_body = '''
            <tds:SystemRebootResponse>
                <tds:Message>System is rebooting...</tds:Message>
            </tds:SystemRebootResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_get_scopes(self):
        """Отправка scopes устройства"""
        camera_info = self.server.camera_info
        host = self.server.camera_ip

        xml_body = f'''
            <tds:GetScopesResponse>
                <tds:Scopes>
                    <tt:ScopeDef>Fixed</tt:ScopeDef>
                    <tt:ScopeItem>onvif://www.onvif.org/type/NetworkVideoTransmitter</tt:ScopeItem>
                </tds:Scopes>
                <tds:Scopes>
                    <tt:ScopeDef>Fixed</tt:ScopeDef>
                    <tt:ScopeItem>onvif://www.onvif.org/hardware/{camera_info['model']}</tt:ScopeItem>
                </tds:Scopes>
                <tds:Scopes>
                    <tt:ScopeDef>Fixed</tt:ScopeDef>
                    <tt:ScopeItem>onvif://www.onvif.org/name/{camera_info['name']}</tt:ScopeItem>
                </tds:Scopes>
                <tds:Scopes>
                    <tt:ScopeDef>Fixed</tt:ScopeDef>
                    <tt:ScopeItem>onvif://www.onvif.org/location/</tt:ScopeItem>
                </tds:Scopes>
            </tds:GetScopesResponse>
        '''
        self._send_soap_response(xml_body)

    def _handle_get_device_info(self):
        """Отправка дополнительной информации об устройстве"""
        camera_info = self.server.camera_info

        xml_body = f'''
            <tds:GetDeviceInformationResponse>
                <tds:Manufacturer>{camera_info['manufacturer']}</tds:Manufacturer>
                <tds:Model>{camera_info['model']}</tds:Model>
                <tds:FirmwareVersion>{camera_info['firmware']}</tds:FirmwareVersion>
                <tds:SerialNumber>{camera_info['serial']}</tds:SerialNumber>
                <tds:HardwareId>{camera_info['hardware']}</tds:HardwareId>
            </tds:GetDeviceInformationResponse>
        '''
        self._send_soap_response(xml_body)

    def _send_error_response(self, reason):
        """Отправка ошибки"""
        xml_body = f'''
            <SOAP-ENV:Fault>
                <SOAP-ENV:Code>
                    <SOAP-ENV:Value>SOAP-ENV:Receiver</SOAP-ENV:Value>
                    <SOAP-ENV:Subcode>
                        <SOAP-ENV:Value>ter:ActionNotSupported</SOAP-ENV:Value>
                    </SOAP-ENV:Subcode>
                </SOAP-ENV:Code>
                <SOAP-ENV:Reason>
                    <SOAP-ENV:Text xml:lang="en">{reason}</SOAP-ENV:Text>
                </SOAP-ENV:Reason>
            </SOAP-ENV:Fault>
        '''
        self._send_soap_response(xml_body)

    def log_message(self, format, *args):
        """Отключаем логирование запросов"""
        pass

class ONVIFServer:
    """ONVIF сервер для эмуляции камеры"""

    def __init__(self, camera_ip, onvif_port, rtsp_port, username, password, camera_name, camera_id, video_width=1920, video_height=1080, fps=30):
        self.camera_ip = camera_ip
        self.onvif_port = onvif_port
        self.rtsp_port = rtsp_port
        self.username = username
        self.password = password
        self.camera_name = camera_name
        self.camera_id = camera_id
        self.running = False
        self.http_server = None

        # Генерируем информацию о камере на основе ID для консистентности
        random.seed(hash(camera_id) % 1000)

        # Выбираем случайного производителя
        vendor = random.choice(list(CAMERA_MODELS.keys()))
        vendor_data = CAMERA_MODELS[vendor]
        model_data = random.choice(vendor_data['models'])

        # Генерируем серийный номер
        serial = f"{vendor.upper()}{random.randint(100000, 999999)}"

        self.camera_info = {
            'name': camera_name,
            'manufacturer': vendor_data['manufacturer'],
            'model': model_data['name'],
            'firmware': f"{vendor_data['firmware']} build {random.randint(20230101, 20251231)}",
            'hardware': vendor_data['hardware'],
            'serial': serial,
            'resolution': model_data['resolution'] or f"{video_width}x{video_height}",
            'fps': model_data['fps'] or fps,
            'description': model_data['description']
        }

        logger.info(f"ONVIF камера {camera_id} настроена как: {self.camera_info['manufacturer']} {self.camera_info['model']}")

    def start(self):
        """Запуск ONVIF сервера"""
        try:
            import socketserver
            from http.server import HTTPServer

            class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
                allow_reuse_address = True

            self.http_server = ThreadedHTTPServer(('0.0.0.0', self.onvif_port), ONVIFHandler)
            self.http_server.camera_info = self.camera_info
            self.http_server.camera_ip = self.camera_ip
            self.http_server.onvif_port = self.onvif_port
            self.http_server.rtsp_port = self.rtsp_port
            self.http_server.username = self.username
            self.http_server.password = self.password

            logger.info(f"ONVIF сервер для камеры {self.camera_id} запущен на порту {self.onvif_port}")
            logger.info(f"Эмулируется: {self.camera_info['manufacturer']} {self.camera_info['model']}")

            self.running = True
            self.http_server.serve_forever()

        except Exception as e:
            logger.error(f"Ошибка запуска ONVIF сервера: {e}")

    def stop(self):
        """Остановка ONVIF сервера"""
        self.running = False
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
            logger.info(f"ONVIF сервер для камеры {self.camera_id} остановлен")
