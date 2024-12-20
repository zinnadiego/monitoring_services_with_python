# Importaciones de bibliotecas necesarias
import requests  # Para realizar peticiones HTTP
import mysql.connector  # Para conexiones a MySQL
import psycopg  # Para conexiones a PostgreSQL
#import cx_Oracle  # (Comentado) Para conexiones a Oracle
import pyodbc  # Para conexiones a bases de datos vía ODBC
import smtplib  # Para enviar correos electrónicos
import logging  # Para el sistema de logs
import json  # Para manejar archivos JSON
import platform  # Para obtener información del sistema
import socket  # Para obtener información de red
from email.mime.text import MIMEText  # Para crear el contenido del correo
from email.mime.multipart import MIMEMultipart  # Para crear correos con múltiples partes
import time  # Para manejar delays y tiempos
from datetime import datetime, timedelta  # Para manejar fechas y tiempos
from abc import ABC, abstractmethod  # Para crear clases abstractas
import os  # Para operaciones del sistema de archivos
import sys  # Para funciones del sistema
from logging.handlers import RotatingFileHandler  # Para rotar archivos de log

def load_config():
    """Carga la configuración desde un archivo JSON"""
    try:
        # Intenta abrir y leer el archivo config.json
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Si no encuentra el archivo, registra una advertencia y retorna configuración por defecto
        logger.warning("Archivo config.json no encontrado, usando configuración por defecto")
        return {
            'websites': {},
            'databases': {},
            'email': {},
            'monitor_settings': {},
            'logging_settings': {}
        }


def setup_logging():
    """Configura el sistema de logging basado en la configuración del JSON"""
    # Carga la configuración
    config = load_config()
    # Obtiene la configuración de logging o usa valores por defecto
    logging_config = config.get('logging_settings', {
        'enable_file_logging': True,  # Por defecto habilitado
        'max_bytes': 5*1024*1024,    # 5 MB por defecto
        'backup_count': 5,           # 5 archivos por defecto
        'log_file': 'monitor_servicios.log'
    })

    # Configura el logger principal
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Elimina handlers existentes para evitar duplicados
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Configura el handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Configura el handler de archivo si está habilitado
    if logging_config.get('enable_file_logging', True):
        try:
            file_handler = RotatingFileHandler(
                logging_config['log_file'],
                maxBytes=logging_config['max_bytes'],
                backupCount=logging_config['backup_count'],
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.info("Logging a archivo habilitado: %s", logging_config['log_file'])
        except Exception as e:
            logger.error(f"Error al configurar el logging a archivo: {e}")
    else:
        logger.info("Logging a archivo deshabilitado por configuración")
    
    return logger

# Inicializar el logger
logger = setup_logging()

class ServiceStatus:
    def __init__(self):
        # Inicializa diccionarios para rastrear el estado de los servicios
        self.failures = {}      # Contador de fallos por servicio
        self.successes = {}     # Contador de éxitos por servicio
        self.last_alert = {}    # Última alerta enviada por servicio
        self.is_down = {}       # Estado actual de cada servicio
        
    def record_failure(self, service_name):
        # Registra un fallo para un servicio
        self.failures[service_name] = self.failures.get(service_name, 0) + 1
        self.successes[service_name] = 0  # Reinicia el contador de éxitos
        return self.failures[service_name]
        
    def record_success(self, service_name):
        # Registra un éxito para un servicio
        self.successes[service_name] = self.successes.get(service_name, 0) + 1
        self.failures[service_name] = 0    # Reinicia el contador de fallos
        return self.successes[service_name]
        
    def should_alert(self, service_name, threshold, repeat_interval):
        """Determina si se debe enviar una alerta basándose en los fallos y el intervalo de repetición"""
        current_failures = self.failures.get(service_name, 0)
        last_alert_time = self.last_alert.get(service_name)
        
        # Si no hay suficientes fallos, no alerta
        if current_failures < threshold:
            return False
            
        # Si es la primera alerta o ha pasado el intervalo de repetición
        if last_alert_time is None:
            return True
            
        # Calcula el tiempo transcurrido desde la última alerta
        time_since_last_alert = (datetime.now() - last_alert_time).total_seconds()
        return time_since_last_alert >= repeat_interval
                 
    def mark_alerted(self, service_name):
        # Marca que se ha enviado una alerta para el servicio
        self.last_alert[service_name] = datetime.now()
        self.is_down[service_name] = True
        
    def is_recovered(self, service_name, threshold):
        # Verifica si un servicio se ha recuperado basado en el número de éxitos
        return (self.is_down.get(service_name, False) and 
                self.successes.get(service_name, 0) >= threshold)
                
    def mark_recovered(self, service_name):
        # Marca un servicio como recuperado
        if service_name in self.last_alert:
            del self.last_alert[service_name]
        self.is_down[service_name] = False


class SystemInfo:
    """Clase para obtener información del sistema"""
    @staticmethod
    def get_system_info():
        # Recopila información del sistema usando el módulo platform
        info = {
            'hostname': socket.gethostname(),        # Nombre del host
            'system': platform.system(),             # Sistema operativo
            'release': platform.release(),           # Versión del sistema
            'machine': platform.machine(),           # Arquitectura
            'processor': platform.processor(),       # Procesador
            'python_version': platform.python_version() # Versión de Python
        }
        return info

class DatabaseChecker(ABC):
    """Clase base abstracta para verificadores de bases de datos"""
    
    @abstractmethod
    def check_connection(self, config):
        """Método abstracto que debe ser implementado por las subclases
        para verificar la conexión específica de cada tipo de base de datos"""
        pass
        
    def check_with_retry(self, config, retry_attempts=3, retry_delay=30):
        """Intenta conectar con reintentos si falla la conexión"""
        for attempt in range(retry_attempts):
            try:
                # Intenta la conexión
                result = self.check_connection(config)
                if result:
                    return True
                # Si falla, registra el intento y espera antes de reintentar
                logger.warning(f"Intento {attempt + 1} fallido, reintentando en {retry_delay} segundos...")
                time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Error en intento {attempt + 1}: {e}")
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay)
        return False

