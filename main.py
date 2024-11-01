import streamlit as st
import boto3
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import time



def get_ec2_client():
    return boto3.client('ec2')

def get_cloudwatch_client():
    return boto3.client(
        'cloudwatch')

def start_instance(ec2, instance_id):
    try:
        ec2.start_instances(InstanceIds=[instance_id])
        return True, "Iniciando instancia..."
    except Exception as e:
        return False, f"Error al iniciar la instancia: {str(e)}"

def stop_instance(ec2, instance_id):
    try:
        ec2.stop_instances(InstanceIds=[instance_id])
        return True, "Deteniendo instancia..."
    except Exception as e:
        return False, f"Error al detener la instancia: {str(e)}"

def reboot_instance(ec2, instance_id):
    try:
        ec2.reboot_instances(InstanceIds=[instance_id])
        return True, "Reiniciando instancia..."
    except Exception as e:
        return False, f"Error al reiniciar la instancia: {str(e)}"


def get_instance_health(ec2, instance_id):
    response = ec2.describe_instance_status(
        InstanceIds=[instance_id],
        IncludeAllInstances=True
    )
    
    if response['InstanceStatuses']:
        status = response['InstanceStatuses'][0]
        system_status = status['SystemStatus']['Status']
        instance_status = status['InstanceStatus']['Status']
        
        # Ambos checks deben estar 'ok' para considerar la instancia healthy
        is_healthy = system_status == 'ok' and instance_status == 'ok'
        
        return {
            'system_status': system_status,
            'instance_status': instance_status,
            'is_healthy': is_healthy
        }
    return {
        'system_status': 'unknown',
        'instance_status': 'unknown',
        'is_healthy': False
    }

def get_instance_metrics(cloudwatch, instance_id, metric_name, period=300):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=3)
    
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'cpu_util',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/EC2',
                        'MetricName': metric_name,
                        'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}]
                    },
                    'Period': period,
                    'Stat': 'Average'
                }
            }
        ],
        StartTime=start_time,
        EndTime=end_time
    )
    
    if response['MetricDataResults']:
        timestamps = response['MetricDataResults'][0]['Timestamps']
        values = response['MetricDataResults'][0]['Values']
        return pd.DataFrame({
            'timestamp': timestamps,
            'value': values
        })
    return pd.DataFrame()

def get_health_status_emoji(is_healthy):
    return "✅" if is_healthy else "❌"


def instance_control_buttons(ec2, instance_id, instance_state):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if instance_state != 'running':
            if st.button("▶️ Iniciar", key=f"start_{instance_id}"):
                if st.button("🔄 Confirmar Inicio", key=f"confirm_start_{instance_id}"):
                    success, message = start_instance(ec2, instance_id)
                    st.success(message) if success else st.error(message)
                    time.sleep(2)
                    st.rerun()
    
    with col2:
        if instance_state == 'running':
            if st.button("⏹️ Detener", key=f"stop_{instance_id}"):
                if st.button("🔄 Confirmar Detención", key=f"confirm_stop_{instance_id}"):
                    success, message = stop_instance(ec2, instance_id)
                    st.success(message) if success else st.error(message)
                    time.sleep(2)
                    st.rerun()
    
    with col3:
        if instance_state == 'running':
            if st.button("🔄 Reiniciar", key=f"reboot_{instance_id}"):
                if st.button("🔄 Confirmar Reinicio", key=f"confirm_reboot_{instance_id}"):
                    success, message = reboot_instance(ec2, instance_id)
                    st.success(message) if success else st.error(message)
                    time.sleep(2)
                    st.rerun()



