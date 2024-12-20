# Sistema de Monitoreo de Servicios
## Documentación Técnica v2.0

## Índice
1. [Descripción General](#descripción-general)
2. [Requisitos del Sistema](#requisitos-del-sistema)
3. [Instalación](#instalación)
4. [Configuración](#configuración)
5. [Estructura del Programa](#estructura-del-programa)
6. [Funcionalidades](#funcionalidades)
7. [Logs y Monitoreo](#logs-y-monitoreo)
8. [Solución de Problemas](#solución-de-problemas)
9. [Mantenimiento y Mejores Prácticas](#mantenimiento-y-mejores-prácticas)

## Descripción General
Este sistema es una herramienta robusta de monitoreo que supervisa constantemente la disponibilidad de sitios web y servicios. Cuando detecta una caída o recuperación de un servicio, envía notificaciones por correo electrónico a los administradores designados.

### Características Principales
- Monitoreo continuo de sitios web y bases de datos con sistema de reintentos
- Soporte para múltiples tipos de bases de datos (MySQL, PostgreSQL, SQL Server)
- Sistema de notificaciones por correo electrónico con soporte para múltiples destinatarios
- Sistema de logs rotativo y configurable
- Detección inteligente de caídas y recuperaciones de servicios
- Manejo de errores robusto y resiliente
- Soporte para TLS/SSL en comunicaciones SMTP

## Requisitos del Sistema

### Software Necesario
- Python 3.7 o superior
- pip (gestor de paquetes de Python)
- Acceso a servidor SMTP para envío de correos
- Permisos de escritura en el directorio para los logs

### Bibliotecas Python Requeridas
```bash
requests==2.28.1          # Para peticiones HTTP
mysql-connector-python    # Para conexiones MySQL
psycopg2-binary          # Para conexiones PostgreSQL
pyodbc                   # Para conexiones ODBC
```

## Instalación

### Estructura del Proyecto
```
sistema-monitoreo/
│
├── monitoreo.py           # Script principal
├── config.json           # Archivo de configuración
├── requirements.txt      # Lista de dependencias
└── monitor_servicios.log # Archivo de logs (generado automáticamente)
```

### Pasos de Instalación

1. Clonar o descargar los archivos del programa:
   ```bash
   git clone https://github.com/zinnadiego/monitoring_services_with_python
   cd sistema-monitoreo
   ```

2. Instalar las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

### Dependencias (requirements.txt)
El archivo requirements.txt contiene las siguientes bibliotecas:

- `requests==2.28.1`: 
  - Realiza peticiones HTTP a los sitios web monitoreados
  - Maneja timeouts y errores de conexión
  - Soporta headers personalizados y SSL

- `mysql-connector-python==8.0.32`:
  - Conecta con bases de datos MySQL
  - Soporta SSL y autenticación segura
  - Maneja pool de conexiones

- `psycopg2-binary==2.9.5`:
  - Conecta con bases de datos PostgreSQL
  - Versión binaria precompilada
  - Soporta SSL y conexiones asíncronas

- `pyodbc==4.0.35`:
  - Conecta con bases de datos vía ODBC
  - Soporta SQL Server y otras bases compatibles
  - Maneja múltiples tipos de autenticación

NOTA: El archivo requirements.txt debe estar en el directorio raíz del proyecto para que pip pueda encontrarlo automáticamente.

## Configuración

### Estructura de config.json
```json
{
    "websites": {
        "Web uno": "https://www.direccionwebuno.com",
        "Web dos": "https://www.direccionwebdos.com"
    },
    "databases": {
        "Database1": {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "nombre_db",
            "user": "usuario",
            "password": "contraseña"
        },
        "Database2": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "nombre_db",
            "user": "usuario",
            "password": "contraseña"
        }
    },
    "email": {
        "smtp_server": "mail.servidor.com",
        "smtp_port": 587,
        "smtp_use_tls": true,
        "smtp_use_ssl": false,
        "sender_email": "ejemplo@tucorreo.com",
        "sender_password": "tu_password",
        "recipient_emails": [
            "ejemplo@tucorreo.com",
            "ejemplo@tucorreo.com"
        ]
    },
    "monitor_settings": {
        "check_interval": 60,
        "retry_attempts": 3,
        "retry_delay": 6,
        "alert_threshold": 3,
        "recovery_threshold": 2,
        "alert_repeat_interval": 20
    },
    "logging_settings": {
        "enable_file_logging": false,
        "max_bytes": 5242880,
        "backup_count": 5,
        "log_file": "monitor_servicios.log"
    }
}
```

### Descripción de Parámetros

#### Websites
Define los sitios web a monitorear:
- `"Nombre del Sitio"`: Identificador amigable del sitio
- `"URL"`: Dirección web completa del sitio a monitorear

#### Databases
Define las bases de datos a monitorear:
- `type`: Tipo de base de datos ("mysql", "postgresql", "sqlserver")
- `host`: Servidor de la base de datos
- `port`: Puerto de conexión
- `database`: Nombre de la base de datos
- `user`: Usuario para la conexión
- `password`: Contraseña del usuario

#### Email
Configuración del sistema de notificaciones:
- `smtp_server`: Servidor SMTP para envío de correos
- `smtp_port`: Puerto del servidor (587 para TLS, 465 para SSL)
- `smtp_use_tls`: Habilita conexión TLS
- `smtp_use_ssl`: Habilita conexión SSL
- `sender_email`: Correo electrónico remitente
- `sender_password`: Contraseña del correo remitente
- `recipient_emails`: Array de correos destinatarios

#### Monitor Settings
Parámetros de comportamiento del monitor:
- `check_interval`: Segundos entre verificaciones (default: 60)
- `retry_attempts`: Intentos antes de marcar como caído (default: 3)
- `retry_delay`: Segundos entre reintentos (default: 6)
- `alert_threshold`: Fallos consecutivos antes de alertar (default: 3)
- `recovery_threshold`: Éxitos consecutivos para recuperación (default: 2)
- `alert_repeat_interval`: Minutos entre alertas repetidas (default: 20)

#### Logging Settings
Configuración del sistema de logs:
- `enable_file_logging`: Habilita/deshabilita logs en archivo
- `max_bytes`: Tamaño máximo del archivo de log (default: 5MB)
- `backup_count`: Archivos de respaldo a mantener (default: 5)
- `log_file`: Nombre del archivo de log

## Estructura del Programa

### Clases Principales

#### ServiceStatus
Gestiona el estado de los servicios:
```python
class ServiceStatus:
    def __init__(self)
    def record_failure(self, service_name)
    def record_success(self, service_name)
    def should_alert(self, service_name, threshold, repeat_interval)
    def mark_alerted(self, service_name)
    def is_recovered(self, service_name, threshold)
    def mark_recovered(self, service_name)
```

#### SystemInfo
Recopila información del sistema:
```python
class SystemInfo:
    @staticmethod
    def get_system_info()
```

#### DatabaseChecker
Clase base para verificación de bases de datos:
```python
class DatabaseChecker(ABC):
    @abstractmethod
    def check_connection(self, config)
    def check_with_retry(self, config, retry_attempts, retry_delay)
```

### Funciones Principales

#### check_website(url, retry_attempts, retry_delay)
Verifica disponibilidad de sitios web:
- Realiza peticiones HTTP con headers personalizados
- Sistema de reintentos configurable
- Timeout de 10 segundos por intento

#### send_alert_email(service_name, service_type, status, additional_info)
Sistema de notificaciones:
- Soporte para múltiples destinatarios
- Formateo de mensajes con emojis
- Inclusión de información del sistema
- Manejo de errores SMTP

#### monitor_services()
Función principal del programa:
- Bucle principal de monitoreo
- Control de intervalos de verificación
- Manejo de estados y alertas
- Gestión de recuperaciones

## Logs y Monitoreo

### Sistema de Logging
- Logging simultáneo a consola y archivo
- Rotación automática de archivos
- Niveles de log: INFO, WARNING, ERROR, CRITICAL
- Formato timestamp - nivel - mensaje

### Estructura de Logs
```
2024-12-19 10:15:23 - INFO - Iniciando monitor de servicios
2024-12-19 10:15:23 - INFO - Verificando sitio web: Web uno
2024-12-19 10:15:24 - WARNING - Intento 1 fallido (status code: 503)
2024-12-19 10:15:30 - ERROR - Sitio web caído: Web uno
