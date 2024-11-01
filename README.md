# Monitoringdashboard 📊
Dashboard for monitoring instances in AWS accounts

Este dashboard incluye las siguientes características:

### Resumen General:

### Total de instancias
Instancias activas vs detenidas
Tabla con detalles de todas las instancias


### Métricas por Instancia:

Utilización de CPU
Tráfico de red (entrada y salida)
Gráficos interactivos usando Plotly


### Seguridad:

Uso de secrets de Streamlit para las credenciales de AWS
Manejo de errores de conexión



### Para usar este dashboard, necesitarás:

Instalar las dependencias:

```python
pip install streamlit boto3 pandas plotly
```

### Configurar las credenciales de AWS en un archivo

```
AWS_ACCESS_KEY_ID = "tu_access_key"
AWS_SECRET_ACCESS_KEY = "tu_secret_key"
AWS_REGION = "tu_region"
```
### Ejecutar la aplicación:

```
streamlit run main.py
```