from socket import *
import numpy as np
import joblib
import matplotlib.pyplot as plt
from datetime import datetime
from influxdb import InfluxDBClient
import time

# InfluxDB 접속 정보
influx_host = '192.168.199.128'
influx_port = 8086
influx_username = 'hajin'
influx_password = '1234'
influx_database = 'mydb'

# InfluxDB 클라이언트 객체 생성
client = InfluxDBClient(host=influx_host, port=influx_port,
                        username=influx_username, password=influx_password, database=influx_database)

# OneClassSVM 모델 로드
model = joblib.load('trained_oneclass_svm_gas_model.joblib')

# 소켓 설정
port = 9000
BUFSIZE = 1024
sock = socket(AF_INET, SOCK_STREAM)
sock.bind(('', port))
sock.listen(1)
print("Waiting for clients...")

c_sock, (r_host, r_port) = sock.accept()
print('Connected by', r_host, r_port)

interval = 0.1

# 시각화를 위한 데이터 저장 변수 초기화
data_points = []  # 모든 데이터 저장 (정상 + 이상)


try:
    while True:
        data = c_sock.recv(BUFSIZE).decode()
        if not data:
            break
        print("Received message:", data)

        current_time = datetime.utcnow()

        values = data.strip().split(',')
        if len(values) == 3:
            la, Va, gasValue = values
            gas_value_float = float(gasValue)

            # 데이터와 타임스탬프를 리스트에 추가
            data_points.append((gas_value_float, current_time, gas_value_float > 1900))
            
            # InfluxDB에 데이터 기록

            try:
                gasValue_float = float(gasValue)
            except ValueError:
                gasValue_float = 0.0  # 변환에 실패할 경우 기본값 사용
             
            data_to_write = [
                {
                    "measurement": "mydb",
                    "time": current_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    "fields": {
                        "la": float(la),
                        "Va": float(Va),
                        "gasValue": gas_value_float
                    }
                }
            ]
            client.write_points(data_to_write)

        time.sleep(interval)


except KeyboardInterrupt:
    print("Interrupted by user")
finally:
    c_sock.close()
    sock.close()
    print("Connection closed.")

# 데이터 포인트를 타임스탬프에 따라 정렬
data_points.sort(key=lambda x: x[1])
        
# 데이터 시각화 부분
# 타임스탬프에 따른 초 단위 시간 배열 생성
timestamps_seconds = [(t[1] - data_points[0][1]).total_seconds() for t in data_points]
        
# 데이터 값과 이상 여부를 분리
gas_values = [point[0] for point in data_points]
anomalies = [point[2] for point in data_points]

plt.figure(figsize=(10, 6))

# 데이터 그래프 그리기
for i, (value, timestamp, anomaly) in enumerate(data_points):
    if anomaly:
        plt.plot(timestamps_seconds[i], value, 'r-' , label='Anomaly' if i == 0 else "")
        plt.scatter(timestamps_seconds[i], value, c='red', label='Anomaly' if i == 0 else "")
    else:
        plt.plot(timestamps_seconds[i], value, 'b-' , label='Normal' if i == 0 else "")
        plt.scatter(timestamps_seconds[i], value, c='blue', label='Normal' if i == 0 else "")

# 이상치 임계값 그리기
plt.axhline(y=1900, color='r', linestyle='--', label='Anomaly Threshold ')

plt.title('Visualization of Gas Sensor Data')
plt.xlabel('Time (seconds since start)')
plt.ylabel('Gas Sensor Value')
plt.legend()
plt.show()
