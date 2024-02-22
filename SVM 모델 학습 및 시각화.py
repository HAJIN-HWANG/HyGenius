from socket import *
import numpy as np
from sklearn.svm import OneClassSVM as OCS
import joblib
import matplotlib.pyplot as plt
plt.rcParams['axes.unicode_minus'] = False

# 소켓 설정
port = 9000
BUFSIZE = 1024
sock = socket(AF_INET, SOCK_STREAM)
sock.bind(('', port))
sock.listen(1)
print("Waiting for clients...")

# 가스 센서 데이터와 이상치 데이터를 저장할 리스트
gas_data = []
anomalies = []


c_sock, (r_host, r_port) = sock.accept()
print('Connected by', r_host, r_port)

try:
    while True:  # 지속적으로 데이터 수신
        data = c_sock.recv(BUFSIZE).decode()
        if not data:  # 데이터 수신이 없을 경우 루프 중단
            break

        print("Received message:", data)

        # 데이터 분리 및 파싱
        values = data.strip().split(',')
        if len(values) == 3:
            la, Va, gasValue = values
            gas_value_float = float(gasValue)
            
            # 가스 센서 값만 추출하여 리스트에 추가
            gas_data.append([gas_value_float])  
            
            # 이상치 판별 로직
            if gas_value_float > 1700:
                print(f"Anomaly detected: {gas_value_float}")
                anomalies.append([gas_value_float])

except KeyboardInterrupt:  # 사용자가 Ctrl+C를 누르면 실행 중단
    print("Data reception interrupted by user")

finally:
    c_sock.close()
    sock.close()
    print("Socket connection closed.")

    # 데이터가 충분히 수집되었다면 모델 학습 시작
    if len(gas_data) > 0:
        X = np.array(gas_data)
        gamma_value = 1 / (X.shape[1] * X.var())
        
        # OneClassSVM 모델 초기화
        ocs = OCS(kernel='rbf', nu=0.3, gamma=gamma_value)
        ocs.fit(X)
        print(f"Training completed with {len(gas_data)} gas sensor data points.")

        # 학습된 모델 저장
        joblib.dump(ocs, 'trained_oneclass_svm_gas_model.joblib')
        print("Model saved to trained_oneclass_svm_gas_model.joblib")

        # 학습 데이터 및 이상치 시각화
        plt.figure(figsize=(8, 8))
        plt.scatter(X[:, 0], np.zeros_like(X[:, 0]), c='blue', label='Training Data')
        if anomalies:
            anomalies = np.array(anomalies)
            plt.scatter(anomalies[:, 0], np.zeros_like(anomalies[:, 0]), c='red', label='Anomalies')
        plt.axvline(x=1700, color='r', linestyle='--', label='Anomaly Threshold ')
        plt.xlabel('Gas Sensor Value')
        plt.yticks([])  # Y축 눈금 제거
        plt.title('Visualization of Training Data for Gas Sensor with Anomaly Threshold')
        plt.legend()
        plt.show()