def main():
    st.title("📊 Dashboard de Monitoreo EC2")
    
    # Inicializar clientes
    try:
        ec2 = get_ec2_client()
        cloudwatch = get_cloudwatch_client()
    except Exception as e:
        st.error(f"Error al conectar con AWS: {str(e)}")
        return
    
    # Obtener lista de instancias
    instances = ec2.describe_instances()
    instance_list = []
    
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_name = next(
                (tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'),
                instance['InstanceId']
            )
            
            health_status = get_instance_health(ec2, instance['InstanceId'])
            
            instance_list.append({
                'id': instance['InstanceId'],
                'name': instance_name,
                'state': instance['State']['Name'],
                'type': instance['InstanceType'],
                'launch_time': instance['LaunchTime'],
                'health_status': "Healthy" if health_status['is_healthy'] else "Unhealthy",
                'system_status': health_status['system_status'],
                'instance_status': health_status['instance_status']
            })
    
    # Crear DataFrame de instancias
    df_instances = pd.DataFrame(instance_list)
    
    # Mostrar resumen de instancias
    st.header("🖥️ Resumen de Instancias")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Instancias", len(df_instances))
    with col2:
        running = len(df_instances[df_instances['state'] == 'running'])
        st.metric("Instancias Activas", running)
    with col3:
        stopped = len(df_instances[df_instances['state'] == 'stopped'])
        st.metric("Instancias Detenidas", stopped)
    with col4:
        healthy = len(df_instances[df_instances['health_status'] == 'Healthy'])
        st.metric("Instancias Healthy", f"{healthy}/{len(df_instances)}")
    
    # Mostrar tabla de instancias con estado de salud
    st.subheader("📋 Lista de Instancias")
    df_display = df_instances.copy()
    df_display['health_status'] = df_display['health_status'].apply(
        lambda x: f"{get_health_status_emoji(x == 'Healthy')} {x}"
    )
    st.dataframe(df_display)
    
    # Selección de instancia para métricas detalladas
    st.header("📈 Métricas y Control de Instancia")
    selected_instance = st.selectbox(
        "Seleccionar Instancia",
        df_instances['id'].tolist(),
        format_func=lambda x: f"{x} ({df_instances[df_instances['id']==x]['name'].iloc[0]})"
    )
    
    if selected_instance:
        instance_data = df_instances[df_instances['id'] == selected_instance].iloc[0]
        
        # Agregar botones de control
        st.subheader("🎮 Control de Instancia")
        st.write(f"Estado actual: **{instance_data['state'].upper()}**")
        instance_control_buttons(ec2, selected_instance, instance_data['state'])
        
        # Mostrar estado de salud detallado
        st.subheader("Estado de Salud")
        health_col1, health_col2, health_col3 = st.columns(3)
        with health_col1:
            st.metric(
                "Estado General",
                instance_data['health_status'],
                delta=None,
                delta_color="normal"
            )
        with health_col2:
            st.metric(
                "System Status",
                instance_data['system_status'],
                delta=None,
                delta_color="normal"
            )
        with health_col3:
            st.metric(
                "Instance Status",
                instance_data['instance_status'],
                delta=None,
                delta_color="normal"
            )
        
        # Obtener métricas de CPU
        cpu_data = get_instance_metrics(cloudwatch, selected_instance, 'CPUUtilization')
        if not cpu_data.empty:
            fig = px.line(cpu_data, x='timestamp', y='value',
                         title='Utilización de CPU (%)',
                         labels={'timestamp': 'Tiempo', 'value': 'CPU %'})
            st.plotly_chart(fig)
        else:
            st.warning("No hay datos de CPU disponibles para esta instancia")
        
        # Métricas de red
        col1, col2 = st.columns(2)
        with col1:
            network_in = get_instance_metrics(cloudwatch, selected_instance, 'NetworkIn')
            if not network_in.empty:
                fig = px.line(network_in, x='timestamp', y='value',
                             title='Network In (Bytes)',
                             labels={'timestamp': 'Tiempo', 'value': 'Bytes'})
                st.plotly_chart(fig)
        
        with col2:
            network_out = get_instance_metrics(cloudwatch, selected_instance, 'NetworkOut')
            if not network_out.empty:
                fig = px.line(network_out, x='timestamp', y='value',
                             title='Network Out (Bytes)',
                             labels={'timestamp': 'Tiempo', 'value': 'Bytes'})
                st.plotly_chart(fig)

if __name__ == "__main__":
    main()