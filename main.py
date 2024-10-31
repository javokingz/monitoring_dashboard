import streamlit as st
import boto3
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

def get_ec2_client():
    return boto3.client(
        'ec2'
    )

def get_cloudwatch_client():
    return boto3.client(
        'cloudwatch',
        
    )

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
            instance_list.append({
                'id': instance['InstanceId'],
                'name': instance_name,
                'state': instance['State']['Name'],
                'type': instance['InstanceType'],
                'launch_time': instance['LaunchTime']
            })
    
    # Crear DataFrame de instancias
    df_instances = pd.DataFrame(instance_list)
    
    # Mostrar resumen de instancias
    st.header("🖥️ Resumen de Instancias")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Instancias", len(df_instances))
    with col2:
        running = len(df_instances[df_instances['state'] == 'running'])
        st.metric("Instancias Activas", running)
    with col3:
        stopped = len(df_instances[df_instances['state'] == 'stopped'])
        st.metric("Instancias Detenidas", stopped)
    
    # Mostrar tabla de instancias
    st.subheader("📋 Lista de Instancias")
    st.dataframe(df_instances)
    
    # Selección de instancia para métricas detalladas
    st.header("📈 Métricas Detalladas")
    selected_instance = st.selectbox(
        "Seleccionar Instancia",
        df_instances['id'].tolist(),
        format_func=lambda x: f"{x} ({df_instances[df_instances['id']==x]['name'].iloc[0]})"
    )
    
    if selected_instance:
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