def check_website(url, retry_attempts=3, retry_delay=30):
    """Verifica el estado de un sitio web con reintentos"""
    # Define headers personalizados para la petición HTTP
    headers = {
        'User-Agent': 'ServiceMonitor/1.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    # Intenta la conexión el número de veces especificado
    for attempt in range(retry_attempts):
        try:
            # Realiza la petición HTTP con timeout de 10 segundos
            response = requests.get(url, timeout=10, headers=headers)
            # Si el status code es 200 (OK), el sitio está funcionando
            if response.status_code == 200:
                return True
            # Si no es 200, registra el fallo y reintenta
            logger.warning(f"Intento {attempt + 1} fallido (status code: {response.status_code})")
            if attempt < retry_attempts - 1:
                time.sleep(retry_delay)
        except requests.RequestException as e:
            # Si hay una excepción, registra el error y reintenta
            logger.error(f"Error en intento {attempt + 1}: {e}")
            if attempt < retry_attempts - 1:
                time.sleep(retry_delay)
    return False

def send_alert_email(service_name, service_type, status="down", additional_info=None):
    """Envía un correo de alerta con información detallada"""
    # Carga la configuración
    config = load_config()
    email_config = config['email']
    
    logger.info("Preparando envío de correo de alerta...")
    logger.info(f"Configuración SMTP: servidor={email_config['smtp_server']}, puerto={email_config['smtp_port']}")
    
    # Obtiene lista de destinatarios
    recipients = email_config.get('recipient_emails', [email_config.get('recipient_email', '')])
    if isinstance(recipients, str):
        recipients = [recipients]
    
    logger.info(f"Enviando correo a {len(recipients)} destinatarios")
    
    try:
        # Configura la conexión SMTP
        logger.info("Iniciando conexión con servidor SMTP...")
        if email_config['smtp_use_ssl']:
            server = smtplib.SMTP_SSL(email_config['smtp_server'], email_config['smtp_port'])
        else:
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
        
        server.ehlo()
        
        # Configura TLS si está habilitado
        if email_config['smtp_use_tls']:
            logger.info("Iniciando TLS...")
            server.starttls()
            server.ehlo()
        
        # Login si hay credenciales
        if email_config['sender_password']:
            logger.info(f"Intentando login con usuario: {email_config['sender_email']}")
            server.login(email_config['sender_email'], email_config['sender_password'])
        
        # Envía el correo a cada destinatario
        for recipient in recipients:
            try:
                # Crea el mensaje
                msg = MIMEMultipart()
                msg['From'] = email_config['sender_email']
                msg['To'] = recipient
                
                # Define el asunto según el estado
                if status == "down":
                    msg['Subject'] = f'🔴 ALERTA: Servicio caído - {service_name}'
                else:
                    msg['Subject'] = f'🟢 RECUPERADO: Servicio {service_name}'

                # Prepara el cuerpo del mensaje con información detallada
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                system_info = SystemInfo.get_system_info()
                
                # Construcción del cuerpo del mensaje
                body = f"""
                {'⚠️ ALERTA DE SERVICIO CAÍDO' if status == "down" else '✅ SERVICIO RECUPERADO'}
                
                Detalles del servicio:
                ----------------------
                Servicio: {service_name}
                Tipo: {service_type}
                Estado: {"CAÍDO" if status == "down" else "RECUPERADO"}
                Fecha y hora: {current_time}
                
                Información del sistema:
                -----------------------
                Hostname: {system_info['hostname']}
                Sistema: {system_info['system']} {system_info['release']}
                Máquina: {system_info['machine']}
                
                {"Información adicional:" if additional_info else ""}
                {additional_info if additional_info else ""}
                
                Este es un mensaje automático del sistema de monitoreo.
                """
                
                msg.attach(MIMEText(body, 'plain'))
                server.send_message(msg)
                logger.info(f"Correo enviado exitosamente a {recipient}")
                
            except Exception as e:
                logger.error(f"Error enviando correo a {recipient}: {e}")
                continue
        
        server.quit()
        logger.info("Proceso de envío de correos completado")
        
    except Exception as e:
        # Manejo de diferentes tipos de errores SMTP
        logger.error(f"Error en el proceso de envío: {e}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback completo: {traceback.format_exc()}")

def monitor_services():
    """Función principal que monitorea todos los servicios"""
    # Carga la configuración y crea el rastreador de estado
    config = load_config()
    status_tracker = ServiceStatus()
    
    # Verifica que haya servicios configurados
    if not config['websites'] and not config['databases']:
        logger.error("No hay servicios configurados para monitorear.")
        sys.exit(1)
    
    # Muestra resumen de configuración
    logger.info("Iniciando monitor de servicios")
    logger.info("Configuración cargada:")
    # Muestra los sitios web configurados
    if config['websites']:
        logger.info("Sitios web:")
        for name, url in config['websites'].items():
            logger.info(f"  - {name}: {url}")
    # Muestra las bases de datos configuradas
    if config['databases']:
        logger.info("Bases de datos:")
        for name, db_config in config['databases'].items():
            logger.info(f"  - {name} ({db_config['type']})")
    
    logger.info("Iniciando bucle de monitoreo...")
    
    # Bucle principal de monitoreo
    while True:
        try:
            start_time = datetime.now()
            logger.info(f"Iniciando ciclo de verificación a las {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Monitoreo de sitios web
            for name, url in config['websites'].items():
                logger.info(f"Verificando sitio web: {name}")
                success = check_website(
                    url, 
                    config['monitor_settings']['retry_attempts'],
                    config['monitor_settings']['retry_delay']
                )
                
                # Manejo de fallos
                if not success:
                    failures = status_tracker.record_failure(name)
                    if status_tracker.should_alert(
                        name, 
                        config['monitor_settings']['alert_threshold'],
                        config['monitor_settings'].get('alert_repeat_interval', 300)
                    ):
                        logger.error(f"Sitio web caído: {name}")
                        send_alert_email(name, "Sitio Web")
                        status_tracker.mark_alerted(name)
                # Manejo de éxitos
                else:
                    successes = status_tracker.record_success(name)
                    if status_tracker.is_recovered(name, config['monitor_settings']['recovery_threshold']):
                        logger.info(f"Sitio web recuperado: {name}")
                        send_alert_email(name, "Sitio Web", status="recovered")
                        status_tracker.mark_recovered(name)
            
            # Calcula el tiempo de espera hasta el próximo ciclo
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            sleep_time = max(1, config['monitor_settings']['check_interval'] - execution_time)
            
            logger.info(f"Ciclo completado. Esperando {sleep_time} segundos hasta el próximo ciclo...")
            time.sleep(sleep_time)
            
        except KeyboardInterrupt:
            logger.info("Deteniendo el monitor de servicios...")
            break
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            logger.info("Esperando 60 segundos antes de reintentar...")
            time.sleep(60)
            
if __name__ == "__main__":    # Verifica si el script se está ejecutando directamente
    try:
        monitor_services()     # Inicia la función principal de monitoreo
    except Exception as e:     # Captura cualquier error no manejado
        # Registra el error como crítico en el log
        logger.critical(f"Error crítico: {e}")
        # Termina el programa con código de error 1
        sys.exit(1)